# Evidra

Evidra e uma plataforma para registar e tornar verificaveis decisoes empresariais assistidas por inteligencia artificial.

## Estrutura

```text
evidra/
├── apps/
│   ├── frontend/
│   ├── core-api/
│   └── ai-service/
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Tecnologias

- Frontend: Next.js, TypeScript, App Router, Tailwind CSS
- Core API: Java 21, Spring Boot, Maven, Spring Web, Actuator
- AI Service: Python 3.12, FastAPI, Uvicorn, Pydantic
- Docker Compose

## Requisitos

- Docker
- Docker Compose

## Arranque

```bash
docker compose up --build
```

## URLs locais

Frontend:
http://localhost:3000

Core API:
http://localhost:8080/health

AI Service:
http://localhost:8000/health

