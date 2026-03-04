from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router as api_router
from app.core.logging import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="RAG AI System")

# allow cross‑origin requests from frontend dev server etc.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change if you want stricter rules
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    logger.info("Starting RAG AI System")
