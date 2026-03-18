from fastapi import APIRouter, HTTPException, UploadFile, File
from app.db.vector_db import get_qdrant_client
from app.schemas.schemas import IngestRequest, QueryRequest, QueryResponse
from app.services.ingestion_service import ingest_documents
from app.services.embedding_service import embed_texts
from app.services.embedding_service import generate_embedding
from app.services.retrieval_service import retrieve
from app.services.llm_service import generate_answer
from app.utils.file_parser import parse_file
from app.utils.chunking import chunk_text
from app.services.vision_service import process_image_for_rag
from app.core.config import settings
from qdrant_client.http.models import PointStruct
from uuid import uuid4
import os
import fitz
from datetime import datetime, timedelta
from typing import List, Dict, Any  

router = APIRouter()

@router.post("/ingest")
async def ingest(req: IngestRequest):
    try:
        ingest_documents(req.documents)
        return {"status": "ok", "ingested": len(req.documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    print(f"\n🚀 DEBUG START: Processing file: {file.filename}")
    
    try:
        file_ext = os.path.splitext(file.filename)[1].lower()
        metadata_base = {"filename": file.filename}
        points = []

        # 1. טיפול בתמונות (הופכות לתיאור טקסטואלי יחיד)
        if file_ext in IMAGE_EXTENSIONS:
            print(f"DEBUG: Processing as IMAGE")
            image_bytes = await file.read()
            vision_result = await process_image_for_rag(image_bytes, file.filename)
            
            content = vision_result.get("text", "")
            if content:
                vector = generate_embedding(content)
                points.append(PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={"text": content, "type": "image", **metadata_base, **vision_result.get("metadata", {})}
                ))

        # 2. טיפול במסמכים (PDF / טקסט) עם Chunking
        else:
            print(f"DEBUG: Processing as DOCUMENT ({file_ext})")
            file_bytes = await file.read()
            raw_text = ""

            if file_ext == ".pdf":
                # חילוץ טקסט מכל דפי ה-PDF
                with fitz.open(stream=file_bytes, filetype="pdf") as doc:
                    raw_text = chr(12).join([page.get_text() for page in doc])
            else:
                # קבצי טקסט רגילים / Markdown
                raw_text = file_bytes.decode("utf-8")

            if not raw_text.strip():
                print(f"⚠️ DEBUG WARNING: No text extracted from {file.filename}")
                return {"status": "warning", "message": "No text content found."}

            # לוגיקת Chunking: מפרקים את הטקסט לחתיכות של 1000 תווים עם חפיפה
            # חפיפה (Overlap) עוזרת לשמור על הקשר בין פסקה לפסקה
            chunk_size = 1000
            overlap = 200
            chunks = [raw_text[i:i + chunk_size] for i in range(0, len(raw_text), chunk_size - overlap)]
            
            print(f"DEBUG: Created {len(chunks)} chunks for document.")

            for i, chunk in enumerate(chunks):
                if not chunk.strip(): continue
                
                vector = generate_embedding(chunk)
                points.append(PointStruct(
                    id=str(uuid4()),
                    vector=vector,
                    payload={
                        "text": chunk, 
                        "type": "text", 
                        "chunk_index": i, 
                        **metadata_base
                    }
                ))

        # 3. שמירה ב-Qdrant
        if points:
            client = get_qdrant_client()
            print(f"DEBUG: Upserting {len(points)} points to Qdrant...")
            client.upsert(
                collection_name=settings.QDRANT_COLLECTION,
                wait=True,
                points=points
            )
            print(f"✅ DEBUG SUCCESS: {file.filename} processed into {len(points)} vectors.")
            return {
                "status": "success", 
                "filename": file.filename, 
                "chunks_ingested": len(points)
            }
        else:
            return {"status": "error", "message": "No embeddable content found."}

    except Exception as e:
        print(f"❌ DEBUG ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/assets")
async def list_assets():
    """List all assets (files) in the system"""
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(collection_name=settings.QDRANT_COLLECTION)
        count = collection_info.points_count
        results = client.scroll(collection_name=settings.QDRANT_COLLECTION, limit=100)
        
        assets = []
        seen_files = set()
        
        for point in results[0]:
            if point.payload:
                filename = point.payload.get("filename", "unknown")
                doc_type = point.payload.get("type", "text")
                
                # Avoid duplicate entries for the same file
                if filename not in seen_files and filename != "unknown":
                    asset_type = "image" if doc_type == "image" else "file"
                    assets.append({
                        "id": str(point.id),
                        "name": filename,
                        "type": asset_type,
                        "size": None,  # Size info not stored in vector DB
                        "path": None   # Path info not stored in vector DB
                    })
                    seen_files.add(filename)
        
        return {"assets": assets}
    except Exception as e:
        return {"assets": [], "error": str(e)}

@router.get("/documents")
async def list_documents():
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(collection_name=settings.QDRANT_COLLECTION)
        count = collection_info.points_count
        results = client.scroll(collection_name=settings.QDRANT_COLLECTION, limit=100)
        filenames = set()
        for point in results[0]:
            fname = point.payload.get("filename", "unknown") if point.payload else "unknown"
            filenames.add(fname)
        return {"total_points": count, "documents": sorted(list(filenames))}
    except Exception as e:
        return {"total_points": 0, "documents": [], "error": str(e)}

@router.post("/query")
async def query(request: QueryRequest):
    try:
        # 0. DEBUG - בוא נראה מה קיבלנו מהמשתמש
        print(f"DEBUG: Received request: {request}")
        
        # במידה והשדה ב-Schema שלך נקרא 'question' ולא 'query', שנה כאן:
        user_query = getattr(request, 'query', getattr(request, 'question', None))
        
        if not user_query:
            raise ValueError("No query or question found in request body")

        # 1. יצירת Embedding
        query_vectors = embed_texts([user_query])
        query_vector = query_vectors[0]
        
        # 2. שליפת מידע
        # שים לב: לפי הלוגים Retrieval עובד ומצא 5 hits!
        hits = await retrieve(query_vector, top_k=request.top_k if hasattr(request, 'top_k') else 5)
        
        print(f"DEBUG: Successfully found {len(hits)} hits.")
        
        # 3. בניית קונטקסט
        context = "\n---\n".join(hits) if hits else "No relevant context found."
        
        # 4. יצירת תשובה
        system_prompt = "You are a helpful assistant. Use the provided context to answer the user's question."
        user_prompt = f"Context:\n{context}\n\nQuestion: {user_query}"
        
        response_text = generate_answer(system_prompt, user_prompt)
        
        return {
            "answer": response_text,
            "context_used": hits
        }

    except Exception as e:
        print(f"ERROR in /query endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard API endpoints
@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get real-time dashboard statistics"""
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(collection_name=settings.QDRANT_COLLECTION)
        
        # Get document statistics
        total_points = collection_info.points_count
        results = client.scroll(collection_name=settings.QDRANT_COLLECTION, limit=1000)
        
        # Analyze documents
        documents = {}
        text_chunks = 0
        image_count = 0
        
        for point in results[0]:
            if point.payload:
                filename = point.payload.get("filename", "unknown")
                doc_type = point.payload.get("type", "text")
                
                if filename not in documents:
                    documents[filename] = {"type": doc_type, "chunks": 0}
                
                documents[filename]["chunks"] += 1
                
                if doc_type == "text":
                    text_chunks += 1
                elif doc_type == "image":
                    image_count += 1
        
        return {
            "total_documents": len(documents),
            "total_chunks": total_points,
            "text_chunks": text_chunks,
            "image_count": image_count,
            "recent_uploads": len([d for d in documents.values() if d["type"] == "text"])
        }
    except Exception as e:
        return {
            "total_documents": 0,
            "total_chunks": 0,
            "text_chunks": 0,
            "image_count": 0,
            "recent_uploads": 0,
            "error": str(e)
        }

@router.get("/dashboard/activity")
async def get_recent_activity():
    """Get recent system activity"""
    try:
        client = get_qdrant_client()
        results = client.scroll(collection_name=settings.QDRANT_COLLECTION, limit=50, order_by="timestamp")
        
        activities = []
        documents = {}
        
        # Process recent documents
        for point in results[0]:
            if point.payload:
                filename = point.payload.get("filename", "unknown")
                doc_type = point.payload.get("type", "text")
                
                if filename not in documents:
                    documents[filename] = {
                        "filename": filename,
                        "type": doc_type,
                        "chunks": 0,
                        "first_seen": datetime.now().isoformat()
                    }
                
                documents[filename]["chunks"] += 1
        
        # Create activity items
        for i, (filename, data) in enumerate(list(documents.items())[:10]):
            activities.append({
                "id": f"activity_{i}",
                "type": "upload" if data["type"] == "text" else "agent",
                "title": f"{data['type'].title()} Processed",
                "description": f"{filename} - {data['chunks']} chunks generated",
                "timestamp": "Just now",
                "user": "System",
                "metadata": {
                    "files": [filename],
                    "chunks": data["chunks"],
                    "type": data["type"]
                }
            })
        
        # Add some mock system activities for demo
        activities.extend([
            {
                "id": "system_1",
                "type": "system",
                "title": "System Health Check",
                "description": "All services running normally",
                "timestamp": "5 minutes ago",
                "metadata": {"status": "healthy"}
            },
            {
                "id": "query_1", 
                "type": "query",
                "title": "Search Query Executed",
                "description": "User performed semantic search",
                "timestamp": "12 minutes ago",
                "user": "Anonymous User",
                "metadata": {"queryType": "semantic", "results": 5}
            }
        ])
        
        return {"activities": activities[:20]}  # Return last 20 activities
    except Exception as e:
        return {"activities": [], "error": str(e)}

@router.post("/search")
async def hybrid_search(request: QueryRequest):
    """Hybrid search endpoint combining vector and keyword search"""
    try:
        # Extract query from request
        user_query = getattr(request, 'query', getattr(request, 'question', None))
        
        if not user_query:
            raise ValueError("No query or question found in request body")
        
        # Get search mode from request (default to hybrid)
        search_mode = getattr(request, 'search_mode', 'hybrid')
        top_k = getattr(request, 'top_k', 5)
        
        # Perform hybrid search
        results = await retrieve(user_query, search_mode=search_mode, top_k=top_k)
        
        # Generate answer using the retrieved context
        context = "\n---\n".join([doc["text"] for doc in results]) if results else "No relevant context found."
        system_prompt = "You are a helpful assistant. Use the provided context to answer the user's question."
        user_prompt = f"Context:\n{context}\n\nQuestion: {user_query}"
        
        response_text = generate_answer(system_prompt, user_prompt)
        
        # Return results with search metadata
        return {
            "answer": response_text,
            "results": results,
            "search_mode": search_mode,
            "total_results": len(results),
            "query": user_query
        }
        
    except Exception as e:
        print(f"ERROR in /search endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))