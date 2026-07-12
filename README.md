# Evidra

Evidra vem de **EVIDence + Record + Audit**.

O Evidra é um copiloto developer-first para migração e vigilância criptográfica pós-quântica. O objetivo é ajudar equipas Java e Spring Boot a transformar um inventário criptográfico, como um CBOM CycloneDX gerado por ferramentas existentes, num plano de migração compreensível, fundamentado, testável e pronto para revisão humana.

A pergunta central do produto é:

> Como pode esta equipa migrar esta utilização criptográfica sem quebrar o projeto?

O Evidra não pretende substituir scanners criptográficos nem tratar o LLM como fonte de verdade. O scanner encontra, o RAG fundamenta, o GenAI explica e propõe, a compilação e os testes verificam, e o programador aprova.

## Visão do Produto

O Evidra foca-se na interseção entre:

- Java e Spring Boot
- GenAI e RAG
- criptografia pós-quântica
- CBOMs e auditoria técnica
- CI/CD e DevSecOps
- migrações seguras e reversíveis

O problema não é apenas trocar RSA ou ECC por ML-KEM, ML-DSA ou SLH-DSA. Uma migração real pode afetar dados históricos, formatos cifrados, certificados, autenticação, assinaturas digitais, integrações externas, recuperação de dados, gestão de chaves, desempenho e compatibilidade retroativa.

## Público Inicial

O produto é pensado primeiro para:

- programadores
- equipas Java/Spring Boot
- AppSec
- DevSecOps
- responsáveis técnicos por migrações criptográficas

O posicionamento é developer-first: ferramentas tradicionais mostram que criptografia existe; o Evidra deve ajudar o programador a entender o impacto e a migrar com segurança.

## Fluxo Principal

```text
CBOMkit analisa o projeto
        |
        v
gera um CBOM CycloneDX
        |
        v
Evidra importa e interpreta
        |
        v
RAG recupera documentação fiável
        |
        v
GenAI explica riscos e propõe plano
        |
        v
compilação e testes verificam
        |
        v
programador aprova
```

## MVP

O MVP deve manter-se pequeno e progressivo. Nesta fase, o Evidra deve permitir:

1. Importar um CBOM CycloneDX de um projeto Java.
2. Interpretar ativos criptográficos.
3. Apresentar findings.
4. Selecionar um finding.
5. Recuperar documentação relevante.
6. Gerar uma explicação estruturada.
7. Gerar um plano de migração.
8. Sugerir testes.
9. Exportar um relatório simples.

Fora do MVP inicial:

- edição automática de código
- criação automática de pull requests
- hash-chain
- Vault
- arquitetura distribuída pesada
- dashboard empresarial complexo
- suporte para várias linguagens
- substituição do CBOMkit

## Roadmap

### Versão 1

CBOM -> finding -> contexto -> RAG -> explicação -> plano.

### Versão 2

Plano -> patch -> diff -> compilação -> testes -> revisão humana.

### Versão 3

GitHub App -> análise por pull request -> CBOM diff -> políticas -> merge check.

### Futuro

- OpenRewrite
- pull requests automáticos
- benchmarks
- análise de certificados, keystores e TLS
- suporte Gradle
- políticas empresariais
- evidência assinada
- GitLab e Azure DevOps
- suporte para Python, .NET e JavaScript

## Princípios de Desenvolvimento

1. Implementar uma funcionalidade de cada vez.
2. Não reinventar o scanner.
3. Separar operações determinísticas de GenAI.
4. Não confiar no LLM como fonte de verdade.
5. Usar structured outputs sempre que fizer sentido.
6. Fundamentar respostas com RAG.
7. Validar alterações com compilação e testes.
8. Manter revisão humana.
9. Não adicionar tecnologias sem necessidade.
10. Pensar desde cedo na integração futura com CI/CD.

## Arquitetura Atual

O repositório está organizado como monorepo:

```text
evidra/
|-- apps/
|   |-- frontend/
|   |-- core-api/
|   `-- ai-service/
|-- docker-compose.yml
|-- .gitignore
`-- README.md
```

### Apps

- `apps/frontend`: interface web em Next.js.
- `apps/core-api`: API principal em Java 21 e Spring Boot.
- `apps/ai-service`: serviço GenAI/RAG em Python e FastAPI.

## Stack

- Frontend: Next.js, TypeScript e Tailwind CSS.
- Backend principal: Java 21, Spring Boot, Maven e Spring Web.
- Serviço GenAI: Python 3.12, FastAPI, Pydantic, HTTPX e pytest.
- Scanning e formato: CBOMkit, sonar-cryptography, CycloneDX e CycloneDX Core Java.
- RAG: inicialmente simples; depois Qdrant, embeddings, metadata filtering, hybrid retrieval e reranking.
- PQC em Java: Bouncy Castle com ML-KEM, ML-DSA e SLH-DSA.
- Refatoração futura: OpenRewrite.
- Infraestrutura: Docker, Docker Compose, GitHub Actions e AWS mais tarde.
- Observabilidade futura: Langfuse apenas quando necessário.

## Requisitos

- Docker
- Docker Compose

## Arranque Local

```bash
docker compose up --build
```

## URLs Locais

- Frontend: http://localhost:3000
- Core API: http://localhost:8080/health
- AI Service: http://localhost:8000/health

## Laboratório Java Futuro

Em paralelo ao produto, o projeto deve incluir um pequeno laboratório Java para estudar uma migração real:

```text
RSA-OAEP -> ML-KEM -> modo híbrido
```

Esse laboratório deve explorar:

- AES-256-GCM
- compatibilidade retroativa
- versionamento de formato cifrado
- dados históricos
- diferenças de tamanho
- desempenho
- chaves erradas
- deteção de alterações

## Frase de Produto

Evidra transforma um CBOM numa migração pós-quântica compreensível, testável e pronta para revisão, e impede que nova dívida criptográfica volte a entrar no projeto.
