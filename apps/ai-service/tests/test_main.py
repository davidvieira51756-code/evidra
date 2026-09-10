import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from main import (
    FindingInput,
    app,
    build_deterministic_explanation,
    get_ai_provider,
    retrieve_context,
)
from providers import AIProviderError, OllamaProvider


class FakeProvider:
    def __init__(
        self,
        *,
        configured: bool = True,
        response: str | None = None,
        error: AIProviderError | None = None,
        disabled_reason: str = "GenAI is disabled because OLLAMA_MODEL is not configured.",
    ) -> None:
        self._configured = configured
        self.response = response or (
            '{"findingId":"finding-ignored-by-service",'
            '"summary":"GenAI summary.",'
            '"riskExplanation":"GenAI risk explanation.",'
            '"migrationConsiderations":["GenAI migration step."],'
            '"suggestedTests":["GenAI test."],'
            '"limitations":["Generated from structured finding data only."]}'
        )
        self.error = error
        self._disabled_reason = disabled_reason
        self.prompts: list[str] = []

    @property
    def is_configured(self) -> bool:
        return self._configured

    @property
    def disabled_reason(self) -> str:
        return self._disabled_reason

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.response


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides() -> None:
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def use_provider(provider: FakeProvider) -> FakeProvider:
    app.dependency_overrides[get_ai_provider] = lambda: provider
    return provider


def finding_payload(
    *,
    finding_id: str = "finding-1",
    title: str = "RSA-OAEP usage detected in bcprov-jdk18on",
    crypto_asset_name: str = "bcprov-jdk18on",
    status: str = "QUANTUM_VULNERABLE",
    reason: str = "The algorithm is explicitly recognized as vulnerable.",
    algorithm: str | None = "RSA-OAEP",
    component_name: str | None = "bcprov-jdk18on",
    component_version: str | None = "1.78",
    recommendation: str = "Assess migration impact.",
    evidence: list[str] | None = None,
) -> dict:
    return {
        "finding": {
            "id": finding_id,
            "title": title,
            "cryptoAssetName": crypto_asset_name,
            "status": status,
            "reason": reason,
            "algorithm": algorithm,
            "componentName": component_name,
            "componentVersion": component_version,
            "recommendation": recommendation,
            "evidence": (
                evidence
                if evidence is not None
                else [f"property:evidra.crypto.algorithm={algorithm}"]
            ),
        }
    }


def finding_input(**overrides: object) -> FindingInput:
    payload = finding_payload(**overrides)["finding"]
    return FindingInput.model_validate(payload)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-service"}


def test_explains_quantum_vulnerable_finding_when_provider_is_disabled(
    client: TestClient,
) -> None:
    provider = use_provider(FakeProvider(configured=False))

    response = client.post("/findings/explain", json=finding_payload())

    body = response.json()
    assert response.status_code == 200
    assert body["findingId"] == "finding-1"
    assert body["summary"] == (
        "RSA-OAEP was detected in bcprov-jdk18on with status QUANTUM_VULNERABLE."
    )
    assert "classified as quantum-vulnerable" in body["riskExplanation"]
    assert "Map the affected code paths and external integrations." in body[
        "migrationConsiderations"
    ]
    assert "Verify old data remains readable or verifiable during migration." in body[
        "suggestedTests"
    ]
    assert "GenAI is disabled because OLLAMA_MODEL is not configured." in body["limitations"]
    assert any(
        limitation.startswith("Local RAG context used: pqc-threat-model")
        for limitation in body["limitations"]
    )
    assert provider.prompts == []


def test_explains_post_quantum_finding_when_provider_is_disabled(
    client: TestClient,
) -> None:
    use_provider(FakeProvider(configured=False))

    response = client.post(
        "/findings/explain",
        json=finding_payload(
            finding_id="finding-2",
            title="ML-KEM usage detected in pqc-provider",
            crypto_asset_name="pqc-provider",
            status="POST_QUANTUM",
            reason="The algorithm is explicitly recognized as post-quantum.",
            algorithm="ML-KEM",
            component_name="pqc-provider",
            component_version="0.1.0",
            recommendation="Validate interoperability.",
        ),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["findingId"] == "finding-2"
    assert "classified as post-quantum" in body["riskExplanation"]
    assert "Validate provider support and algorithm parameters." in body[
        "migrationConsiderations"
    ]
    assert "Test interoperability with configured providers." in body["suggestedTests"]


def test_explains_review_required_finding_when_provider_is_disabled(
    client: TestClient,
) -> None:
    use_provider(FakeProvider(configured=False))

    response = client.post(
        "/findings/explain",
        json=finding_payload(
            finding_id="finding-3",
            title="AES-GCM usage detected in crypto-utils",
            crypto_asset_name="crypto-utils",
            status="REVIEW_REQUIRED",
            reason="The algorithm is not explicitly classified yet.",
            algorithm="AES-GCM",
            component_name="crypto-utils",
            component_version="1.0.0",
            recommendation="Review manually.",
        ),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["findingId"] == "finding-3"
    assert "not explicitly classified" in body["riskExplanation"]
    assert "Confirm what the algorithm is used for." in body["migrationConsiderations"]
    assert "Add characterization tests before changing the implementation." in body[
        "suggestedTests"
    ]


def test_explains_finding_when_optional_details_are_missing(client: TestClient) -> None:
    use_provider(FakeProvider(configured=False))

    response = client.post(
        "/findings/explain",
        json=finding_payload(
            finding_id="finding-optional",
            title="RSA usage detected in RSA-2048",
            crypto_asset_name="RSA-2048",
            algorithm="RSA",
            component_name=None,
            component_version=None,
            recommendation="",
            evidence=[],
        ),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["findingId"] == "finding-optional"
    assert body["summary"] == "RSA was detected in RSA-2048 with status QUANTUM_VULNERABLE."
    assert "classified as quantum-vulnerable" in body["riskExplanation"]


def test_explanation_logic_uses_configured_provider(client: TestClient) -> None:
    provider = use_provider(FakeProvider())

    response = client.post(
        "/findings/explain",
        json=finding_payload(
            finding_id="finding-4",
            title="RSA usage detected in auth-service",
            crypto_asset_name="auth-service",
            algorithm="RSA",
            component_name="auth-service",
            component_version="2.1.0",
        ),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["findingId"] == "finding-4"
    assert body["summary"] == "GenAI summary."
    assert body["riskExplanation"] == "GenAI risk explanation."
    assert "GenAI migration step." in body["migrationConsiderations"]
    assert "GenAI test." in body["suggestedTests"]
    assert len(provider.prompts) == 1
    model_input = json.loads(provider.prompts[0].split("Input:\n", 1)[1])
    assert model_input["normalizedContext"]["algorithm"] == "RSA"
    assert any(
        snippet["id"] == "pqc-threat-model"
        for snippet in model_input["retrievedKnowledge"]
    )


def test_provider_failure_falls_back_to_deterministic_explanation(
    client: TestClient,
) -> None:
    use_provider(FakeProvider(error=AIProviderError("Provider failed.")))

    response = client.post(
        "/findings/explain",
        json=finding_payload(
            finding_id="finding-5",
            title="RSA usage detected in auth-service",
            crypto_asset_name="auth-service",
            algorithm="RSA",
            component_name="auth-service",
            component_version="2.1.0",
        ),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["findingId"] == "finding-5"
    assert "classified as quantum-vulnerable" in body["riskExplanation"]
    assert "GenAI explanation failed; deterministic fallback was used." in body["limitations"]
    assert "Provider failed." in body["limitations"]
    assert any(
        limitation.startswith("Local RAG context used: pqc-threat-model")
        for limitation in body["limitations"]
    )


def test_malformed_provider_response_falls_back_to_deterministic_explanation(
    client: TestClient,
) -> None:
    use_provider(FakeProvider(response="not-json"))

    response = client.post("/findings/explain", json=finding_payload(finding_id="finding-6"))

    body = response.json()
    assert response.status_code == 200
    assert body["findingId"] == "finding-6"
    assert "classified as quantum-vulnerable" in body["riskExplanation"]
    assert "GenAI explanation failed; deterministic fallback was used." in body["limitations"]
    assert "GenAI response handling failed: JSONDecodeError." in body["limitations"]


def test_ollama_provider_reads_configuration_and_invokes_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.test:11434/")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    httpx_post = Mock()
    httpx_response = Mock()
    httpx_response.json.return_value = {"response": '{"summary":"ok"}'}
    httpx_post.return_value = httpx_response
    monkeypatch.setattr("providers.httpx.post", httpx_post)

    provider = OllamaProvider()

    assert provider.is_configured is True
    assert provider.generate("prompt text") == '{"summary":"ok"}'
    httpx_post.assert_called_once()
    assert httpx_post.call_args.args[0] == "http://ollama.test:11434/api/generate"
    assert httpx_post.call_args.kwargs["json"] == {
        "model": "test-model",
        "stream": False,
        "format": "json",
        "prompt": "prompt text",
    }
    assert httpx_post.call_args.kwargs["timeout"] == 30


def test_ollama_provider_reports_unconfigured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OLLAMA_MODEL", "")

    provider = OllamaProvider()

    assert provider.is_configured is False
    assert provider.disabled_reason == "GenAI is disabled because OLLAMA_MODEL is not configured."


def test_ollama_provider_wraps_provider_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("providers.httpx.post", Mock(side_effect=RuntimeError("network unavailable")))

    provider = OllamaProvider(model="test-model")

    with pytest.raises(AIProviderError, match="GenAI response handling failed: RuntimeError."):
        provider.generate("prompt text")


def test_retrieves_local_context_for_review_required_algorithms() -> None:
    context = retrieve_context(
        finding_input(
            finding_id="finding-review",
            title="AES-GCM usage detected in crypto-utils",
            crypto_asset_name="crypto-utils",
            status="REVIEW_REQUIRED",
            reason="The algorithm is not explicitly classified yet.",
            algorithm="AES-GCM",
        ),
        "AES-GCM",
    )

    assert [snippet["id"] for snippet in context] == ["review-required"]


def test_deterministic_explanation_reports_missing_local_context() -> None:
    finding = finding_input(
        finding_id="finding-unknown",
        title="CustomCipher usage detected in local-lib",
        crypto_asset_name="local-lib",
        status="REVIEW_REQUIRED",
        reason="The algorithm is not explicitly classified yet.",
        algorithm="CustomCipher",
        component_name="local-lib",
    )

    explanation = build_deterministic_explanation(
        finding=finding,
        algorithm="CustomCipher",
        component="local-lib",
        retrieved_context=[],
        extra_limitations=["GenAI is disabled because OLLAMA_MODEL is not configured."],
    )

    assert explanation.findingId == "finding-unknown"
    assert "not explicitly classified" in explanation.riskExplanation
    assert "No local RAG context matched this finding." in explanation.limitations


def test_rejects_invalid_explain_request(client: TestClient) -> None:
    response = client.post("/findings/explain", json={"finding": {"id": "finding-1"}})

    assert response.status_code == 422
