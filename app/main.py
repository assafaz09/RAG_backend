from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Body
from .agents.graph import graph
from app.api.routes import router as api_router
from app.api.auth import router as auth_router
from app.core.logging import setup_logger
from app.services.mcp_service import discover_mcp_tools, run_mcp_tool

logger = setup_logger(__name__)

app = FastAPI(title="RAG AI System")

user_mcp_config = {}
user_mcp_tools = {}  

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router)


@app.get("/")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    logger.info("Starting RAG AI System")
    
    # Create database tables
    from app.db.database import engine, Base
    from app.db.models import User
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


@app.post("/deploy-mcp")
async def deploy_mcp(config: dict = Body(...)):
    global user_mcp_config, user_mcp_tools
    user_mcp_config = config
    
    # 
    try:
        user_mcp_tools = await discover_mcp_tools(config)
        logger.info(f"Discovered {len(user_mcp_tools)} MCP tools: {list(user_mcp_tools.keys())}")
    except Exception as e:
        logger.error(f"Failed to discover MCP tools: {e}")
        # 
        if config.get('main_tool'):
            user_mcp_tools = {
                config['main_tool']: {
                    "description": f"Main tool: {config['main_tool']}",
                    "schema": {"type": "object", "properties": {}},
                    "server_config": config
                }
            }
    
    return {
        "status": "MCP Server Configured",
        "tools": list(user_mcp_tools.keys()),
        "tool_details": {name: {"description": info["description"]} 
                         for name, info in user_mcp_tools.items()}
    }


@app.post("/chat")
async def chat(message: str = Body(...)):

    global user_mcp_config, user_mcp_tools

    inputs = {
        "messages": [{"role": "user", "content": message}],
        "mcp_config": user_mcp_config,
        "mcp_tools": user_mcp_tools,  
        "user_id": ""
    }
    result = await graph.ainvoke(inputs)
    return {"response": result["messages"][-1]["content"]}

@app.get("/mcp-servers")
async def get_mcp_servers():
    global user_mcp_config, user_mcp_tools
    # 
    if user_mcp_config and "name" in user_mcp_config:
        return {
            "servers": [user_mcp_config["name"]],
            "tools": list(user_mcp_tools.keys()),
            "tool_details": {name: {"description": info["description"]} 
                             for name, info in user_mcp_tools.items()}
        }
    return {"servers": [], "tools": []}