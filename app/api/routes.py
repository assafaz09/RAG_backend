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
    """Upload and ingest a file (PDF, DOCX, TXT, MD)."""
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
    """List all ingested documents."""
    from app.db.vector_db import get_qdrant_client
    from app.core.config import settings
    
    try:
        client = get_qdrant_client()
        collection_info = client.get_collection(collection_name=settings.QDRANT_COLLECTION)
        count = collection_info.points_count
        results = client.scroll(collection_name=settings.QDRANT_COLLECTION, limit=100)
        filenames = set()
        for point in results[0]:
            if hasattr(point.payload, '__getitem__'):
                fname = point.payload.get("filename", "unknown")
            else:
                fname = getattr(point.payload, "filename", "unknown")
            filenames.add(fname)
        return {"total_points": count, "documents": sorted(list(filenames))}
    except Exception as e:
        return {"total_points": 0, "documents": [], "error": str(e)}

@router.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    # 1. יצירת ווקטור לשאלה
    vectors = embed_texts([req.question])
    if not vectors or len(vectors) == 0:
        raise HTTPException(status_code=400, detail="Embedding failed")
    
    # 2. חיפוש ב-Qdrant
    hits = retrieve(vectors[0], top_k=req.top_k)
    
    print(f"DEBUG: Found {len(hits)} hits. Top score: {hits[0].score if hits else 'N/A'}")
    
    relevant_texts = []
    for i, h in enumerate(hits):
        # וידוא שה-payload קיים והמפתח text קיים
        text_chunk = h.payload.get('text') if h.payload else None
        if text_chunk:
            print(f"Hit {i} (Score: {h.score}): {text_chunk[:50]}...")
            relevant_texts.append(text_chunk)

    # 3. בניית הקונטקסט
    context = "\n\n".join(relevant_texts)
    
    if not context.strip():
        print("DEBUG: No context found for this query.")
        return QueryResponse(answer="Sorry, I couldn't find relevant information in the uploaded documents.", sources=[])

    # 4. הדפסת הקונטקסט שנשלח ל-AI (כדי שתוכל לראות בטרמינל)
    print(f"DEBUG: Sending context to LLM (Length: {len(context)})")

    # 5. יצירת תשובה
    answer = generate_answer(req.question, context)
    return QueryResponse(answer=answer, sources=[str(h.id) for h in hits])