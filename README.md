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
- use local RAG snippets to add context to explanations
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
- `apps/ai-service`: optional AI service. Uses local RAG snippets and, when configured, OpenAI to produce structured finding explanations.

## Local Setup

### AI service

Create `apps/ai-service/.env` from `.env.example`:

```env
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4.1
```

Then run:

```powershell
cd apps/ai-service
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

If `OPENAI_API_KEY` is missing, invalid, or quota-limited, the service still returns a deterministic fallback explanation using local RAG context.

### Core API

```powershell
cd apps/core-api
mvn spring-boot:run
```

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

## RAG Scope

RAG is currently local and minimal. The AI service contains curated knowledge snippets in code and retrieves relevant snippets based on the finding status, algorithm, title, and reason.

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
