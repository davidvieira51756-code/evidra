from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_SERVICE_PATH = REPO_ROOT / "apps" / "ai-service"
DEFAULT_DATASET_PATH = REPO_ROOT / "evals" / "datasets" / "crypto-findings-v1.json"
DEFAULT_RESULTS_DIR = REPO_ROOT / "evals" / "results"
RETRIEVAL_STRATEGY = "keyword"

if str(AI_SERVICE_PATH) not in sys.path:
    sys.path.insert(0, str(AI_SERVICE_PATH))

from knowledge import load_knowledge_corpus  # noqa: E402
from main import FindingInput, retrieve_context  # noqa: E402


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caseId: str
    category: str
    finding: FindingInput
    expectedSourceIds: list[str] = Field(default_factory=list)
    forbiddenSourceIds: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("caseId", "category")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("expectedSourceIds", "forbiddenSourceIds")
    @classmethod
    def require_unique_source_ids(cls, value: list[str]) -> list[str]:
        if any(not item.strip() for item in value):
            raise ValueError("source IDs must not be empty")
        if len(value) != len(set(value)):
            raise ValueError("source IDs must be unique")
        return value


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datasetId: str
    description: str
    retrievalStrategy: str
    cases: list[EvaluationCase]

    @field_validator("datasetId", "description", "retrievalStrategy")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def require_unique_case_ids(self) -> "EvaluationDataset":
        case_ids = [case.caseId for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("case IDs must be unique")
        if not self.cases:
            raise ValueError("must contain at least one case")
        return self


class CaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caseId: str
    category: str
    expectedSourceIds: list[str]
    forbiddenSourceIds: list[str]
    retrievedSourceIds: list[str]
    retrievedChunkIds: list[str]
    matchedTermsByChunk: dict[str, list[str]]
    hit: bool | None
    noSourceExpected: bool
    noSourceCorrect: bool | None
    sourcePrecision: float | None
    sourceRecall: float | None
    sourceF1: float | None
    missingSourceIds: list[str]
    unexpectedSourceIds: list[str]
    forbiddenRetrievedSourceIds: list[str]
    passed: bool
    notes: str


def load_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> EvaluationDataset:
    dataset_path = Path(path)
    with dataset_path.open(encoding="utf-8") as dataset_file:
        dataset = EvaluationDataset.model_validate(json.load(dataset_file))

    validate_dataset_source_ids(dataset)
    return dataset


def validate_dataset_source_ids(dataset: EvaluationDataset) -> None:
    known_source_ids = {
        document.source_id
        for document in load_knowledge_corpus().documents
    }

    invalid_references: list[str] = []
    for case in dataset.cases:
        referenced_source_ids = [*case.expectedSourceIds, *case.forbiddenSourceIds]
        for source_id in referenced_source_ids:
            if source_id not in known_source_ids:
                invalid_references.append(f"{case.caseId}: {source_id}")

    if invalid_references:
        raise ValueError(
            "dataset references unknown source IDs: " + ", ".join(invalid_references)
        )


def evaluate_dataset(dataset: EvaluationDataset) -> dict[str, Any]:
    case_results = [evaluate_case(case) for case in dataset.cases]
    return {
        "datasetId": dataset.datasetId,
        "retrievalStrategy": RETRIEVAL_STRATEGY,
        "caseCount": len(dataset.cases),
        "metrics": calculate_metrics(case_results),
        "cases": [case_result.model_dump() for case_result in case_results],
    }


def evaluate_case(case: EvaluationCase) -> CaseResult:
    algorithm = case.finding.algorithm or "unknown algorithm"
    retrieval_results = retrieve_context(case.finding, algorithm)
    retrieved_source_ids = unique_preserving_order(
        result.document.source_id for result in retrieval_results
    )
    retrieved_chunk_ids = [result.chunk.chunk_id for result in retrieval_results]
    matched_terms_by_chunk = {
        result.chunk.chunk_id: result.matched_terms
        for result in retrieval_results
    }

    expected = set(case.expectedSourceIds)
    retrieved = set(retrieved_source_ids)
    forbidden = set(case.forbiddenSourceIds)
    true_positive_count = len(expected.intersection(retrieved))
    no_source_expected = not expected

    source_precision = None
    source_recall = None
    source_f1 = None
    hit = None
    no_source_correct = None

    if no_source_expected:
        no_source_correct = len(retrieved_source_ids) == 0
    else:
        hit = true_positive_count > 0
        source_precision = (
            true_positive_count / len(retrieved_source_ids)
            if retrieved_source_ids
            else 0.0
        )
        source_recall = true_positive_count / len(case.expectedSourceIds)
        source_f1 = calculate_f1(source_precision, source_recall)

    missing_source_ids = sorted(expected.difference(retrieved))
    unexpected_source_ids = sorted(retrieved.difference(expected))
    forbidden_retrieved_source_ids = sorted(forbidden.intersection(retrieved))
    passed = (
        no_source_correct is True
        if no_source_expected
        else not missing_source_ids and not forbidden_retrieved_source_ids
    )

    return CaseResult(
        caseId=case.caseId,
        category=case.category,
        expectedSourceIds=case.expectedSourceIds,
        forbiddenSourceIds=case.forbiddenSourceIds,
        retrievedSourceIds=retrieved_source_ids,
        retrievedChunkIds=retrieved_chunk_ids,
        matchedTermsByChunk=matched_terms_by_chunk,
        hit=hit,
        noSourceExpected=no_source_expected,
        noSourceCorrect=no_source_correct,
        sourcePrecision=round_metric(source_precision),
        sourceRecall=round_metric(source_recall),
        sourceF1=round_metric(source_f1),
        missingSourceIds=missing_source_ids,
        unexpectedSourceIds=unexpected_source_ids,
        forbiddenRetrievedSourceIds=forbidden_retrieved_source_ids,
        passed=passed,
        notes=case.notes,
    )


def calculate_metrics(case_results: list[CaseResult]) -> dict[str, Any]:
    expected_source_cases = [
        case_result for case_result in case_results if not case_result.noSourceExpected
    ]
    no_source_cases = [
        case_result for case_result in case_results if case_result.noSourceExpected
    ]

    hit_count = sum(1 for case_result in expected_source_cases if case_result.hit)
    true_positive_count = sum(
        len(set(case_result.expectedSourceIds).intersection(case_result.retrievedSourceIds))
        for case_result in case_results
    )
    retrieved_count = sum(len(case_result.retrievedSourceIds) for case_result in case_results)
    expected_count = sum(len(case_result.expectedSourceIds) for case_result in case_results)
    no_source_correct_count = sum(
        1 for case_result in no_source_cases if case_result.noSourceCorrect
    )

    source_precision = (
        true_positive_count / retrieved_count
        if retrieved_count
        else None
    )
    source_recall = (
        true_positive_count / expected_count
        if expected_count
        else None
    )

    return {
        "retrievalHitRate": {
            "value": round_metric(hit_count / len(expected_source_cases))
            if expected_source_cases
            else None,
            "hitCases": hit_count,
            "evaluatedCases": len(expected_source_cases),
            "definition": "Cases with expected sources where at least one expected source ID was retrieved.",
        },
        "sourcePrecision": {
            "value": round_metric(source_precision),
            "truePositiveSourceIds": true_positive_count,
            "retrievedSourceIds": retrieved_count,
            "definition": "Expected retrieved source IDs divided by all retrieved source IDs, counted per case.",
        },
        "sourceRecall": {
            "value": round_metric(source_recall),
            "truePositiveSourceIds": true_positive_count,
            "expectedSourceIds": expected_count,
            "definition": "Expected retrieved source IDs divided by expected source IDs, counted per case.",
        },
        "sourceF1": {
            "value": round_metric(calculate_f1(source_precision, source_recall)),
            "definition": "Harmonic mean of source precision and source recall when both are defined.",
        },
        "noSourceCorrectness": {
            "value": round_metric(no_source_correct_count / len(no_source_cases))
            if no_source_cases
            else None,
            "correctCases": no_source_correct_count,
            "evaluatedCases": len(no_source_cases),
            "definition": "Cases with no expected sources where retrieval returned no sources.",
        },
    }


def run_baseline_evaluation(
    *,
    dataset_path: str | Path = DEFAULT_DATASET_PATH,
    output_dir: str | Path = DEFAULT_RESULTS_DIR,
    output_path: str | Path | None = None,
    overwrite: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    dataset = load_dataset(dataset_path)
    evaluated = evaluate_dataset(dataset)
    started_at = datetime.now(UTC).replace(microsecond=0)
    created_at = started_at.isoformat()
    resolved_run_id = run_id or started_at.strftime("%Y%m%dT%H%M%SZ")
    result_path = resolve_result_path(
        dataset_id=dataset.datasetId,
        output_dir=output_dir,
        output_path=output_path,
        run_id=resolved_run_id,
    )
    result = {
        "runId": resolved_run_id,
        "createdAt": created_at,
        "datasetId": evaluated["datasetId"],
        "datasetPath": display_path(Path(dataset_path)),
        "retrievalStrategy": evaluated["retrievalStrategy"],
        "caseCount": evaluated["caseCount"],
        "metrics": evaluated["metrics"],
        "cases": evaluated["cases"],
        "resultPath": display_path(result_path),
    }

    write_result(result, result_path, overwrite=overwrite)
    return result


def resolve_result_path(
    *,
    dataset_id: str,
    output_dir: str | Path,
    output_path: str | Path | None,
    run_id: str,
) -> Path:
    if output_path is not None:
        return Path(output_path)

    return Path(output_dir) / f"{run_id}-{dataset_id}-{RETRIEVAL_STRATEGY}.json"


def write_result(result: dict[str, Any], path: Path, *, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"result file already exists: {path}")

    with path.open("w", encoding="utf-8") as result_file:
        json.dump(result, result_file, indent=2)
        result_file.write("\n")


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def print_summary(result: dict[str, Any]) -> None:
    metrics = result["metrics"]
    print(f"Dataset: {result['datasetId']}")
    print(f"Retrieval strategy: {result['retrievalStrategy']}")
    print(f"Cases: {result['caseCount']}")
    print_metric("Retrieval hit rate", metrics["retrievalHitRate"])
    print_metric("Source precision", metrics["sourcePrecision"])
    print_metric("Source recall", metrics["sourceRecall"])
    print_metric("Source F1", metrics["sourceF1"])
    print_metric("No-source correctness", metrics["noSourceCorrectness"])

    weak_cases = [
        case_result
        for case_result in result["cases"]
        if not case_result["passed"] or case_result["unexpectedSourceIds"]
    ]
    if weak_cases:
        print("\nCases to inspect:")
        for case_result in weak_cases:
            print(
                "- "
                + case_result["caseId"]
                + f": retrieved={case_result['retrievedSourceIds']}, "
                + f"missing={case_result['missingSourceIds']}, "
                + f"unexpected={case_result['unexpectedSourceIds']}"
            )

    print(f"\nResult JSON: {result['resultPath']}")


def print_metric(label: str, metric: dict[str, Any]) -> None:
    value = metric["value"]
    printable = "n/a" if value is None else f"{value:.4f}"
    print(f"{label}: {printable}")


def calculate_f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def round_metric(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def unique_preserving_order(values: Any) -> list[str]:
    seen = set()
    unique_values = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique_values.append(value)
    return unique_values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Evidra deterministic retrieval evals.")
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to the versioned evaluation dataset.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_RESULTS_DIR),
        help="Directory for timestamped result JSON files.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Exact result JSON path. Defaults to a timestamped file in --output-dir.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing the output file when --output points to an existing path.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run ID for reproducible baseline artifacts.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_baseline_evaluation(
        dataset_path=args.dataset,
        output_dir=args.output_dir,
        output_path=args.output,
        overwrite=args.overwrite,
        run_id=args.run_id,
    )
    print_summary(result)


if __name__ == "__main__":
    main()
