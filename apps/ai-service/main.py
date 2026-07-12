import json
import os

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


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
    recommendation: str
    evidence: list[str]


class ExplainFindingRequest(BaseModel):
    finding: FindingInput


class ExplainFindingResponse(BaseModel):
    findingId: str
    summary: str
    riskExplanation: str
    migrationConsiderations: list[str]
    suggestedTests: list[str]
    limitations: list[str]


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
    genai_response = build_genai_explanation(finding, algorithm, component)

    if genai_response is not None:
        return genai_response

    return build_deterministic_explanation(
        finding=finding,
        algorithm=algorithm,
        component=component,
        extra_limitations=["GenAI is disabled because OPENAI_API_KEY is not configured."],
    )


def build_genai_explanation(
    finding: FindingInput,
    algorithm: str,
    component: str,
) -> ExplainFindingResponse | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        response = httpx.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=build_openai_payload(finding, algorithm, component),
            timeout=30,
        )
        response.raise_for_status()
        return parse_openai_response(response.json(), finding.id)
    except Exception:
        return build_deterministic_explanation(
            finding=finding,
            algorithm=algorithm,
            component=component,
            extra_limitations=["GenAI explanation failed; deterministic fallback was used."],
        )


def build_openai_payload(finding: FindingInput, algorithm: str, component: str) -> dict:
    return {
        "model": os.getenv("OPENAI_MODEL", "gpt-4.1"),
        "instructions": (
            "You are Evidra's cryptography migration analyst. Explain a single CBOM finding. "
            "Use only the structured finding data provided by the application. Do not claim to "
            "have inspected source code, certificates, keystores, runtime configuration, or logs. "
            "Keep the response practical, concise, and conservative."
        ),
        "input": json.dumps(
            {
                "finding": finding.model_dump(),
                "normalizedContext": {
                    "algorithm": algorithm,
                    "component": component,
                },
            }
        ),
        "temperature": 0.2,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "evidra_finding_explanation",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "findingId",
                        "summary",
                        "riskExplanation",
                        "migrationConsiderations",
                        "suggestedTests",
                        "limitations",
                    ],
                    "properties": {
                        "findingId": {"type": "string"},
                        "summary": {"type": "string"},
                        "riskExplanation": {"type": "string"},
                        "migrationConsiderations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 5,
                        },
                        "suggestedTests": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 5,
                        },
                        "limitations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                            "maxItems": 5,
                        },
                    },
                },
            }
        },
    }


def parse_openai_response(response_body: dict, expected_finding_id: str) -> ExplainFindingResponse:
    output_text = response_body.get("output_text")

    if output_text is None:
        output = response_body["output"]
        output_text = output[0]["content"][0]["text"]

    parsed = json.loads(output_text)
    parsed["findingId"] = expected_finding_id
    return ExplainFindingResponse.model_validate(parsed)


def build_deterministic_explanation(
    finding: FindingInput,
    algorithm: str,
    component: str,
    extra_limitations: list[str],
) -> ExplainFindingResponse:
    return ExplainFindingResponse(
        findingId=finding.id,
        summary=build_summary(finding, algorithm, component),
        riskExplanation=build_risk_explanation(finding, algorithm),
        migrationConsiderations=build_migration_considerations(finding.status),
        suggestedTests=build_suggested_tests(finding.status),
        limitations=[
            "This explanation is generated from structured finding data only.",
            "It does not inspect source code, historical data, certificates, keystores, or runtime configuration.",
            *extra_limitations,
        ],
    )


def build_summary(finding: FindingInput, algorithm: str, component: str) -> str:
    return f"{algorithm} was detected in {component} with status {finding.status}."


def build_risk_explanation(finding: FindingInput, algorithm: str) -> str:
    if finding.status == "QUANTUM_VULNERABLE":
        return (
            f"{algorithm} is classified as quantum-vulnerable by the deterministic rules. "
            "Before migration, identify where it is used, what data depends on it, and whether "
            "backward compatibility is required."
        )

    if finding.status == "POST_QUANTUM":
        return (
            f"{algorithm} is classified as post-quantum by the deterministic rules. "
            "The main risk is not quantum exposure, but incorrect integration, key management, "
            "interoperability, payload size, or performance regressions."
        )

    return (
        f"{algorithm} is not explicitly classified by the deterministic rules. "
        "It should be reviewed manually before assigning migration priority."
    )


def build_migration_considerations(status: str) -> list[str]:
    if status == "QUANTUM_VULNERABLE":
        return [
            "Map the affected code paths and external integrations.",
            "Check whether existing encrypted or signed historical data must remain readable or verifiable.",
            "Prefer a staged migration plan with versioned formats and compatibility tests.",
            "Consider post-quantum or hybrid designs only after impact is understood.",
        ]

    if status == "POST_QUANTUM":
        return [
            "Validate provider support and algorithm parameters.",
            "Check interoperability with dependent systems.",
            "Measure payload size, key size, and performance impact.",
        ]

    return [
        "Confirm what the algorithm is used for.",
        "Determine whether the usage is encryption, signing, key exchange, hashing, or authentication.",
        "Classify the usage before planning migration work.",
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
