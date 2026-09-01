import json
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()


class HealthResponse(BaseModel):
    status: str
    service: str


class FindingInput(BaseModel):
    id: str
    title: str
    cryptoAssetName: str
    status: str
    reason: str
    algorithm: str | None = None
    componentName: str | None = None
    componentVersion: str | None = None
    recommendation: str = ""
    evidence: list[str] = Field(default_factory=list)


class ExplainFindingRequest(BaseModel):
    finding: FindingInput


class ExplainFindingResponse(BaseModel):
    findingId: str
    summary: str
    riskExplanation: str
    migrationConsiderations: list[str]
    suggestedTests: list[str]
    limitations: list[str]


KNOWLEDGE_SNIPPETS = [
    {
        "id": "pqc-threat-model",
        "title": "Quantum risk for public-key cryptography",
        "keywords": ["QUANTUM_VULNERABLE", "RSA", "ECDSA", "ECDH", "DSA", "DH"],
        "text": (
            "RSA, ECDSA, ECDH, DSA, and DH are public-key algorithms considered vulnerable "
            "to cryptographically relevant quantum computers. Migration planning should identify "
            "affected protocols, data formats, signatures, certificates, key exchange flows, and "
            "long-lived encrypted or signed data."
        ),
    },
    {
        "id": "kem-migration",
        "title": "KEM migration considerations",
        "keywords": ["ML-KEM", "KEM", "RSA-OAEP", "key exchange", "encapsulation"],
        "text": (
            "ML-KEM is a post-quantum key encapsulation mechanism. It is not a drop-in replacement "
            "for every RSA-OAEP usage; teams should check protocol shape, payload sizes, provider "
            "support, versioned ciphertext formats, and rollback compatibility."
        ),
    },
    {
        "id": "signature-migration",
        "title": "Signature migration considerations",
        "keywords": ["ML-DSA", "SLH-DSA", "ECDSA", "DSA", "signature", "signing"],
        "text": (
            "ML-DSA and SLH-DSA are post-quantum signature options. Migration should consider "
            "signature size, verification performance, certificate or token formats, interoperability, "
            "and whether old signatures must remain verifiable."
        ),
    },
    {
        "id": "review-required",
        "title": "Manual review for unclassified algorithms",
        "keywords": ["REVIEW_REQUIRED", "AES", "SHA", "HMAC", "unknown"],
        "text": (
            "Algorithms classified as REVIEW_REQUIRED need context before migration priority is assigned. "
            "For symmetric encryption, hashing, and authentication, quantum risk depends on usage, key "
            "sizes, protocol context, and security requirements."
        ),
    },
]


app = FastAPI(title="Evidra AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="ai-service")


@app.post("/findings/explain", response_model=ExplainFindingResponse)
def explain_finding(request: ExplainFindingRequest) -> ExplainFindingResponse:
    finding = request.finding
    algorithm = finding.algorithm or "unknown algorithm"
    component = finding.componentName or finding.cryptoAssetName
    retrieved_context = retrieve_context(finding, algorithm)
    llm_response = build_llm_explanation(finding, algorithm, component, retrieved_context)

    if llm_response is not None:
        return llm_response

    return build_deterministic_explanation(
        finding=finding,
        algorithm=algorithm,
        component=component,
        retrieved_context=retrieved_context,
        extra_limitations=["GenAI is disabled because OLLAMA_MODEL is not configured."],
    )


def build_llm_explanation(
    finding: FindingInput,
    algorithm: str,
    component: str,
    retrieved_context: list[dict],
) -> ExplainFindingResponse | None:
    model = os.getenv("OLLAMA_MODEL")
    if not model:
        return None

    try:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        response = httpx.post(
            f"{base_url}/api/generate",
            json=build_ollama_payload(model, finding, algorithm, component, retrieved_context),
            timeout=30,
        )
        response.raise_for_status()
        return parse_ollama_response(response.json(), finding.id)
    except Exception as exception:
        return build_deterministic_explanation(
            finding=finding,
            algorithm=algorithm,
            component=component,
            retrieved_context=retrieved_context,
            extra_limitations=[
                "GenAI explanation failed; deterministic fallback was used.",
                describe_llm_failure(exception),
            ],
        )


def build_ollama_payload(
    model: str,
    finding: FindingInput,
    algorithm: str,
    component: str,
    retrieved_context: list[dict],
) -> dict:
    return {
        "model": model,
        "stream": False,
        "format": "json",
        "prompt": (
            "You are Evidra's cryptography migration analyst. Explain a single CBOM finding.\n"
            "Use only the structured finding data and retrieved knowledge snippets provided by the "
            "application. Do not claim to have inspected source code, certificates, keystores, runtime "
            "configuration, or logs. Keep the response practical, concise, and conservative. When "
            "retrieved snippets are insufficient, say so in limitations.\n\n"
            "Return only valid JSON with this exact shape:\n"
            "{\n"
            '  "findingId": "string",\n'
            '  "summary": "string",\n'
            '  "riskExplanation": "string",\n'
            '  "migrationConsiderations": ["string"],\n'
            '  "suggestedTests": ["string"],\n'
            '  "limitations": ["string"]\n'
            "}\n\n"
            "Input:\n"
            + json.dumps(
                {
                    "finding": finding.model_dump(),
                    "normalizedContext": {
                        "algorithm": algorithm,
                        "component": component,
                    },
                    "retrievedKnowledge": retrieved_context,
                },
                ensure_ascii=True,
            )
        ),
    }


def describe_llm_failure(exception: Exception) -> str:
    if isinstance(exception, httpx.HTTPStatusError):
        response_text = exception.response.text.replace("\n", " ")
        return (
            f"Ollama API returned HTTP {exception.response.status_code}: "
            f"{truncate(response_text, 240)}"
        )

    if isinstance(exception, httpx.RequestError):
        return f"Ollama API request failed before receiving a response: {exception.__class__.__name__}."

    return f"GenAI response handling failed: {exception.__class__.__name__}."


def truncate(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return value[: max_length - 3] + "..."


def retrieve_context(finding: FindingInput, algorithm: str, limit: int = 3) -> list[dict]:
    query_terms = {
        finding.status.upper(),
        algorithm.upper(),
        *(word.upper() for word in finding.title.replace("-", " ").split()),
        *(word.upper() for word in finding.reason.replace("-", " ").split()),
    }

    scored_snippets = []
    for snippet in KNOWLEDGE_SNIPPETS:
        keywords = {keyword.upper() for keyword in snippet["keywords"]}
        score = len(query_terms.intersection(keywords))
        if score > 0:
            scored_snippets.append((score, snippet))

    scored_snippets.sort(key=lambda item: item[0], reverse=True)

    return [
        {
            "id": snippet["id"],
            "title": snippet["title"],
            "text": snippet["text"],
        }
        for _, snippet in scored_snippets[:limit]
    ]


def parse_ollama_response(response_body: dict, expected_finding_id: str) -> ExplainFindingResponse:
    parsed = json.loads(response_body["response"])
    parsed["findingId"] = expected_finding_id
    return ExplainFindingResponse.model_validate(parsed)


def build_deterministic_explanation(
    finding: FindingInput,
    algorithm: str,
    component: str,
    retrieved_context: list[dict],
    extra_limitations: list[str],
) -> ExplainFindingResponse:
    return ExplainFindingResponse(
        findingId=finding.id,
        summary=build_summary(finding, algorithm, component),
        riskExplanation=build_risk_explanation(finding, algorithm, retrieved_context),
        migrationConsiderations=build_migration_considerations(finding.status, retrieved_context),
        suggestedTests=build_suggested_tests(finding.status),
        limitations=[
            "This explanation is generated from structured finding data only.",
            "It does not inspect source code, historical data, certificates, keystores, or runtime configuration.",
            *build_retrieval_limitations(retrieved_context),
            *extra_limitations,
        ],
    )


def build_summary(finding: FindingInput, algorithm: str, component: str) -> str:
    return f"{algorithm} was detected in {component} with status {finding.status}."


def build_risk_explanation(
    finding: FindingInput,
    algorithm: str,
    retrieved_context: list[dict],
) -> str:
    if finding.status == "QUANTUM_VULNERABLE":
        explanation = (
            f"{algorithm} is classified as quantum-vulnerable by the deterministic rules. "
            "Before migration, identify where it is used, what data depends on it, and whether "
            "backward compatibility is required."
        )
        return append_retrieved_context(explanation, retrieved_context)

    if finding.status == "POST_QUANTUM":
        explanation = (
            f"{algorithm} is classified as post-quantum by the deterministic rules. "
            "The main risk is not quantum exposure, but incorrect integration, key management, "
            "interoperability, payload size, or performance regressions."
        )
        return append_retrieved_context(explanation, retrieved_context)

    explanation = (
        f"{algorithm} is not explicitly classified by the deterministic rules. "
        "It should be reviewed manually before assigning migration priority."
    )
    return append_retrieved_context(explanation, retrieved_context)


def append_retrieved_context(explanation: str, retrieved_context: list[dict]) -> str:
    if not retrieved_context:
        return explanation

    return explanation + " Retrieved context: " + retrieved_context[0]["text"]


def build_migration_considerations(status: str, retrieved_context: list[dict]) -> list[str]:
    if status == "QUANTUM_VULNERABLE":
        considerations = [
            "Map the affected code paths and external integrations.",
            "Check whether existing encrypted or signed historical data must remain readable or verifiable.",
            "Prefer a staged migration plan with versioned formats and compatibility tests.",
            "Consider post-quantum or hybrid designs only after impact is understood.",
        ]
        return add_retrieval_consideration(considerations, retrieved_context)

    if status == "POST_QUANTUM":
        considerations = [
            "Validate provider support and algorithm parameters.",
            "Check interoperability with dependent systems.",
            "Measure payload size, key size, and performance impact.",
        ]
        return add_retrieval_consideration(considerations, retrieved_context)

    considerations = [
        "Confirm what the algorithm is used for.",
        "Determine whether the usage is encryption, signing, key exchange, hashing, or authentication.",
        "Classify the usage before planning migration work.",
    ]
    return add_retrieval_consideration(considerations, retrieved_context)


def add_retrieval_consideration(considerations: list[str], retrieved_context: list[dict]) -> list[str]:
    if not retrieved_context:
        return considerations

    return [
        *considerations,
        "Review local RAG context: " + ", ".join(snippet["title"] for snippet in retrieved_context),
    ]


def build_retrieval_limitations(retrieved_context: list[dict]) -> list[str]:
    if not retrieved_context:
        return ["No local RAG context matched this finding."]

    return [
        "Local RAG context used: " + ", ".join(snippet["id"] for snippet in retrieved_context)
    ]


def build_suggested_tests(status: str) -> list[str]:
    common_tests = [
        "Add regression tests around the affected cryptographic workflow.",
        "Test invalid keys, corrupted payloads, and unsupported versions.",
    ]

    if status == "QUANTUM_VULNERABLE":
        return [
            "Verify old data remains readable or verifiable during migration.",
            "Test new and old cryptographic formats side by side.",
            "Benchmark latency and payload size before and after migration.",
            *common_tests,
        ]

    if status == "POST_QUANTUM":
        return [
            "Test interoperability with configured providers.",
            "Benchmark key generation, encapsulation, signing, or verification operations.",
            *common_tests,
        ]

    return [
        "Add characterization tests before changing the implementation.",
        *common_tests,
    ]
