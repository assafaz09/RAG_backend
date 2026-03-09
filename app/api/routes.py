from fastapi import APIRouter, HTTPException, UploadFile, File
from app.schemas.schemas import IngestRequest, QueryRequest, QueryResponse
from app.services.ingestion_service import ingest_documents
from app.services.embedding_service import embed_texts
from app.services.retrieval_service import retrieve
from app.services.llm_service import generate_answer
from app.utils.file_parser import parse_file
from app.utils.chunking import chunk_text
import uuid

router = APIRouter()

@router.post("/ingest")
async def ingest(req: IngestRequest):
    try:
        ingest_documents(req.documents)
        return {"status": "ok", "ingested": len(req.documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text, _ = parse_file(content, file.filename)
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        docs = []
        for i, chunk in enumerate(chunks):
            doc_id = f"{file.filename}_{i}_{uuid.uuid4()}"
            docs.append({
                "id": doc_id,
                "text": chunk,
                "filename": file.filename,
                "meta": {"chunk_index": i, "total_chunks": len(chunks)},
            })
        ingest_documents(docs)
        return {"status": "ok", "filename": file.filename, "chunks_ingested": len(docs)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")

@router.get("/documents")
async def list_documents():
    from app.db.vector_db import get_qdrant_client
    from app.core.config import settings
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
        hits = retrieve(query_vector, top_k=request.top_k if hasattr(request, 'top_k') else 5)
        
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