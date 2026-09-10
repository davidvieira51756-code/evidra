import json
import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CORPUS_PATH = Path(__file__).with_name("knowledge_corpus.json")


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    title: str
    publisher: str
    reference: str
    document_type: str
    version: str
    status: str

    @field_validator("source_id", "title", "publisher", "reference", "document_type", "version", "status")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value


class KnowledgeChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    source_id: str
    section: str
    keywords: list[str] = Field(default_factory=list)
    content: str

    @field_validator("chunk_id", "source_id", "section", "content")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("keywords")
    @classmethod
    def require_keywords(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("must contain at least one keyword")
        if any(not item.strip() for item in value):
            raise ValueError("keywords must not be empty")
        return value


class RetrievalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: KnowledgeDocument
    chunk: KnowledgeChunk
    matched_terms: list[str]

    @field_validator("matched_terms")
    @classmethod
    def require_matched_terms(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("must contain at least one matched term")
        return value


class KnowledgeDocumentEntry(KnowledgeDocument):
    chunks: list[KnowledgeChunk]


class KnowledgeCorpus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[KnowledgeDocumentEntry]

    @model_validator(mode="after")
    def require_unique_ids(self) -> "KnowledgeCorpus":
        source_ids = [document.source_id for document in self.documents]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source IDs must be unique")

        chunk_ids = [
            chunk.chunk_id
            for document in self.documents
            for chunk in document.chunks
        ]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("chunk IDs must be unique")

        for document in self.documents:
            for chunk in document.chunks:
                if chunk.source_id != document.source_id:
                    raise ValueError("chunk source_id must match document source_id")

        return self


class KeywordRetriever:
    def __init__(self, corpus: KnowledgeCorpus) -> None:
        self.documents_by_source_id = {
            document.source_id: document_as_source(document)
            for document in corpus.documents
        }
        self.chunks = [
            chunk
            for document in corpus.documents
            for chunk in document.chunks
        ]

    def retrieve(self, query_terms: set[str], limit: int = 3) -> list[RetrievalResult]:
        normalized_query_terms = {normalize_term(term) for term in query_terms if normalize_term(term)}
        scored_chunks: list[tuple[int, str, KnowledgeChunk, list[str]]] = []

        for chunk in self.chunks:
            chunk_terms = build_chunk_terms(chunk)
            matched_terms = sorted(normalized_query_terms.intersection(chunk_terms))
            if matched_terms:
                scored_chunks.append((len(matched_terms), chunk.chunk_id, chunk, matched_terms))

        scored_chunks.sort(key=lambda item: (-item[0], item[1]))

        return [
            RetrievalResult(
                document=self.documents_by_source_id[chunk.source_id],
                chunk=chunk,
                matched_terms=matched_terms,
            )
            for _, _, chunk, matched_terms in scored_chunks[:limit]
        ]


@lru_cache(maxsize=1)
def load_knowledge_corpus(path: str | Path = CORPUS_PATH) -> KnowledgeCorpus:
    with Path(path).open(encoding="utf-8") as corpus_file:
        return KnowledgeCorpus.model_validate(json.load(corpus_file))


@lru_cache(maxsize=1)
def get_default_retriever() -> KeywordRetriever:
    return KeywordRetriever(load_knowledge_corpus())


def document_as_source(document: KnowledgeDocumentEntry) -> KnowledgeDocument:
    return KnowledgeDocument.model_validate(document.model_dump(exclude={"chunks"}))


def build_chunk_terms(chunk: KnowledgeChunk) -> set[str]:
    terms = {
        normalize_term(chunk.source_id),
        normalize_term(chunk.chunk_id),
        normalize_term(chunk.section),
        *(normalize_term(keyword) for keyword in chunk.keywords),
    }
    return {term for term in terms if term}


def tokenize(value: str) -> set[str]:
    normalized = value.replace("-", " ")
    return {
        normalize_term(token)
        for token in re.split(r"[^A-Za-z0-9]+", normalized)
        if normalize_term(token)
    }


def normalize_term(value: str) -> str:
    return value.strip().upper()
