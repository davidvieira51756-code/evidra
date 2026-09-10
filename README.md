# Evidra

Evidra means **Evidence + Record + Audit**.

Evidra is a developer-first MVP for turning CycloneDX CBOM files into structured cryptography findings, explanations, and simple migration guidance for post-quantum readiness.

The project does not replace crypto scanners and does not treat GenAI as the source of truth. Deterministic parsing and classification happen first; GenAI is optional and only explains already-derived findings.

## Current Status

The current MVP can:

- import and validate CycloneDX JSON CBOM files
- extract simple cryptographic assets from CBOM metadata/properties
- classify algorithms with explicit rules
- generate deterministic findings
- generate a structured CBOM analysis
- export a Markdown report
- explain individual findings through an optional FastAPI AI service
- use a local curated knowledge corpus with source attribution to add context to explanations
- fall back to deterministic explanations when GenAI is unavailable or quota-limited

Current algorithm classification:

- `RSA`, `ECDSA`, `ECDH`, `DSA`, `DH` -> `QUANTUM_VULNERABLE`
- `ML-KEM`, `ML-DSA`, `SLH-DSA` -> `POST_QUANTUM`
- anything else -> `REVIEW_REQUIRED`

`REVIEW_REQUIRED` is intentionally conservative. AES, SHA, and HMAC do not have special categories yet.

## Architecture

```text
evidra/
|-- apps/
|   |-- frontend/    # Next.js UI
|   |-- core-api/    # Java 21 Spring Boot API
|   `-- ai-service/  # Python FastAPI GenAI/RAG service
|-- docs/
|-- docker-compose.yml
`-- README.md
```

## Services

- `apps/frontend`: web UI for importing CBOM files, viewing findings, explaining findings, and exporting reports.
- `apps/core-api`: main API. Validates CBOM files, extracts crypto assets, classifies findings, generates analysis/report output, and proxies finding explanation requests to the AI service.
- `apps/ai-service`: optional AI service. Uses a local curated knowledge corpus, source-aware retrieval, and an AI provider boundary. Ollama is the current provider for structured finding explanations when configured.

## Local Setup

### AI service

Create `apps/ai-service/.env` from `.env.example`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

Install Ollama from https://ollama.com/download, start it, and pull the model you want to use:

```powershell
ollama pull llama3.1:8b
```

Then run:

```powershell
cd apps/ai-service
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

If `OLLAMA_MODEL` is missing, Ollama is unavailable, or the model call fails, the service still returns a deterministic fallback explanation using retrieved local evidence where available.

The AI service keeps provider-specific invocation behind a small provider abstraction. Ollama remains the only implemented provider and the existing `OLLAMA_BASE_URL` and `OLLAMA_MODEL` environment variables are still supported.

When running through Docker Compose, keep Ollama running on the host and set `OLLAMA_MODEL` in your shell or a root `.env` file:

```powershell
$env:OLLAMA_MODEL="llama3.1:8b"
docker compose up --build
```

### Core API

```powershell
cd apps/core-api
mvn spring-boot:run
```

The Core API forwards finding explanation requests to the AI service. For local non-Docker runs it defaults to `http://localhost:8000`; override with `EVIDRA_AI_SERVICE_BASE_URL` when needed. The proxy request timeout defaults to 5 seconds and can be changed with `EVIDRA_AI_SERVICE_TIMEOUT_SECONDS`.

### Frontend

```powershell
cd apps/frontend
npm.cmd run dev
```

Local URLs:

- Frontend: http://localhost:3000
- Core API health: http://localhost:8080/health
- AI service health: http://localhost:8000/health

## API Examples

Run these from `apps/core-api` or adjust the file path.

Import and validate a CBOM:

```powershell
curl.exe -F "file=@src/test/resources/cbom/rsa-oaep-cbom.json" http://localhost:8080/api/cboms/import
```

Analyze a CBOM:

```powershell
curl.exe -F "file=@src/test/resources/cbom/rsa-oaep-cbom.json" http://localhost:8080/api/cboms/analyze
```

Export a Markdown report:

```powershell
curl.exe -F "file=@src/test/resources/cbom/rsa-oaep-cbom.json" http://localhost:8080/api/cboms/report
```

The MVP API contract is documented in [docs/api.md](docs/api.md).

## Verification

Run the current test/build checks from the repository root:

```powershell
cd apps/ai-service
.\.venv\Scripts\python.exe -m pytest

cd ..\core-api
mvn test

cd ..\frontend
npm.cmd run build
```

## RAG Scope

RAG is currently local and minimal. The AI service loads a curated offline corpus from `apps/ai-service/knowledge_corpus.json`. Documents and chunks have stable source IDs and references, and retrieval returns structured results with provenance. The current retriever is a baseline keyword implementation over finding status, algorithm, title, reason, and explicit chunk keywords.

Initial sources are NIST FIPS 203, FIPS 204, FIPS 205, SP 800-227, and CSWP 39upd1. Add trusted sources by adding a document entry and one or more chunks to `knowledge_corpus.json`; no documents are fetched at runtime.

Retrieved content is passed to the model as bounded evidence, not as instructions. The provider boundary is intentionally separate from RAG: retrieval and deterministic fallback remain application logic, while Ollama-specific HTTP invocation and response extraction live in the provider implementation.

There is no vector database, embedding pipeline, persistence layer, or contextual source-code analysis yet.

Before expanding RAG, the project should define a clear data boundary: what can leave Evidra for GenAI and what must always stay local.

## Not Implemented Yet

- PostgreSQL persistence
- user accounts
- full CBOM history
- vector database RAG
- source-code analysis
- automatic code changes
- automatic pull requests
- CI/CD policy gates
- enterprise dashboard

## Development Principles

- Keep deterministic analysis separate from GenAI.
- Do not send complete CBOM files to GenAI.
- Keep GenAI explanations grounded in structured findings and retrieved context.
- Prefer explicit algorithm classification over substring guessing.
- Add persistence, richer RAG, and automation only after the MVP data boundary is clear.
