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
from app.services.conversation_persistence import conversation_persistence
from app.dependencies.auth import get_current_active_user, get_optional_current_user
from .orchestrator.orchestrator import orchestrator
from .orchestrator.schemas import OrchestrationRequest, OrchestrationResponse, AgentType
import uuid
import json

logger = setup_logger(__name__)

app = FastAPI(title="RAG AI System")

from app.services.user_mcp_service import user_mcp_service

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
async def deploy_mcp(
    config: dict = Body(...), 
    current_user: User = Depends(get_current_active_user)
):
    user_id = str(current_user.id)
    user_mcp_service.set_config(user_id, config)
    
    try:
        tools = await discover_mcp_tools(config)
        user_mcp_service.set_tools(user_id, tools)
        logger.info(f"Discovered {len(tools)} MCP tools for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to discover MCP tools: {e}")
        if config.get('main_tool'):
            user_mcp_service.set_tools(user_id, {
                config['main_tool']: {
                    "description": f"Main tool: {config['main_tool']}",
                    "schema": {"type": "object", "properties": {}},
                    "server_config": config
                }
            })
    
    return {
        "status": "MCP Server Configured",
        "user_id": user_id,
        "tools": list(user_mcp_service.get_tools(user_id, {}).keys()),
        "tool_details": {name: {"description": info["description"]} 
                         for name, info in user_mcp_service.get_tools(user_id, {}).items()}
    }


@app.post("/chat")
async def chat(
    message: str = Body(...),
    thread_id: str = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user_id = str(current_user.id)

    # 1. Get or create conversation for the user
    conv = conversation_persistence.get_or_create_conversation(
        db, user_id, thread_id
    )

    # 2. Save user message
    user_msg = Message(conversation_id=conv.id, role="user", content=message)
    db.add(user_msg)
    db.commit()

    # 3. Invoke Agent Graph with user context
    inputs = {
        "messages": [{"role": "user", "content": message}],
        "mcp_config": user_mcp_service.get_config(user_id) or {},
        "mcp_tools": user_mcp_service.get_tools(user_id) or {},  
        "user_id": user_id,
        "thread_id": conv.thread_id,
        "filesystem_root": f"user_data/{user_id}"
    }
    
    # Configure with checkpoint saver for persistence
    config = {
        "thread_id": conv.thread_id,
        "user_id": user_id
    }
    
    result = await graph.ainvoke(inputs, config=config)
    response_content = result["messages"][-1]["content"]

    # 5. Save assistant response
    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=response_content)
    db.add(assistant_msg)
    db.commit()

    return {
        "response": response_content,
        "thread_id": conv.thread_id,
        "conversation_id": str(conv.id)
    }

@app.get("/mcp-servers")
async def get_mcp_servers(current_user: User = Depends(get_current_active_user)):
    user_id = str(current_user.id)
    config = user_mcp_service.get_config(user_id) or {}
    tools = user_mcp_service.get_tools(user_id) or {}
    
    if config and "name" in config:
        return {
            "servers": [config["name"]],
            "tools": list(tools.keys()),
            "tool_details": {name: {"description": info["description"]} 
                             for name, info in tools.items()}
        }
    return {"servers": [], "tools": []}


# Conversation Management Endpoints

@app.get("/conversations")
async def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all conversations for the current user"""
    conversations = conversation_persistence.list_user_conversations(db, current_user)
    return {
        "conversations": [
            {
                "id": str(conv.id),
                "title": conv.title,
                "thread_id": conv.thread_id,
                "created_at": conv.created_at.isoformat()
            }
            for conv in conversations
        ]
    }

@app.get("/conversations/{thread_id}")
async def get_conversation(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific conversation with all messages"""
    # Validate user access
    if not conversation_persistence.validate_user_access(current_user, thread_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv = db.query(Conversation).filter(
        Conversation.thread_id == thread_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(Message).filter(
        Message.conversation_id == conv.id
    ).order_by(Message.created_at).all()
    
    return {
        "conversation": {
            "id": str(conv.id),
            "title": conv.title,
            "thread_id": conv.thread_id,
            "created_at": conv.created_at.isoformat()
        },
        "messages": [
            {
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    }

@app.delete("/conversations/{thread_id}")
async def delete_conversation(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a conversation and all its data"""
    success = conversation_persistence.delete_conversation(db, current_user, thread_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"message": "Conversation deleted successfully"}


# Multi-Agent Orchestration Endpoints

@app.post("/orchestrate")
async def start_orchestration(
    request: OrchestrationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Start a new multi-agent orchestration session"""
    try:
        # Add user context to orchestration
        session = await orchestrator.start_session(
            goal=request.goal,
            preferred_agents=request.preferred_agents,
            user_id=str(current_user.id)
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
async def list_orchestration_sessions(
    current_user: User = Depends(get_current_active_user)
):
    """List all orchestration sessions for the current user"""
    sessions = orchestrator.list_sessions(user_id=str(current_user.id))
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
