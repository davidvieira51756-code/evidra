from fastapi import FastAPI
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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="ai-service")


@app.post("/findings/explain", response_model=ExplainFindingResponse)
def explain_finding(request: ExplainFindingRequest) -> ExplainFindingResponse:
    finding = request.finding
    algorithm = finding.algorithm or "unknown algorithm"
    component = finding.componentName or finding.cryptoAssetName

    return ExplainFindingResponse(
        findingId=finding.id,
        summary=build_summary(finding, algorithm, component),
        riskExplanation=build_risk_explanation(finding, algorithm),
        migrationConsiderations=build_migration_considerations(finding.status),
        suggestedTests=build_suggested_tests(finding.status),
        limitations=[
            "This explanation is generated from structured finding data only.",
            "It does not inspect source code, historical data, certificates, keystores, or runtime configuration.",
            "It is deterministic placeholder output and does not use GenAI or RAG yet.",
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
