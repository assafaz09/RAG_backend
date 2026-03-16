from typing import TypedDict, Annotated, Sequence, Dict, Any, List, Optional, Literal
from enum import Enum
from datetime import datetime
import operator
from pydantic import BaseModel, Field


class AgentType(str, Enum):
    RESEARCH = "research"
    MCP = "mcp"
    DATA = "data"
    REVIEWER = "reviewer"
    ORCHESTRATOR = "orchestrator"
    CODE = "code"
    IMAGE = "image"
    SUMMARY = "summary"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class SessionStatus(str, Enum):
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class AgentTask(BaseModel):
    """Individual task for an agent"""
    id: str
    agent_type: AgentType
    status: TaskStatus
    input: str
    output: Optional[Any] = None
    dependencies: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationSession(BaseModel):
    """Multi-agent orchestration session"""
    id: str
    goal: str
    status: SessionStatus
    tasks: List[AgentTask] = Field(default_factory=list)
    shared_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AgentState(TypedDict):
    """LangGraph state for multi-agent orchestration"""
    session_id: str
    goal: str
    tasks: Annotated[List[AgentTask], operator.add]
    shared_context: Dict[str, Any]
    current_task_id: Optional[str]
    status: SessionStatus
    messages: Annotated[Sequence[dict], operator.add]


class AgentMessage(BaseModel):
    """Message from agent to orchestrator"""
    task_id: str
    agent_type: AgentType
    message_type: Literal["status_update", "result", "error"]
    content: Any
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentCapability(BaseModel):
    """Agent capability description"""
    agent_type: AgentType
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    can_run_parallel: bool = True
    estimated_duration: Optional[int] = None  # seconds


class OrchestrationRequest(BaseModel):
    """Request to start orchestration"""
    goal: str
    preferred_agents: Optional[List[AgentType]] = None
    requirements: Dict[str, Any] = Field(default_factory=dict)


class OrchestrationResponse(BaseModel):
    """Response for orchestration status"""
    session_id: str
    status: SessionStatus
    tasks: List[AgentTask]
    shared_context: Dict[str, Any]
    progress: float = Field(ge=0.0, le=1.0)  # 0.0 to 1.0
