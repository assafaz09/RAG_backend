from qdrant_client.http.models import PointStruct
from typing import List, Dict
import uuid
from datetime import datetime
from app.services.embedding_service import embed_texts
from app.db.vector_db import get_qdrant_client
from app.db.elasticsearch_db import get_elasticsearch_client, bulk_index_documents
from app.core.config import settings

def ingest_documents(docs: List[Dict]):
    if not docs:
        return
    
    texts = [d["text"] for d in docs]
    vectors = embed_texts(texts)
    
    qdrant_client = get_qdrant_client()
    es_client = get_elasticsearch_client()
    
    points = []
    es_docs = []
    
    for i, (doc, vec) in enumerate(zip(docs, vectors)):
        # Generate unique chunk ID
        chunk_id = str(uuid.uuid4())
        document_id = doc.get("document_id", str(uuid.uuid4()))
        
        # Prepare Qdrant payload
        payload = doc.get("meta") or {}
        payload["text"] = doc["text"]
        payload["filename"] = doc.get("filename", "unknown")
        payload["document_id"] = document_id
        payload["chunk_id"] = chunk_id
        payload["timestamp"] = datetime.utcnow().isoformat()
        
        points.append(PointStruct(
            id=chunk_id,
            vector=vec,
            payload=payload
        ))
        
        # Prepare Elasticsearch document
        es_doc = {
            "document_id": document_id,
            "chunk_id": chunk_id,
            "content": doc["text"],
            "filename": doc.get("filename", "unknown"),
            "metadata": doc.get("meta", {}),
            "timestamp": datetime.utcnow().isoformat()
        }
        es_docs.append(es_doc)
    
    try:
        # Index in Qdrant
        qdrant_client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=points
        )
        
        # Index in Elasticsearch
        bulk_index_documents(es_client, settings.ELASTICSEARCH_INDEX, es_docs)
        
        print(f"Successfully indexed {len(docs)} documents in both Qdrant and Elasticsearch")
        
    except Exception as e:
        print(f"Error during ingestion: {e}")
        raise