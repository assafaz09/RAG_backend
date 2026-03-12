from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class Document(BaseModel):
    id: str
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class IngestRequest(BaseModel):
    documents: List[Document]


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    sources: List[Optional[str]] = Field(default_factory=list)
