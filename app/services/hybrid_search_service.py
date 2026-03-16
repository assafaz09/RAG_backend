import asyncio
from typing import List, Dict, Any, Optional
from app.db.vector_db import get_qdrant_client
from app.db.elasticsearch_db import get_elasticsearch_client, search_documents
from app.services.embedding_service import embed_texts
from app.core.config import settings
from datetime import datetime
import hashlib

class HybridSearchService:
    """Hybrid search service combining vector and keyword search"""
    
    def __init__(self):
        self.vector_weight = settings.HYBRID_SEARCH_VECTOR_WEIGHT
        self.keyword_weight = settings.HYBRID_SEARCH_KEYWORD_WEIGHT
        self.top_k = settings.HYBRID_SEARCH_TOP_K
    
    async def search(self, query: str, search_mode: str = "hybrid", top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and keyword search
        
        Args:
            query: Search query
            search_mode: "hybrid", "vector", or "keyword"
            top_k: Number of results to return (overrides config)
        
        Returns:
            List of search results with combined scores
        """
        if top_k is None:
            top_k = self.top_k
        
        if search_mode == "vector":
            return await self._vector_search_only(query, top_k)
        elif search_mode == "keyword":
            return await self._keyword_search_only(query, top_k)
        else:
            return await self._hybrid_search(query, top_k)
    
    async def _vector_search_only(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform vector search only"""
        try:
            # Generate query embedding - run sync function in async context
            loop = asyncio.get_event_loop()
            query_vectors = await loop.run_in_executor(None, embed_texts, [query])
            query_vector = query_vectors[0]
            
            # Search Qdrant
            qdrant_client = get_qdrant_client()
            response = qdrant_client.query_points(
                collection_name=settings.QDRANT_COLLECTION,
                query=query_vector,
                limit=top_k,
                with_payload=True
            )
            
            results = []
            for hit in response.points:
                if hit.payload:
                    result = {
                        "content": hit.payload.get("text", ""),
                        "filename": hit.payload.get("filename", "Unknown"),
                        "document_id": hit.payload.get("document_id", ""),
                        "chunk_id": str(hit.id),
                        "metadata": hit.payload.get("meta", {}),
                        "timestamp": hit.payload.get("timestamp", datetime.utcnow().isoformat()),
                        "vector_score": hit.score,
                        "keyword_score": 0.0,
                        "combined_score": hit.score,
                        "source": "vector"
                    }
                    results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
    
    async def _keyword_search_only(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform keyword search only"""
        try:
            # Search Elasticsearch
            es_client = get_elasticsearch_client()
            es_results = search_documents(es_client, settings.ELASTICSEARCH_INDEX, query, top_k)
            
            results = []
            for hit in es_results:
                result = {
                    "content": hit.get("content", ""),
                    "filename": hit.get("filename", "Unknown"),
                    "document_id": hit.get("document_id", ""),
                    "chunk_id": hit.get("chunk_id", ""),
                    "metadata": hit.get("metadata", {}),
                    "timestamp": hit.get("timestamp", datetime.utcnow().isoformat()),
                    "vector_score": 0.0,
                    "keyword_score": hit.get("_score", 0.0),
                    "combined_score": hit.get("_score", 0.0),
                    "source": "keyword"
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Keyword search error: {e}")
            return []
    
    async def _hybrid_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform hybrid search combining both vector and keyword search"""
        # Run both searches in parallel
        vector_results, keyword_results = await asyncio.gather(
            self._vector_search_only(query, top_k),
            self._keyword_search_only(query, top_k),
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(vector_results, Exception):
            vector_results = []
            print(f"Vector search failed: {vector_results}")
        
        if isinstance(keyword_results, Exception):
            keyword_results = []
            print(f"Keyword search failed: {keyword_results}")
        
        # Combine and deduplicate results
        combined_results = self._merge_results(vector_results, keyword_results)
        
        # Sort by combined score and return top_k
        combined_results.sort(key=lambda x: x["combined_score"], reverse=True)
        return combined_results[:top_k]
    
    def _merge_results(self, vector_results: List[Dict], keyword_results: List[Dict]) -> List[Dict[str, Any]]:
        """Merge and deduplicate results from both searches"""
        # Create content-based deduplication
        seen_content = set()
        merged_results = []
        
        # Process vector results first
        for result in vector_results:
            content_hash = self._get_content_hash(result["content"])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                merged_results.append(result)
        
        # Process keyword results
        for result in keyword_results:
            content_hash = self._get_content_hash(result["content"])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                merged_results.append(result)
            else:
                # Update existing result with keyword score if higher
                for existing in merged_results:
                    if self._get_content_hash(existing["content"]) == content_hash:
                        existing["keyword_score"] = max(existing["keyword_score"], result["keyword_score"])
                        existing["combined_score"] = self._calculate_combined_score(existing)
                        existing["source"] = "hybrid"
                        break
        
        # Calculate combined scores for all results
        for result in merged_results:
            result["combined_score"] = self._calculate_combined_score(result)
            if result["vector_score"] > 0 and result["keyword_score"] > 0:
                result["source"] = "hybrid"
        
        return merged_results
    
    def _calculate_combined_score(self, result: Dict[str, Any]) -> float:
        """Calculate combined relevance score"""
        vector_score = result.get("vector_score", 0.0)
        keyword_score = result.get("keyword_score", 0.0)
        
        # Normalize scores (assuming both are in similar range)
        # If one score is 0, use only the other
        if vector_score == 0:
            return keyword_score
        if keyword_score == 0:
            return vector_score
        
        # Weighted combination
        combined = (vector_score * self.vector_weight) + (keyword_score * self.keyword_weight)
        return combined
    
    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        # Use first 100 characters for faster hashing
        content_sample = content[:100].strip().lower()
        return hashlib.md5(content_sample.encode()).hexdigest()

# Global service instance
hybrid_search_service = HybridSearchService()
