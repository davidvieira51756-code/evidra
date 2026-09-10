# Evidra Evaluations

Evidra uses evaluations to keep retrieval and AI explanation changes measurable. The first evaluation baseline is intentionally deterministic and offline so future retrieval changes can be compared before replacing the current implementation.

## Dataset

The initial dataset is:

```text
evals/datasets/crypto-findings-v1.json
```

Dataset ID:

```text
crypto-findings-v1
```

The cases are grounded in the current curated knowledge corpus in `apps/ai-service/knowledge_corpus.json`. They cover RSA/RSA-OAEP, ML-KEM, ML-DSA, SLH-DSA, KEM guidance, crypto agility, review-required findings, ambiguous signature cases, and unrelated no-source controls.

The dataset stores structured finding input, expected source IDs, optional forbidden source IDs, category, and notes. It does not store generated explanations.

## Baseline Runner

Run the deterministic baseline from the repository root:

```powershell
.\apps\ai-service\.venv\Scripts\python.exe -m evals.runner
```

The default command:

- loads `crypto-findings-v1`
- uses the current keyword retriever
- does not call Ollama
- does not use the internet
- writes a JSON result under `evals/results/`

To write a stable baseline artifact:

```powershell
.\apps\ai-service\.venv\Scripts\python.exe -m evals.runner --run-id baseline --output evals\results\baseline-keyword-crypto-findings-v1.json --overwrite
```

Ordinary generated result files in `evals/results/` are ignored by git. The named baseline artifact is kept so future retrieval implementations have a fixed comparison point.

## Metrics

Current metrics are source-level retrieval metrics:

- `retrievalHitRate`: among cases with expected sources, the fraction where at least one expected source ID was retrieved.
- `sourcePrecision`: expected retrieved source IDs divided by all retrieved source IDs, counted per case.
- `sourceRecall`: expected retrieved source IDs divided by expected source IDs, counted per case.
- `sourceF1`: harmonic mean of source precision and source recall when both are defined.
- `noSourceCorrectness`: among cases with no expected sources, the fraction where retrieval returned no sources.

Per-case results include expected source IDs, retrieved source IDs, retrieved chunk IDs, matched terms by chunk, missing sources, unexpected sources, forbidden retrieved sources, and a pass flag.

## Current Limits

This baseline does not measure:

- hallucination rate
- groundedness of generated prose
- answer completeness
- semantic answer quality
- source-code analysis quality
- live model quality

Those require additional defensible evaluation methods and should be added in later phases. The current runner also does not perform LLM-as-a-judge evaluation.

## Future Retrieval Changes

Future embedding, vector, hybrid, or reranking implementations should be run against this same dataset before replacing the keyword baseline. If the dataset changes, create a new explicit dataset version rather than silently changing `crypto-findings-v1`.
