import asyncio
from app.db.vector_db import get_qdrant_client
from app.services.hybrid_search_service import hybrid_search_service
from app.core.config import settings
from typing import List, Dict

async def retrieve(query: str, search_mode: str = "hybrid", top_k: int = 5) -> List[Dict]:
    """
    Retrieve documents using hybrid search
    
    Args:
        query: Search query
        search_mode: "hybrid", "vector", or "keyword"
        top_k: Number of results to return
    
    Returns:
        List of search results
    """
    try:
        print(f"DEBUG: Executing {search_mode} retrieval")
        
        # Use hybrid search service - now both functions are async
        results = await hybrid_search_service.search(query, search_mode, top_k)
        
        # Convert to legacy format for backward compatibility
        legacy_results = []
        for result in results:
            legacy_result = {
                "text": result["content"],
                "source": result["filename"],
                "document_id": result.get("document_id", ""),
                "chunk_id": result.get("chunk_id", ""),
                "metadata": result.get("metadata", {}),
                "score": result["combined_score"],
                "vector_score": result.get("vector_score", 0.0),
                "keyword_score": result.get("keyword_score", 0.0),
                "search_source": result.get("source", "unknown")
            }
            legacy_results.append(legacy_result)
        
        print(f"DEBUG: Successfully found {len(legacy_results)} results using {search_mode} search")
        return legacy_results

    except Exception as e:
        print(f"DEBUG: Hybrid search failed, falling back to vector search: {e}")
        # Fallback to original vector search
        return _fallback_vector_search(query, top_k)

def _fallback_vector_search(query: str, top_k: int) -> List[Dict]:
    """Fallback to original vector search"""
    try:
        from app.services.embedding_service import embed_texts
        
        # Generate query embedding
        query_vectors = embed_texts([query])
        query_vector = query_vectors[0]
        
        client = get_qdrant_client()
        response = client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )
        
        results = [
            {
                "text": hit.payload.get("text", ""), 
                "source": hit.payload.get("filename", "Unknown"),
                "document_id": hit.payload.get("document_id", ""),
                "chunk_id": str(hit.id),
                "metadata": hit.payload.get("meta", {}),
                "score": hit.score,
                "vector_score": hit.score,
                "keyword_score": 0.0,
                "search_source": "vector_fallback"
            } 
            for hit in response.points if hit.payload
        ]
        
        print(f"DEBUG: Fallback vector search found {len(results)} results")
        return results

    except Exception as final_e:
        print(f"DEBUG: !! All retrieval attempts failed: {final_e}")
        return []
