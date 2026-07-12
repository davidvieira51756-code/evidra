import json
import unittest
from pathlib import Path
import sys
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import app


class AiServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health_returns_ok(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"status": "ok", "service": "ai-service"}, response.json())

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_explains_quantum_vulnerable_finding(self) -> None:
        response = self.client.post(
            "/findings/explain",
            json={
                "finding": {
                    "id": "finding-1",
                    "title": "RSA-OAEP usage detected in bcprov-jdk18on",
                    "cryptoAssetName": "bcprov-jdk18on",
                    "status": "QUANTUM_VULNERABLE",
                    "reason": "The algorithm is explicitly recognized as vulnerable.",
                    "algorithm": "RSA-OAEP",
                    "componentName": "bcprov-jdk18on",
                    "componentVersion": "1.78",
                    "recommendation": "Assess migration impact.",
                    "evidence": ["property:evidra.crypto.algorithm=RSA-OAEP"],
                }
            },
        )

        body = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("finding-1", body["findingId"])
        self.assertEqual(
            "RSA-OAEP was detected in bcprov-jdk18on with status QUANTUM_VULNERABLE.",
            body["summary"],
        )
        self.assertIn("classified as quantum-vulnerable", body["riskExplanation"])
        self.assertIn(
            "Map the affected code paths and external integrations.",
            body["migrationConsiderations"],
        )
        self.assertIn(
            "Verify old data remains readable or verifiable during migration.",
            body["suggestedTests"],
        )
        self.assertIn(
            "GenAI is disabled because OPENAI_API_KEY is not configured.",
            body["limitations"],
        )
        self.assertTrue(
            any(
                limitation.startswith("Local RAG context used: pqc-threat-model")
                for limitation in body["limitations"]
            )
        )
        self.assertTrue(
            any(
                item.startswith("Review local RAG context:")
                for item in body["migrationConsiderations"]
            )
        )

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_explains_post_quantum_finding(self) -> None:
        response = self.client.post(
            "/findings/explain",
            json={
                "finding": {
                    "id": "finding-2",
                    "title": "ML-KEM usage detected in pqc-provider",
                    "cryptoAssetName": "pqc-provider",
                    "status": "POST_QUANTUM",
                    "reason": "The algorithm is explicitly recognized as post-quantum.",
                    "algorithm": "ML-KEM",
                    "componentName": "pqc-provider",
                    "componentVersion": "0.1.0",
                    "recommendation": "Validate interoperability.",
                    "evidence": ["property:evidra.crypto.algorithm=ML-KEM"],
                }
            },
        )

        body = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("finding-2", body["findingId"])
        self.assertIn("classified as post-quantum", body["riskExplanation"])
        self.assertIn(
            "Validate provider support and algorithm parameters.",
            body["migrationConsiderations"],
        )
        self.assertIn(
            "Test interoperability with configured providers.",
            body["suggestedTests"],
        )

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_explains_review_required_finding(self) -> None:
        response = self.client.post(
            "/findings/explain",
            json={
                "finding": {
                    "id": "finding-3",
                    "title": "AES-GCM usage detected in crypto-utils",
                    "cryptoAssetName": "crypto-utils",
                    "status": "REVIEW_REQUIRED",
                    "reason": "The algorithm is not explicitly classified yet.",
                    "algorithm": "AES-GCM",
                    "componentName": "crypto-utils",
                    "componentVersion": "1.0.0",
                    "recommendation": "Review manually.",
                    "evidence": ["property:evidra.crypto.algorithm=AES-GCM"],
                }
            },
        )

        body = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("finding-3", body["findingId"])
        self.assertIn("not explicitly classified", body["riskExplanation"])
        self.assertIn("Confirm what the algorithm is used for.", body["migrationConsiderations"])
        self.assertIn(
            "Add characterization tests before changing the implementation.",
            body["suggestedTests"],
        )

    @patch.dict("os.environ", {"OPENAI_API_KEY": ""})
    def test_explains_finding_when_optional_details_are_missing(self) -> None:
        response = self.client.post(
            "/findings/explain",
            json={
                "finding": {
                    "id": "finding-optional",
                    "title": "RSA usage detected in RSA-2048",
                    "cryptoAssetName": "RSA-2048",
                    "status": "QUANTUM_VULNERABLE",
                    "reason": "The algorithm is explicitly recognized as vulnerable.",
                    "algorithm": "RSA",
                    "componentName": "RSA-2048",
                }
            },
        )

        body = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("finding-optional", body["findingId"])
        self.assertIn("classified as quantum-vulnerable", body["riskExplanation"])

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"})
    @patch("main.httpx.post")
    def test_explains_finding_with_genai_when_api_key_is_configured(self, httpx_post: Mock) -> None:
        httpx_response = Mock()
        httpx_response.json.return_value = {
            "output_text": (
                '{"findingId":"finding-ignored-by-service",'
                '"summary":"GenAI summary.",'
                '"riskExplanation":"GenAI risk explanation.",'
                '"migrationConsiderations":["GenAI migration step."],'
                '"suggestedTests":["GenAI test."],'
                '"limitations":["Generated from structured finding data only."]}'
            )
        }
        httpx_post.return_value = httpx_response

        response = self.client.post(
            "/findings/explain",
            json={
                "finding": {
                    "id": "finding-4",
                    "title": "RSA usage detected in auth-service",
                    "cryptoAssetName": "auth-service",
                    "status": "QUANTUM_VULNERABLE",
                    "reason": "The algorithm is explicitly recognized as vulnerable.",
                    "algorithm": "RSA",
                    "componentName": "auth-service",
                    "componentVersion": "2.1.0",
                    "recommendation": "Assess migration impact.",
                    "evidence": ["property:evidra.crypto.algorithm=RSA"],
                }
            },
        )

        body = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("finding-4", body["findingId"])
        self.assertEqual("GenAI summary.", body["summary"])
        self.assertEqual("GenAI risk explanation.", body["riskExplanation"])
        self.assertIn("GenAI migration step.", body["migrationConsiderations"])
        self.assertIn("GenAI test.", body["suggestedTests"])
        httpx_post.assert_called_once()
        self.assertEqual(
            "test-model",
            httpx_post.call_args.kwargs["json"]["model"],
        )
        model_input = json.loads(httpx_post.call_args.kwargs["json"]["input"])
        self.assertEqual("RSA", model_input["normalizedContext"]["algorithm"])
        self.assertTrue(
            any(
                snippet["id"] == "pqc-threat-model"
                for snippet in model_input["retrievedKnowledge"]
            )
        )

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    @patch("main.httpx.post")
    def test_falls_back_to_deterministic_explanation_when_genai_fails(
        self,
        httpx_post: Mock,
    ) -> None:
        httpx_post.side_effect = RuntimeError("network unavailable")

        response = self.client.post(
            "/findings/explain",
            json={
                "finding": {
                    "id": "finding-5",
                    "title": "RSA usage detected in auth-service",
                    "cryptoAssetName": "auth-service",
                    "status": "QUANTUM_VULNERABLE",
                    "reason": "The algorithm is explicitly recognized as vulnerable.",
                    "algorithm": "RSA",
                    "componentName": "auth-service",
                    "componentVersion": "2.1.0",
                    "recommendation": "Assess migration impact.",
                    "evidence": ["property:evidra.crypto.algorithm=RSA"],
                }
            },
        )

        body = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("finding-5", body["findingId"])
        self.assertIn("classified as quantum-vulnerable", body["riskExplanation"])
        self.assertIn(
            "GenAI explanation failed; deterministic fallback was used.",
            body["limitations"],
        )
        self.assertIn(
            "GenAI response handling failed: RuntimeError.",
            body["limitations"],
        )
        self.assertTrue(
            any(
                limitation.startswith("Local RAG context used: pqc-threat-model")
                for limitation in body["limitations"]
            )
        )

    def test_rejects_invalid_explain_request(self) -> None:
        response = self.client.post("/findings/explain", json={"finding": {"id": "finding-1"}})

        self.assertEqual(422, response.status_code)


if __name__ == "__main__":
    unittest.main()
