import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.orchestrator.orchestrator import MultiAgentOrchestrator, AgentRegistry
from app.orchestrator.schemas import AgentType, TaskStatus, SessionStatus, AgentTask


class TestAgentRegistry:
    """Test cases for AgentRegistry"""
    
    def setup_method(self):
        self.registry = AgentRegistry()
    
    def test_register_agent(self):
        """Test agent registration"""
        from app.orchestrator.schemas import AgentCapability
        
        capability = AgentCapability(
            agent_type=AgentType.RESEARCH,
            name="Test Agent",
            description="Test description",
            input_schema={"type": "string"},
            output_schema={"type": "string"},
            can_run_parallel=True,
            estimated_duration=30
        )
        
        def test_agent(state):
            return {"test": "result"}
        
        self.registry.register_agent(capability, test_agent)
        
        assert self.registry.get_agent(AgentType.RESEARCH) == capability
        assert self.registry.get_agent_function(AgentType.RESEARCH) == test_agent
    
    def test_list_agents(self):
        """Test listing all agents"""
        agents = self.registry.list_agents()
        assert len(agents) >= 4  # Default agents
        
        agent_types = [agent.agent_type for agent in agents]
        assert AgentType.RESEARCH in agent_types
        assert AgentType.MCP in agent_types
    
    def test_get_parallel_agents(self):
        """Test getting parallel-capable agents"""
        parallel_agents = self.registry.get_parallel_agents()
        assert len(parallel_agents) >= 2  # Research and MCP should be parallel
        
        for agent in parallel_agents:
            assert agent.can_run_parallel == True


class TestMultiAgentOrchestrator:
    """Test cases for MultiAgentOrchestrator"""
    
    def setup_method(self):
        self.orchestrator = MultiAgentOrchestrator()
    
    @pytest.mark.asyncio
    async def test_start_session(self):
        """Test starting a new orchestration session"""
        session = await self.orchestrator.start_session("Test goal")
        
        assert session.id is not None
        assert session.goal == "Test goal"
        assert session.status == SessionStatus.EXECUTING
        assert session.created_at is not None
        assert session.started_at is not None
    
    def test_get_session(self):
        """Test retrieving a session"""
        # Create a session first
        session_id = "test-session-id"
        session = self.orchestrator.sessions[session_id] = MagicMock()
        
        retrieved = self.orchestrator.get_session(session_id)
        assert retrieved == session
    
    def test_list_sessions(self):
        """Test listing all sessions"""
        sessions = self.orchestrator.list_sessions()
        assert isinstance(sessions, list)
    
    @pytest.mark.asyncio
    async def test_plan_tasks(self):
        """Test task planning"""
        state = {
            "session_id": "test-session",
            "goal": "Test goal",
            "tasks": [],
            "shared_context": {},
            "current_task_id": None,
            "status": SessionStatus.PLANNING,
            "messages": []
        }
        
        result = await self.orchestrator._plan_tasks(state)
        
        assert "tasks" in result
        assert "status" in result
        assert len(result["tasks"]) >= 2  # Should have at least research and reviewer tasks
    
    @pytest.mark.asyncio
    async def test_execute_tasks(self):
        """Test task execution"""
        # Create a test task
        task_id = "test-task"
        task = AgentTask(
            id=task_id,
            agent_type=AgentType.RESEARCH,
            status=TaskStatus.PENDING,
            input="Test input",
            dependencies=[]
        )
        
        state = {
            "session_id": "test-session",
            "goal": "Test goal",
            "tasks": [task],
            "shared_context": {},
            "current_task_id": task_id,
            "status": SessionStatus.EXECUTING,
            "messages": []
        }
        
        result = await self.orchestrator._execute_tasks(state)
        
        assert "tasks" in result
        assert len(result["tasks"]) == 1
        assert result["tasks"][0].id == task_id
    
    @pytest.mark.asyncio
    async def test_review_results(self):
        """Test result review"""
        # Create test tasks
        completed_task = AgentTask(
            id="completed-task",
            agent_type=AgentType.RESEARCH,
            status=TaskStatus.COMPLETED,
            input="Test input",
            dependencies=[],
            output={"result": "test result"}
        )
        
        reviewer_task = AgentTask(
            id="reviewer-task",
            agent_type=AgentType.REVIEWER,
            status=TaskStatus.PENDING,
            input="Review results",
            dependencies=[]
        )
        
        state = {
            "session_id": "test-session",
            "goal": "Test goal",
            "tasks": [completed_task, reviewer_task],
            "shared_context": {},
            "current_task_id": "reviewer-task",
            "status": SessionStatus.EXECUTING,
            "messages": []
        }
        
        result = await self.orchestrator._review_results(state)
        
        assert "tasks" in result
        assert len(result["tasks"]) == 1
        assert result["tasks"][0].id == "reviewer-task"
    
    def test_check_execution_status(self):
        """Test execution status checking"""
        # Test completed tasks
        completed_tasks = [
            AgentTask(id="1", agent_type=AgentType.RESEARCH, status=TaskStatus.COMPLETED, input="input", dependencies=[]),
            AgentTask(id="2", agent_type=AgentType.MCP, status=TaskStatus.COMPLETED, input="input", dependencies=[])
        ]
        
        state = {"tasks": completed_tasks}
        result = self.orchestrator._check_execution_status(state)
        assert result == "review"
        
        # Test pending tasks
        pending_tasks = [
            AgentTask(id="1", agent_type=AgentType.RESEARCH, status=TaskStatus.PENDING, input="input", dependencies=[])
        ]
        
        state = {"tasks": pending_tasks}
        result = self.orchestrator._check_execution_status(state)
        assert result == "continue"
        
        # Test failed tasks
        failed_tasks = [
            AgentTask(id="1", agent_type=AgentType.RESEARCH, status=TaskStatus.FAILED, input="input", dependencies=[])
        ]
        
        state = {"tasks": failed_tasks}
        result = self.orchestrator._check_execution_status(state)
        assert result == "error"


class TestSpecializedAgents:
    """Test cases for specialized agents"""
    
    @pytest.mark.asyncio
    async def test_code_agent(self):
        """Test Code Agent execution"""
        from app.orchestrator.specialized_agents import CodeAgent
        
        task = AgentTask(
            id="test-code-task",
            agent_type="code",
            status=TaskStatus.PENDING,
            input="Generate a Python function to calculate factorial",
            dependencies=[]
        )
        
        state = {
            "session_id": "test-session",
            "goal": "Test goal",
            "tasks": [task],
            "shared_context": {},
            "current_task_id": "test-code-task",
            "status": SessionStatus.EXECUTING,
            "messages": []
        }
        
        result = await CodeAgent.execute(state)
        
        assert "tasks" in result
        assert len(result["tasks"]) == 1
        assert result["tasks"][0].status == TaskStatus.COMPLETED
        assert "output" in result["tasks"][0]
    
    @pytest.mark.asyncio
    async def test_image_agent(self):
        """Test Image Agent execution"""
        from app.orchestrator.specialized_agents import ImageAgent
        
        task = AgentTask(
            id="test-image-task",
            agent_type="image",
            status=TaskStatus.PENDING,
            input="Analyze this image for objects",
            dependencies=[]
        )
        
        state = {
            "session_id": "test-session",
            "goal": "Test goal",
            "tasks": [task],
            "shared_context": {},
            "current_task_id": "test-image-task",
            "status": SessionStatus.EXECUTING,
            "messages": []
        }
        
        result = await ImageAgent.execute(state)
        
        assert "tasks" in result
        assert len(result["tasks"]) == 1
        assert result["tasks"][0].status == TaskStatus.COMPLETED
        assert "output" in result["tasks"][0]
    
    @pytest.mark.asyncio
    async def test_summary_agent(self):
        """Test Summary Agent execution"""
        from app.orchestrator.specialized_agents import SummaryAgent
        
        # Create completed tasks for summarization
        completed_task = AgentTask(
            id="completed-task",
            agent_type=AgentType.RESEARCH,
            status=TaskStatus.COMPLETED,
            input="Research input",
            dependencies=[],
            output={"result": "Research findings"}
        )
        
        summary_task = AgentTask(
            id="summary-task",
            agent_type="summary",
            status=TaskStatus.PENDING,
            input="Summarize the results",
            dependencies=[]
        )
        
        state = {
            "session_id": "test-session",
            "goal": "Test goal",
            "tasks": [completed_task, summary_task],
            "shared_context": {},
            "current_task_id": "summary-task",
            "status": SessionStatus.EXECUTING,
            "messages": []
        }
        
        result = await SummaryAgent.execute(state)
        
        assert "tasks" in result
        assert len(result["tasks"]) == 1
        assert result["tasks"][0].status == TaskStatus.COMPLETED
        assert "output" in result["tasks"][0]


class TestIntegration:
    """Integration tests for the orchestration system"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow from start to finish"""
        orchestrator = MultiAgentOrchestrator()
        
        # Start a session
        session = await orchestrator.start_session("Analyze market trends and generate report")
        
        assert session.id is not None
        assert session.goal == "Analyze market trends and generate report"
        
        # Wait a bit for async processing
        await asyncio.sleep(0.1)
        
        # Check session status
        updated_session = orchestrator.get_session(session.id)
        assert updated_session is not None
        assert len(updated_session.tasks) > 0
    
    def test_agent_registry_integration(self):
        """Test agent registry integration with orchestrator"""
        orchestrator = MultiAgentOrchestrator()
        
        # Check that all required agents are registered
        agents = orchestrator.registry.list_agents()
        agent_types = [agent.agent_type for agent in agents]
        
        required_agents = [
            AgentType.RESEARCH,
            AgentType.MCP,
            AgentType.DATA,
            AgentType.REVIEWER
        ]
        
        for agent_type in required_agents:
            assert agent_type in agent_types
        
        # Check specialized agents are also registered
        specialized_agents = ["code", "image", "summary"]
        for agent_type in specialized_agents:
            assert any(agent.agent_type == agent_type for agent in agents)


if __name__ == "__main__":
    pytest.main([__file__])
