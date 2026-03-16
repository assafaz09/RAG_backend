from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Body, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from .agents.graph import graph
from app.api.routes import router as api_router
from app.api.auth import router as auth_router
from app.api.graph import router as graph_router
from app.core.logging import setup_logger
from app.services.mcp_service import discover_mcp_tools, run_mcp_tool
from app.db.database import get_db, engine, Base
from app.db.models import User, Conversation, Message
from .orchestrator.orchestrator import orchestrator
from .orchestrator.schemas import OrchestrationRequest, OrchestrationResponse, AgentType
import uuid
import json

logger = setup_logger(__name__)

app = FastAPI(title="RAG AI System")

# Simple in-memory storage for user-specific MCP configs (for demo purposes)
# In production, this would be in a database or Redis
user_mcp_configs = {}
user_mcp_tools_map = {}

# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_personal_message(self, message: str, session_id: str):
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_text(message)
    
    async def broadcast_to_session(self, message: str, session_id: str):
        await self.send_personal_message(message, session_id)

manager = ConnectionManager()  

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(auth_router)
app.include_router(graph_router, prefix="/api/graph", tags=["graph"])


@app.get("/")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
async def on_startup():
    logger.info("Starting RAG AI System")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


@app.post("/deploy-mcp")
async def deploy_mcp(config: dict = Body(...), user_id: str = "default"):
    global user_mcp_configs, user_mcp_tools_map
    user_mcp_configs[user_id] = config
    
    try:
        tools = await discover_mcp_tools(config)
        user_mcp_tools_map[user_id] = tools
        logger.info(f"Discovered {len(tools)} MCP tools for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to discover MCP tools: {e}")
        if config.get('main_tool'):
            user_mcp_tools_map[user_id] = {
                config['main_tool']: {
                    "description": f"Main tool: {config['main_tool']}",
                    "schema": {"type": "object", "properties": {}},
                    "server_config": config
                }
            }
    
    return {
        "status": "MCP Server Configured",
        "tools": list(user_mcp_tools_map.get(user_id, {}).keys()),
        "tool_details": {name: {"description": info["description"]} 
                         for name, info in user_mcp_tools_map.get(user_id, {}).items()}
    }


@app.post("/chat")
async def chat(
    message: str = Body(...), 
    user_id: str = "default",
    db: Session = Depends(get_db)
):
    global user_mcp_configs, user_mcp_tools_map

    # 1. Get or create a default conversation for the user
    # For now, we use a simple 'default' user if not provided
    user = db.query(User).first() # Just get the first user for demo
    if not user:
        # Create a dummy user for testing if none exists
        user = User(email="test@example.com", name="Test User")
        db.add(user)
        db.commit()
        db.refresh(user)

    conv = db.query(Conversation).filter(Conversation.user_id == user.id).first()
    if not conv:
        conv = Conversation(user_id=user.id, title="New Chat")
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2. Save user message
    user_msg = Message(conversation_id=conv.id, role="user", content=message)
    db.add(user_msg)
    db.commit()

    # 3. Invoke Agent Graph
    inputs = {
        "messages": [{"role": "user", "content": message}],
        "mcp_config": user_mcp_configs.get(user_id, {}),
        "mcp_tools": user_mcp_tools_map.get(user_id, {}),  
        "user_id": str(user.id)
    }
    
    result = await graph.ainvoke(inputs)
    response_content = result["messages"][-1]["content"]

    # 4. Save assistant response
    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=response_content)
    db.add(assistant_msg)
    db.commit()

    return {"response": response_content}

@app.get("/mcp-servers")
async def get_mcp_servers(user_id: str = "default"):
    config = user_mcp_configs.get(user_id, {})
    tools = user_mcp_tools_map.get(user_id, {})
    
    if config and "name" in config:
        return {
            "servers": [config["name"]],
            "tools": list(tools.keys()),
            "tool_details": {name: {"description": info["description"]} 
                             for name, info in tools.items()}
        }
    return {"servers": [], "tools": []}


# Multi-Agent Orchestration Endpoints

@app.post("/orchestrate")
async def start_orchestration(request: OrchestrationRequest):
    """Start a new multi-agent orchestration session"""
    try:
        session = await orchestrator.start_session(
            goal=request.goal,
            preferred_agents=request.preferred_agents
        )
        
        # Send initial status via WebSocket if connection exists
        await manager.broadcast_to_session(
            json.dumps({
                "type": "session_started",
                "session_id": session.id,
                "status": session.status.value,
                "goal": session.goal
            }),
            session.id
        )
        
        return {
            "session_id": session.id,
            "status": session.status.value,
            "goal": session.goal,
            "created_at": session.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to start orchestration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orchestrate/{session_id}")
async def get_orchestration_status(session_id: str):
    """Get the status of an orchestration session"""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Calculate progress
    if not session.tasks:
        progress = 0.0
    else:
        completed_tasks = len([t for t in session.tasks if t.status.value == "completed"])
        progress = completed_tasks / len(session.tasks)
    
    return OrchestrationResponse(
        session_id=session.id,
        status=session.status,
        tasks=session.tasks,
        shared_context=session.shared_context,
        progress=progress
    ).dict()


@app.post("/orchestrate/{session_id}/pause")
async def pause_orchestration(session_id: str):
    """Pause an orchestration session"""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status.value in ["executing", "planning"]:
        session.status = "paused"
        
        await manager.broadcast_to_session(
            json.dumps({
                "type": "session_paused",
                "session_id": session_id,
                "status": "paused"
            }),
            session_id
        )
        
        return {"status": "paused"}
    else:
        raise HTTPException(status_code=400, detail="Cannot pause session in current state")


@app.post("/orchestrate/{session_id}/resume")
async def resume_orchestration(session_id: str):
    """Resume a paused orchestration session"""
    session = orchestrator.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.status.value == "paused":
        session.status = "executing"
        
        await manager.broadcast_to_session(
            json.dumps({
                "type": "session_resumed",
                "session_id": session_id,
                "status": "executing"
            }),
            session_id
        )
        
        return {"status": "executing"}
    else:
        raise HTTPException(status_code=400, detail="Cannot resume session in current state")


@app.get("/orchestrate")
async def list_orchestration_sessions():
    """List all orchestration sessions"""
    sessions = orchestrator.list_sessions()
    return {
        "sessions": [
            {
                "id": session.id,
                "goal": session.goal,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "task_count": len(session.tasks)
            }
            for session in sessions
        ]
    }


@app.get("/agents")
async def list_available_agents():
    """List all available agents and their capabilities"""
    agents = orchestrator.registry.list_agents()
    return {
        "agents": [
            {
                "type": agent.agent_type.value,
                "name": agent.name,
                "description": agent.description,
                "can_run_parallel": agent.can_run_parallel,
                "estimated_duration": agent.estimated_duration
            }
            for agent in agents
        ]
    }


@app.websocket("/ws/orchestrate/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time orchestration updates"""
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Handle any client messages if needed
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        manager.disconnect(session_id)
