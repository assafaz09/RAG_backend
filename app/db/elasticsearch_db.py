from elasticsearch import Elasticsearch
from app.core.config import settings
from typing import Any, Optional, Dict, List
import json

_client: Optional[Elasticsearch] = None

def get_elasticsearch_client() -> Elasticsearch:
    """Get Elasticsearch client instance"""
    global _client
    if _client is None:
        _client = Elasticsearch(
            hosts=[settings.ELASTICSEARCH_URL],
            timeout=30,
            max_retries=3,
            retry_on_timeout=True
        )
        ensure_index(_client, settings.ELASTICSEARCH_INDEX)
    return _client

def ensure_index(client: Elasticsearch, index_name: str):
    """Create index if it doesn't exist"""
    try:
        if not client.indices.exists(index=index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "document_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "content": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "filename": {"type": "keyword"},
                        "metadata": {"type": "object"},
                        "timestamp": {"type": "date"}
                    }
                }
            }
            client.indices.create(index=index_name, body=mapping)
            print(f"Created Elasticsearch index: {index_name}")
    except Exception as e:
        print(f"Error creating Elasticsearch index: {e}")

def index_document(client: Elasticsearch, index_name: str, doc: Dict[str, Any]):
    """Index a document in Elasticsearch"""
    try:
        client.index(
            index=index_name,
            id=doc.get("chunk_id"),
            body=doc
        )
    except Exception as e:
        print(f"Error indexing document in Elasticsearch: {e}")

def bulk_index_documents(client: Elasticsearch, index_name: str, docs: List[Dict[str, Any]]):
    """Bulk index documents in Elasticsearch"""
    if not docs:
        return
    
    try:
        body = []
        for doc in docs:
            body.append({
                "index": {
                    "_index": index_name,
                    "_id": doc.get("chunk_id")
                }
            })
            body.append(doc)
        
        response = client.bulk(body=body)
        
        # Check for errors
        if response.get("errors"):
            for item in response["items"]:
                if "index" in item and item["index"].get("error"):
                    print(f"Bulk index error: {item['index']['error']}")
        else:
            print(f"Successfully bulk indexed {len(docs)} documents")
            
    except Exception as e:
        print(f"Error in bulk indexing: {e}")

def search_documents(client: Elasticsearch, index_name: str, query: str, size: int = 10) -> List[Dict[str, Any]]:
    """Search documents using keyword search"""
    try:
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["content", "content.keyword", "filename"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            },
            "size": size,
            "_source": ["content", "filename", "document_id", "chunk_id", "metadata", "timestamp"]
        }
        
        response = client.search(index=index_name, body=search_body)
        
        results = []
        for hit in response["hits"]["hits"]:
            source = hit["_source"]
            source["_score"] = hit["_score"]
            source["_id"] = hit["_id"]
            results.append(source)
        
        return results
        
    except Exception as e:
        print(f"Error searching Elasticsearch: {e}")
        return []

def delete_index(client: Elasticsearch, index_name: str):
    """Delete Elasticsearch index"""
    try:
        if client.indices.exists(index=index_name):
            client.indices.delete(index=index_name)
            print(f"Deleted Elasticsearch index: {index_name}")
    except Exception as e:
        print(f"Error deleting Elasticsearch index: {e}")
