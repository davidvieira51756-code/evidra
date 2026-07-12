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

- RAG
- persistence
- user accounts
- contextual source-code analysis
- pull request integration

## AI Service: Explain Finding

```http
POST /findings/explain
```

This endpoint lives in `apps/ai-service`.

It receives one structured finding and returns a structured explanation. When `OPENAI_API_KEY` is configured, the service calls the OpenAI Responses API and asks for a structured JSON explanation. Without an API key, or if the model call fails, it returns the deterministic fallback explanation.

The MVP frontend calls the `core-api` proxy endpoint:

```http
POST /api/findings/explain
```

The `core-api` then forwards the structured finding to the `ai-service`.

### GenAI Configuration

```powershell
$env:OPENAI_API_KEY="your-api-key"
$env:OPENAI_MODEL="gpt-4.1"
```

`OPENAI_MODEL` is optional. If it is not set, the service uses `gpt-4.1`.

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
    "This explanation is generated from structured finding data only.",
    "It does not inspect source code, historical data, certificates, keystores, or runtime configuration."
  ]
}
```
