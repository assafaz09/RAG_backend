import uuid
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

# Handle missing API key gracefully
try:
    llm = ChatOpenAI(model="gpt-4o")
except Exception:
    llm = None

from .schemas import (
    AgentState, AgentTask, TaskStatus, SessionStatus, 
    AgentType, AgentCapability, OrchestrationSession
)
from ..agents.graph import rag_agent, mcp_agent
from .specialized_agents import SPECIALIZED_AGENTS, EXTENDED_AGENT_TYPES


class AgentRegistry:
    """Registry for managing available agents and their capabilities"""
    
    def __init__(self):
        self._agents: Dict[AgentType, AgentCapability] = {}
        self._agent_functions: Dict[AgentType, callable] = {}
        self._register_default_agents()
    
    def _register_default_agents(self):
        """Register default agents with their capabilities"""
        
        # Research Agent (RAG)
        self.register_agent(
            AgentCapability(
                agent_type=AgentType.RESEARCH,
                name="Research Agent",
                description="Searches and analyzes documents using RAG",
                input_schema={"type": "string", "description": "Research query"},
                output_schema={"type": "string", "description": "Research findings"},
                can_run_parallel=True,
                estimated_duration=30
            ),
            rag_agent
        )
        
        # MCP Agent
        self.register_agent(
            AgentCapability(
                agent_type=AgentType.MCP,
                name="MCP Agent",
                description="Executes external tools via MCP protocol",
                input_schema={"type": "string", "description": "Tool execution request"},
                output_schema={"type": "string", "description": "Tool execution result"},
                can_run_parallel=True,
                estimated_duration=45
            ),
            mcp_agent
        )
        
        # Data Agent
        self.register_agent(
            AgentCapability(
                agent_type=AgentType.DATA,
                name="Data Agent",
                description="Processes and analyzes data",
                input_schema={"type": "object", "description": "Data processing task"},
                output_schema={"type": "object", "description": "Processed data"},
                can_run_parallel=False,
                estimated_duration=60
            ),
            self._data_agent
        )
        
        # Reviewer Agent
        self.register_agent(
            AgentCapability(
                agent_type=AgentType.REVIEWER,
                name="Reviewer Agent",
                description="Reviews and synthesizes results from other agents",
                input_schema={"type": "array", "description": "Results to review"},
                output_schema={"type": "string", "description": "Synthesized review"},
                can_run_parallel=False,
                estimated_duration=20
            ),
            self._reviewer_agent
        )
        
        # Register specialized agents
        for agent_type, capability in EXTENDED_AGENT_TYPES.items():
            agent_class = SPECIALIZED_AGENTS.get(AgentType(agent_type))
            if agent_class:
                self.register_agent(capability, agent_class.execute)
    
    def register_agent(self, capability: AgentCapability, agent_function: callable):
        """Register an agent with its capability and function"""
        self._agents[capability.agent_type] = capability
        self._agent_functions[capability.agent_type] = agent_function
    
    def get_agent(self, agent_type: AgentType) -> Optional[AgentCapability]:
        """Get agent capability by type"""
        return self._agents.get(agent_type)
    
    def get_agent_function(self, agent_type: AgentType) -> Optional[callable]:
        """Get agent function by type"""
        return self._agent_functions.get(agent_type)
    
    def list_agents(self) -> List[AgentCapability]:
        """List all available agents"""
        return list(self._agents.values())
    
    def get_parallel_agents(self) -> List[AgentCapability]:
        """Get agents that can run in parallel"""
        return [agent for agent in self._agents.values() if agent.can_run_parallel]
    
    async def _data_agent(self, state: AgentState) -> Dict[str, Any]:
        """Data processing agent implementation"""
        try:
            # Placeholder for data processing logic
            task = next((t for t in state["tasks"] if t.id == state["current_task_id"]), None)
            if not task:
                return {"error": "Task not found"}
            
            # Simulate data processing
            await asyncio.sleep(1)
            
            return {
                "tasks": [{
                    "id": task.id,
                    "status": TaskStatus.COMPLETED,
                    "output": {"processed_data": f"Processed: {task.input}"},
                    "completed_at": datetime.utcnow()
                }]
            }
        except Exception as e:
            return {"error": f"Data agent error: {str(e)}"}
    
    async def _reviewer_agent(self, state: AgentState) -> Dict[str, Any]:
        """Reviewer agent implementation"""
        try:
            # Placeholder for reviewer logic
            task = next((t for t in state["tasks"] if t.id == state["current_task_id"]), None)
            if not task:
                return {"error": "Task not found"}
            
            # Get results from other completed tasks
            completed_tasks = [t for t in state["tasks"] if t.status == TaskStatus.COMPLETED]
            
            # Simulate review process
            if not llm:
                return {"tasks": [{"id": task.id, "status": TaskStatus.COMPLETED, "output": {"review": "LLM unavailable - basic review completed"}, "completed_at": datetime.utcnow()}]}
            
            review_prompt = f"""
            Please review and synthesize these results:
            {completed_tasks}
            
            Original goal: {state['goal']}
            
            Provide a comprehensive summary and recommendations.
            """
            
            review_result = await llm.ainvoke(review_prompt)
            
            return {
                "tasks": [{
                    "id": task.id,
                    "status": TaskStatus.COMPLETED,
                    "output": {"review": review_result.content},
                    "completed_at": datetime.utcnow()
                }]
            }
        except Exception as e:
            return {"error": f"Reviewer agent error: {str(e)}"}


class MultiAgentOrchestrator:
    """Main orchestrator for multi-agent workflows"""
    
    def __init__(self):
        self.registry = AgentRegistry()
        self.sessions: Dict[str, OrchestrationSession] = {}
        self.graph = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for multi-agent orchestration"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("planner", self._plan_tasks)
        workflow.add_node("executor", self._execute_tasks)
        workflow.add_node("reviewer", self._review_results)
        workflow.add_node("error_handler", self._handle_error)
        
        # Add edges
        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "executor")
        workflow.add_conditional_edges(
            "executor",
            self._check_execution_status,
            {
                "continue": "executor",
                "review": "reviewer",
                "error": "error_handler"
            }
        )
        workflow.add_edge("reviewer", END)
        workflow.add_edge("error_handler", END)
        
        return workflow.compile()
    
    async def _plan_tasks(self, state: AgentState) -> Dict[str, Any]:
        """Plan tasks based on the goal"""
        try:
            goal = state["goal"]
            session_id = state["session_id"]
            
            # Use LLM to analyze goal and plan tasks
            if not llm:
                # Fallback to simple task planning without LLM
                tasks = []
                research_task = AgentTask(
                    id=str(uuid.uuid4()),
                    agent_type=AgentType.RESEARCH,
                    status=TaskStatus.PENDING,
                    input=goal,
                    dependencies=[]
                )
                tasks.append(research_task)
                
                reviewer_task = AgentTask(
                    id=str(uuid.uuid4()),
                    agent_type=AgentType.REVIEWER,
                    status=TaskStatus.PENDING,
                    input="Review all results",
                    dependencies=[task.id for task in tasks]
                )
                tasks.append(reviewer_task)
                
                return {
                    "tasks": tasks,
                    "status": SessionStatus.EXECUTING,
                    "messages": [{"role": "system", "content": f"Planned {len(tasks)} tasks for goal: {goal} (LLM unavailable)"}]
                }
            
            available_agents = self.registry.list_agents()
            agents_desc = "\n".join([
                f"- {cap.agent_type.value}: {cap.description}"
                for cap in available_agents
            ])
            
            planning_prompt = f"""
            Goal: {goal}
            
            Available agents:
            {agents_desc}
            
            Plan the tasks needed to achieve this goal. For each task, specify:
            1. Which agent should handle it
            2. What the task input should be
            3. Dependencies (if any)
            
            Return as JSON array of tasks.
            """
            
            planning_result = await llm.ainvoke(planning_prompt)
            
            # Parse planning result and create tasks
            # For now, create simple task structure
            tasks = []
            
            # Always add research task first
            research_task = AgentTask(
                id=str(uuid.uuid4()),
                agent_type=AgentType.RESEARCH,
                status=TaskStatus.PENDING,
                input=goal,
                dependencies=[]
            )
            tasks.append(research_task)
            
            # Add MCP task if goal suggests external data
            if any(keyword in goal.lower() for keyword in ["api", "data", "external", "current"]):
                mcp_task = AgentTask(
                    id=str(uuid.uuid4()),
                    agent_type=AgentType.MCP,
                    status=TaskStatus.PENDING,
                    input=goal,
                    dependencies=[]
                )
                tasks.append(mcp_task)
            
            # Always add reviewer task last
            reviewer_task = AgentTask(
                id=str(uuid.uuid4()),
                agent_type=AgentType.REVIEWER,
                status=TaskStatus.PENDING,
                input="Review all results",
                dependencies=[task.id for task in tasks]
            )
            tasks.append(reviewer_task)
            
            return {
                "tasks": tasks,
                "status": SessionStatus.EXECUTING,
                "messages": [{"role": "system", "content": f"Planned {len(tasks)} tasks for goal: {goal}"}]
            }
            
        except Exception as e:
            return {
                "status": SessionStatus.FAILED,
                "error": f"Planning failed: {str(e)}",
                "messages": [{"role": "system", "content": f"Planning error: {str(e)}"}]
            }
    
    async def _execute_tasks(self, state: AgentState) -> Dict[str, Any]:
        """Execute pending tasks"""
        try:
            tasks = state["tasks"]
            current_task_id = state.get("current_task_id")
            
            # Find next task to execute
            pending_tasks = [t for t in tasks if t.status == TaskStatus.PENDING]
            
            if not pending_tasks:
                return {"current_task_id": None}
            
            # Find task that can be executed (dependencies satisfied)
            executable_task = None
            for task in pending_tasks:
                if not task.dependencies:
                    executable_task = task
                    break
                else:
                    # Check if all dependencies are completed
                    deps_completed = all(
                        next((t for t in tasks if t.id == dep_id), None).status == TaskStatus.COMPLETED
                        for dep_id in task.dependencies
                    )
                    if deps_completed:
                        executable_task = task
                        break
            
            if not executable_task:
                return {"current_task_id": None}
            
            # Execute the task
            agent_function = self.registry.get_agent_function(executable_task.agent_type)
            if not agent_function:
                return {
                    "tasks": [{
                        "id": executable_task.id,
                        "status": TaskStatus.FAILED,
                        "error": f"Agent function not found for {executable_task.agent_type}",
                        "completed_at": datetime.utcnow()
                    }]
                }
            
            # Update task status to running
            executable_task.status = TaskStatus.RUNNING
            executable_task.started_at = datetime.utcnow()
            
            # Execute agent function
            agent_state = {
                **state,
                "current_task_id": executable_task.id,
                "messages": [{"role": "user", "content": executable_task.input}]
            }
            
            result = await agent_function(agent_state)
            
            # Update task with result
            if "error" in result:
                executable_task.status = TaskStatus.FAILED
                executable_task.error = result["error"]
            else:
                executable_task.status = TaskStatus.COMPLETED
                executable_task.output = result.get("output", result)
            
            executable_task.completed_at = datetime.utcnow()
            
            return {
                "tasks": [executable_task],
                "current_task_id": None,
                "messages": [{"role": "system", "content": f"Completed task: {executable_task.id}"}]
            }
            
        except Exception as e:
            return {
                "error": f"Execution failed: {str(e)}",
                "status": SessionStatus.FAILED
            }
    
    async def _review_results(self, state: AgentState) -> Dict[str, Any]:
        """Review and finalize results"""
        try:
            tasks = state["tasks"]
            completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
            
            # Create final summary
            results = [task.output for task in completed_tasks if task.output]
            
            return {
                "status": SessionStatus.COMPLETED,
                "shared_context": {"final_results": results},
                "messages": [{"role": "assistant", "content": f"Review completed. {len(completed_tasks)} tasks executed successfully."}]
            }
            
        except Exception as e:
            return {
                "status": SessionStatus.FAILED,
                "error": f"Review failed: {str(e)}"
            }
    
    async def _handle_error(self, state: AgentState) -> Dict[str, Any]:
        """Handle errors in the workflow"""
        error = state.get("error", "Unknown error")
        return {
            "status": SessionStatus.FAILED,
            "messages": [{"role": "system", "content": f"Workflow failed: {error}"}]
        }
    
    def _check_execution_status(self, state: AgentState) -> str:
        """Check execution status and decide next step"""
        tasks = state["tasks"]
        
        # Check if any task failed
        failed_tasks = [t for t in tasks if t.status == TaskStatus.FAILED]
        if failed_tasks:
            return "error"
        
        # Check if all tasks are completed
        pending_tasks = [t for t in tasks if t.status in [TaskStatus.PENDING, TaskStatus.RUNNING]]
        if not pending_tasks:
            return "review"
        
        # Continue execution
        return "continue"
    
    async def start_session(self, goal: str, preferred_agents: Optional[List[AgentType]] = None) -> OrchestrationSession:
        """Start a new orchestration session"""
        session_id = str(uuid.uuid4())
        
        session = OrchestrationSession(
            id=session_id,
            goal=goal,
            status=SessionStatus.PLANNING
        )
        
        self.sessions[session_id] = session
        
        # Initialize workflow state
        initial_state = AgentState(
            session_id=session_id,
            goal=goal,
            tasks=[],
            shared_context={},
            current_task_id=None,
            status=SessionStatus.PLANNING,
            messages=[]
        )
        
        # Start workflow execution
        session.status = SessionStatus.EXECUTING
        session.started_at = datetime.utcnow()
        
        # Run workflow asynchronously
        asyncio.create_task(self._run_workflow(session_id, initial_state))
        
        return session
    
    async def _run_workflow(self, session_id: str, initial_state: AgentState):
        """Run the workflow for a session"""
        try:
            result = await self.graph.ainvoke(initial_state)
            
            # Update session with final state
            session = self.sessions.get(session_id)
            if session:
                session.status = result.get("status", SessionStatus.COMPLETED)
                session.tasks = result.get("tasks", [])
                session.shared_context = result.get("shared_context", {})
                session.completed_at = datetime.utcnow()
                session.error = result.get("error")
                
        except Exception as e:
            session = self.sessions.get(session_id)
            if session:
                session.status = SessionStatus.FAILED
                session.error = str(e)
                session.completed_at = datetime.utcnow()
    
    def get_session(self, session_id: str) -> Optional[OrchestrationSession]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def list_sessions(self) -> List[OrchestrationSession]:
        """List all sessions"""
        return list(self.sessions.values())


# Global orchestrator instance
orchestrator = MultiAgentOrchestrator()
