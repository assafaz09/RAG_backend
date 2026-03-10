from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Body
from .agents.graph import graph
from app.api.routes import router as api_router
from app.core.logging import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="RAG AI System")

user_mcp_config = {} 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.post("/deploy-mcp")
async def deploy_mcp(config: dict = Body(...)):
    global user_mcp_config
    user_mcp_config = config
    return {"status": "MCP Server Configured"}


@app.post("/chat")
async def chat(message: str = Body(...)):

    global user_mcp_config

    inputs = {
        "messages": [{"role": "user", "content": message}],
        "mcp_config": user_mcp_config
    }
    result = await graph.ainvoke(inputs)
    return {"response": result["messages"][-1]["content"]}

@app.get("/mcp-servers")
async def get_mcp_servers():
    global user_mcp_config
    # אם יש קונפיגורציה, נחזיר את השם שלה במערך
    if user_mcp_config and "name" in user_mcp_config:
        return {"servers": [user_mcp_config["name"]]}
    return {"servers": []}