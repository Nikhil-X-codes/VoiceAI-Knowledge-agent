from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from rank_bm25 import BM25Okapi

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover
    TfidfVectorizer = None
    cosine_similarity = None

try:
    import chromadb
except Exception:  # pragma: no cover
    chromadb = None

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RECORDS_PATH = DATA_DIR / "records.jsonl"
CHROMA_PATH = ROOT.parent / "chroma_db"
_READY_INDEX: dict[str, Any] | None = None
_EMBEDDING_MODEL: Any = None


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[\w-]+\b", (_normalize_text(text) or "").lower())


def load_records(path: str | Path = RECORDS_PATH) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    path = Path(path)
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            if record.get("status") not in (None, "active", "superseded"):
                record["status"] = "active"
            records.append(record)
    return records


def chunk_text(text: str, chunk_size: int = 220, overlap: int = 35) -> list[str]:
    words = _tokenize(text)
    if not words:
        return []
    if len(words) <= chunk_size:
        return [" ".join(words)]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += max(1, chunk_size - overlap)
    return chunks


def build_chunk_index(records_path: str | Path = RECORDS_PATH) -> dict[str, Any]:
    records = [record for record in load_records(records_path) if record.get("status") == "active"]
    chunks: list[dict[str, Any]] = []

    for record in records:
        content = record.get("content", "")
        text_chunks = chunk_text(content)
        for idx, chunk in enumerate(text_chunks):
            chunk_id = f"{record.get('record_id', 'record')}_{idx:02d}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "record_id": record.get("record_id"),
                    "title": record.get("title"),
                    "category": record.get("category"),
                    "language": record.get("language", "en"),
                    "version": record.get("version", "1.0"),
                    "status": record.get("status", "active"),
                    "text": chunk,
                    "source": {
                        "ref": record.get("source", {}).get("ref"),
                        "page": record.get("source", {}).get("page"),
                        "url": record.get("source", {}).get("url"),
                    },
                }
            )

    embedding_model = _get_embedding_model() if SentenceTransformer is not None else None
    if chromadb is not None and embedding_model is not None:
        try:
            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            collection = client.get_or_create_collection(name="kb_chunks")
            docs = [chunk["text"] for chunk in chunks]
            ids = [chunk["chunk_id"] for chunk in chunks]
            embeddings = embedding_model.encode(
                [f"passage: {text}" for text in docs],
                normalize_embeddings=True,
            ).tolist()
            metadatas = [
                {
                    "record_id": chunk["record_id"],
                    "title": chunk["title"],
                    "category": chunk["category"],
                    "language": chunk["language"],
                    "version": chunk["version"],
                    "status": chunk["status"],
                    "source_ref": chunk["source"]["ref"],
                    "page": chunk["source"]["page"],
                    "url": chunk["source"]["url"],
                }
                for chunk in chunks
            ]
            if docs:
                collection.delete(ids=ids)
                collection.add(documents=docs, embeddings=embeddings, ids=ids, metadatas=metadatas)
        except Exception:
            pass

    return {"chunks": chunks, "collection_name": "kb_chunks"}


def _get_embedding_model() -> Any:
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None and SentenceTransformer is not None:
        _EMBEDDING_MODEL = SentenceTransformer("intfloat/multilingual-e5-small")
    return _EMBEDDING_MODEL


def prepare_retrieval() -> dict[str, Any]:
    """Build the local index and load embeddings once before serving calls."""
    global _READY_INDEX
    if _READY_INDEX is None:
        _READY_INDEX = build_chunk_index()
        _get_embedding_model()
    return _READY_INDEX


def _vector_similarity_scores(query: str, texts: list[str]) -> list[float]:
    if not texts:
        return []

    model = _get_embedding_model()
    if model is not None:
        try:
            query_emb = model.encode([f"query: {query}"], normalize_embeddings=True)
            text_emb = model.encode([f"passage: {text}" for text in texts], normalize_embeddings=True)
            sims = cosine_similarity(query_emb, text_emb)[0]
            return sims.tolist()
        except Exception:
            pass

    if TfidfVectorizer is not None and cosine_similarity is not None:
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words=None)
        matrix = vectorizer.fit_transform(texts + [query])
        query_vec = matrix[-1]
        corpus = matrix[:-1]
        sims = cosine_similarity(query_vec, corpus)[0]
        return sims.tolist()

    return [0.0 for _ in texts]


def search_kb(query: str, language: str | None = None, category: str | None = None, cutoff: float = 0.01) -> dict[str, Any]:
    index = prepare_retrieval()
    chunks = index["chunks"]
    if language:
        chunks = [chunk for chunk in chunks if chunk["language"] == language]
    if category:
        chunks = [chunk for chunk in chunks if chunk["category"] == category]

    if not chunks:
        return {"found": False, "results": []}

    query_term_list = _tokenize(query)
    query_tokens = set(query_term_list)
    if not query_tokens:
        return {"found": False, "results": []}

    corpus_text = [chunk["text"] for chunk in chunks]
    corpus_tokens = set(token for text in corpus_text for token in _tokenize(text))
    if not query_tokens.intersection(corpus_tokens):
        return {"found": False, "results": []}

    tokenized_corpus = [_tokenize(text) for text in corpus_text]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query_term_list)
    bm25_order = sorted(range(len(chunks)), key=lambda i: bm25_scores[i], reverse=True)[:10]

    vector_scores = _vector_similarity_scores(query, corpus_text)
    vector_order = sorted(range(len(chunks)), key=lambda i: vector_scores[i], reverse=True)[:10]

    rrf_scores: dict[str, float] = defaultdict(float)
    for rank, idx in enumerate(vector_order, start=1):
        rrf_scores[chunks[idx]["chunk_id"]] += 1 / (60 + rank)
    for rank, idx in enumerate(bm25_order, start=1):
        rrf_scores[chunks[idx]["chunk_id"]] += 1 / (60 + rank)

    ranked = []
    for chunk in chunks:
        score = rrf_scores.get(chunk["chunk_id"], 0.0)
        if score > 0:
            ranked.append({
                "chunk_id": chunk["chunk_id"],
                "record_id": chunk["record_id"],
                "title": chunk["title"],
                "text": chunk["text"],
                "score": round(score, 6),
                "source": {
                    "ref": chunk["source"]["ref"],
                    "page": chunk["source"]["page"],
                    "url": chunk["source"]["url"],
                    "version": chunk["version"],
                },
            })

    ranked.sort(key=lambda item: item["score"], reverse=True)
    top_results = ranked[:3]
    if not top_results:
        return {"found": False, "results": []}
    best_score = top_results[0]["score"]

    return {
        "found": bool(best_score >= cutoff),
        "results": [
            {
                "record_id": item["record_id"],
                "text": item["text"],
                "score": item["score"],
                "source": item["source"],
            }
            for item in top_results
        ],
    }


if __name__ == "__main__":
    print(json.dumps(search_kb("late fee due date", category="policy"), indent=2))
