import unittest
from pathlib import Path
import sys

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
            "It is deterministic placeholder output and does not use GenAI or RAG yet.",
            body["limitations"],
        )

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

    def test_rejects_invalid_explain_request(self) -> None:
        response = self.client.post("/findings/explain", json={"finding": {"id": "finding-1"}})

        self.assertEqual(422, response.status_code)


if __name__ == "__main__":
    unittest.main()
