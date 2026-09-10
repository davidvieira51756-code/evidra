# Evidra API Contract

This document describes the current MVP API contract between the frontend and the `core-api`.

The main frontend endpoint is:

```http
POST /api/cboms/analyze
```

The other endpoints are useful for lower-level import inspection and report export.

## Upload Format

All CBOM endpoints receive a `multipart/form-data` request with a file field named `file`.

Example:

```bash
curl -F "file=@apps/core-api/src/test/resources/cbom/rsa-oaep-cbom.json" http://localhost:8080/api/cboms/analyze
```

The uploaded file must be valid JSON and must contain:

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.6"
}
```

## Analyze CBOM

```http
POST /api/cboms/analyze
```

Use this endpoint for the MVP frontend.

It validates the CBOM, extracts crypto assets, generates deterministic findings, and returns an analysis object.

### Response

```json
{
  "status": "completed",
  "summary": {
    "bomFormat": "CycloneDX",
    "specVersion": "1.6",
    "componentCount": 1,
    "cryptoAssetCount": 1,
    "findingCount": 1,
    "quantumVulnerableFindingCount": 1,
    "postQuantumFindingCount": 0,
    "reviewRequiredFindingCount": 0
  },
  "findings": [
    {
      "id": "finding-1",
      "title": "RSA-OAEP usage detected in bcprov-jdk18on",
      "cryptoAssetName": "bcprov-jdk18on",
      "status": "QUANTUM_VULNERABLE",
      "reason": "The algorithm is explicitly recognized as vulnerable to cryptographically relevant quantum attacks.",
      "algorithm": "RSA-OAEP",
      "componentName": "bcprov-jdk18on",
      "componentVersion": "1.78",
      "recommendation": "Assess migration impact and plan a transition path to a post-quantum or hybrid design.",
      "evidence": [
        "property:evidra.crypto.algorithm=RSA-OAEP",
        "property-name=evidra.crypto.algorithm"
      ]
    }
  ],
  "nextActions": [
    "Review quantum-vulnerable findings and identify affected code paths, data formats, and integrations.",
    "Plan a migration path to post-quantum or hybrid cryptography before changing code."
  ]
}
```

### Finding Status

- `QUANTUM_VULNERABLE`: the normalized algorithm is explicitly classified as quantum-vulnerable. Current algorithms: `RSA`, `ECDSA`, `ECDH`, `DSA`, `DH`.
- `POST_QUANTUM`: the normalized algorithm is explicitly classified as post-quantum. Current algorithms: `ML-KEM`, `ML-DSA`, `SLH-DSA`.
- `REVIEW_REQUIRED`: the algorithm is not explicitly classified yet and needs manual review.

The current implementation intentionally does not create specific classes for AES, SHA, or HMAC. They remain `REVIEW_REQUIRED` until contextual analysis is added.

## Import CBOM

```http
POST /api/cboms/import
```

This endpoint exposes the lower-level import result. It is useful for debugging the deterministic pipeline.

### Response

```json
{
  "status": "accepted",
  "bomFormat": "CycloneDX",
  "specVersion": "1.6",
  "serialNumber": "urn:uuid:11111111-1111-1111-1111-111111111111",
  "version": 1,
  "componentCount": 1,
  "cryptoAssetCount": 1,
  "cryptoAssets": [],
  "findingCount": 1,
  "findings": []
}
```

## Export Report

```http
POST /api/cboms/report
```

This endpoint returns a simple Markdown report.

Response content type:

```http
text/markdown
```

## Error Response

Invalid CBOM requests return `400 Bad Request`.

```json
{
  "code": "INVALID_CBOM",
  "message": "CBOM file must be valid JSON."
}
```

Known validation failures:

- missing file
- empty file
- invalid JSON
- JSON that is not an object
- missing `bomFormat`
- `bomFormat` different from `CycloneDX`
- missing `specVersion`

## Current Boundaries

The CBOM import and finding classification pipeline is deterministic.

It does not yet include:

- vector database RAG
- persistence
- user accounts
- contextual source-code analysis
- pull request integration

## AI Service: Explain Finding

```http
POST /findings/explain
```

This endpoint lives in `apps/ai-service`.

It receives one structured finding and returns a structured explanation. The service first retrieves a small set of local knowledge chunks relevant to the finding, then passes bounded evidence blocks through the configured AI provider. Ollama is the current provider. When `OLLAMA_MODEL` is configured, the Ollama provider calls `/api/generate` and asks for a structured JSON explanation. The AI service parses and validates provider output with the existing Pydantic response schema before returning it. Source references are derived from retrieval results, not from model claims. Without a configured model, or if the provider/model call fails or returns invalid structured output, it returns the deterministic fallback explanation.

The MVP frontend calls the `core-api` proxy endpoint:

```http
POST /api/findings/explain
```

The `core-api` then forwards the structured finding to the `ai-service`.

For local non-Docker runs, the Core API defaults to `http://localhost:8000`. In Docker Compose, it is configured to call `http://ai-service:8000`. The proxy timeout defaults to 5 seconds and can be configured with `EVIDRA_AI_SERVICE_TIMEOUT_SECONDS`.

### GenAI Configuration

```powershell
$env:OLLAMA_BASE_URL="http://localhost:11434"
$env:OLLAMA_MODEL="llama3.1:8b"
```

`OLLAMA_BASE_URL` is optional. If it is not set, the AI service uses `http://localhost:11434`.

`OLLAMA_MODEL` is required for GenAI explanations. If it is not set, the service uses the deterministic fallback.

Ollama-specific HTTP behavior is isolated behind the AI service provider implementation. The external `/findings/explain` response shape is unchanged.

Install Ollama from https://ollama.com/download and pull the configured model before starting the service:

```powershell
ollama pull llama3.1:8b
```

### RAG Scope

The current RAG implementation is intentionally small and local. The curated corpus is stored in `apps/ai-service/knowledge_corpus.json` and loaded into explicit `KnowledgeDocument`, `KnowledgeChunk`, and `RetrievalResult` models. Retrieval is a baseline keyword implementation over trusted source metadata and chunk keywords using the finding status, algorithm, title, and reason.

Initial curated source IDs:

- `nist-fips-203`: NIST FIPS 203, ML-KEM.
- `nist-fips-204`: NIST FIPS 204, ML-DSA.
- `nist-fips-205`: NIST FIPS 205, SLH-DSA.
- `nist-sp-800-227`: NIST SP 800-227, Recommendations for Key-Encapsulation Mechanisms.
- `nist-cswp-39-upd1`: NIST CSWP 39upd1, crypto agility.

To add another trusted source, add a document entry with a stable `source_id`, publisher, reference, version/status metadata, and one or more chunks with stable `chunk_id` values and explicit keywords. The service does not fetch sources at runtime, so tests and local startup remain offline.

Retrieved content is passed to the model as evidence blocks with source boundaries. It must be treated as evidence data, not as instructions.

It does not yet use embeddings, vector search, reranking, external documents, Qdrant, or metadata filtering.

### Request

```json
{
  "finding": {
    "id": "finding-1",
    "title": "RSA-OAEP usage detected in bcprov-jdk18on",
    "cryptoAssetName": "bcprov-jdk18on",
    "status": "QUANTUM_VULNERABLE",
    "reason": "The algorithm is explicitly recognized as vulnerable to cryptographically relevant quantum attacks.",
    "algorithm": "RSA-OAEP",
    "componentName": "bcprov-jdk18on",
    "componentVersion": "1.78",
    "recommendation": "Assess migration impact and plan a transition path to a post-quantum or hybrid design.",
    "evidence": [
      "property:evidra.crypto.algorithm=RSA-OAEP"
    ]
  }
}
```

### Response

```json
{
  "findingId": "finding-1",
  "summary": "RSA-OAEP was detected in bcprov-jdk18on with status QUANTUM_VULNERABLE.",
  "riskExplanation": "RSA-OAEP is classified as quantum-vulnerable by the deterministic rules...",
  "migrationConsiderations": [
    "Map the affected code paths and external integrations."
  ],
  "suggestedTests": [
    "Verify old data remains readable or verifiable during migration."
  ],
  "limitations": [
    "This explanation is generated from structured finding data and retrieved evidence.",
    "It does not inspect source code, historical data, certificates, keystores, or runtime configuration."
  ],
  "sourceReferences": [
    {
      "sourceId": "nist-fips-203",
      "title": "FIPS 203: Module-Lattice-Based Key-Encapsulation Mechanism Standard",
      "publisher": "National Institute of Standards and Technology",
      "reference": "https://doi.org/10.6028/NIST.FIPS.203",
      "documentType": "standard",
      "section": "Overview",
      "chunkId": "nist-fips-203:ml-kem-overview"
    }
  ]
}
```
