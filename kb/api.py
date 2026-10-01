from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from kb.retrieval import search_kb


class SearchRequest(BaseModel):
    query: str
    language: str | None = None
    category: str | None = None


app = FastAPI(title="Knowledge Base API", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search")
def search(request: SearchRequest) -> dict[str, object]:
    return search_kb(request.query, language=request.language, category=request.category)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("kb.api:app", host="0.0.0.0", port=8000, reload=False)
