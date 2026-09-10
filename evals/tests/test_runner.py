from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from evals.runner import (
    DEFAULT_DATASET_PATH,
    CaseResult,
    EvaluationDataset,
    calculate_metrics,
    load_dataset,
    run_baseline_evaluation,
)


def test_default_dataset_loads_and_validates_current_sources() -> None:
    dataset = load_dataset(DEFAULT_DATASET_PATH)

    assert dataset.datasetId == "crypto-findings-v1"
    assert dataset.retrievalStrategy == "keyword"
    assert len(dataset.cases) == 20


def test_duplicate_case_ids_are_rejected() -> None:
    payload = {
        "datasetId": "duplicate-case-test",
        "description": "fixture",
        "retrievalStrategy": "keyword",
        "cases": [
            minimal_case("same-id"),
            minimal_case("same-id"),
        ],
    }

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        EvaluationDataset.model_validate(payload)


def test_unknown_expected_source_ids_are_rejected(tmp_path) -> None:
    dataset_path = tmp_path / "invalid-source.json"
    dataset_path.write_text(
        json.dumps(
            {
                "datasetId": "invalid-source-test",
                "description": "fixture",
                "retrievalStrategy": "keyword",
                "cases": [
                    {
                        **minimal_case("case-1"),
                        "expectedSourceIds": ["not-a-real-source"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown source IDs"):
        load_dataset(dataset_path)


def test_metric_calculation_counts_hit_precision_recall_f1_and_no_source() -> None:
    case_results = [
        case_result(
            expected=["nist-fips-203", "nist-cswp-39-upd1"],
            retrieved=["nist-fips-203", "nist-sp-800-227"],
            hit=True,
            precision=0.5,
            recall=0.5,
            f1=0.5,
        ),
        case_result(
            case_id="miss",
            expected=["nist-fips-204"],
            retrieved=[],
            hit=False,
            precision=0.0,
            recall=0.0,
            f1=0.0,
        ),
        case_result(
            case_id="no-source",
            expected=[],
            retrieved=[],
            hit=None,
            no_source_expected=True,
            no_source_correct=True,
        ),
    ]

    metrics = calculate_metrics(case_results)

    assert metrics["retrievalHitRate"]["value"] == 0.5
    assert metrics["sourcePrecision"]["value"] == 0.5
    assert metrics["sourceRecall"]["value"] == 0.3333
    assert metrics["sourceF1"]["value"] == 0.4
    assert metrics["noSourceCorrectness"]["value"] == 1.0


def test_no_source_case_with_retrieval_is_incorrect() -> None:
    metrics = calculate_metrics(
        [
            case_result(
                expected=[],
                retrieved=["nist-cswp-39-upd1"],
                hit=None,
                no_source_expected=True,
                no_source_correct=False,
            )
        ]
    )

    assert metrics["noSourceCorrectness"]["value"] == 0.0
    assert metrics["sourcePrecision"]["value"] == 0.0
    assert metrics["sourceRecall"]["value"] is None
    assert metrics["sourceF1"]["value"] is None


def test_runner_writes_result_json_without_live_provider(tmp_path) -> None:
    result = run_baseline_evaluation(
        output_dir=tmp_path,
        run_id="test-run",
    )

    result_path = tmp_path / "test-run-crypto-findings-v1-keyword.json"
    result_json = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["runId"] == "test-run"
    assert result_json["datasetId"] == "crypto-findings-v1"
    assert result_json["retrievalStrategy"] == "keyword"
    assert result_json["caseCount"] == 20
    assert "provider" not in result_json
    assert "metrics" in result_json
    assert "cases" in result_json
    assert result_json["cases"][0]["caseId"] == "rsa-oaep-quantum-vulnerable"


def minimal_case(case_id: str) -> dict:
    return {
        "caseId": case_id,
        "category": "fixture",
        "finding": {
            "id": case_id,
            "title": "RSA-OAEP usage detected in fixture",
            "cryptoAssetName": "fixture",
            "status": "QUANTUM_VULNERABLE",
            "reason": "The algorithm is explicitly recognized as vulnerable.",
            "algorithm": "RSA-OAEP",
            "componentName": "fixture",
            "componentVersion": "1.0.0",
            "recommendation": "Assess migration impact.",
            "evidence": [],
        },
        "expectedSourceIds": ["nist-fips-203"],
    }


def case_result(
    *,
    case_id: str = "case-1",
    expected: list[str],
    retrieved: list[str],
    hit: bool | None,
    precision: float | None = None,
    recall: float | None = None,
    f1: float | None = None,
    no_source_expected: bool = False,
    no_source_correct: bool | None = None,
) -> CaseResult:
    return CaseResult(
        caseId=case_id,
        category="fixture",
        expectedSourceIds=expected,
        forbiddenSourceIds=[],
        retrievedSourceIds=retrieved,
        retrievedChunkIds=[],
        matchedTermsByChunk={},
        hit=hit,
        noSourceExpected=no_source_expected,
        noSourceCorrect=no_source_correct,
        sourcePrecision=precision,
        sourceRecall=recall,
        sourceF1=f1,
        missingSourceIds=sorted(set(expected).difference(retrieved)),
        unexpectedSourceIds=sorted(set(retrieved).difference(expected)),
        forbiddenRetrievedSourceIds=[],
        passed=True,
        notes="",
    )
