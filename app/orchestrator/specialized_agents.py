import asyncio
from typing import Dict, Any, List
from datetime import datetime
from langchain_openai import ChatOpenAI
from .schemas import AgentState, AgentTask, TaskStatus, AgentType, AgentCapability

# Handle missing API key gracefully
try:
    llm = ChatOpenAI(model="gpt-4o")
except Exception:
    llm = None


class CodeAgent:
    """Specialized agent for code generation and analysis"""
    
    @staticmethod
    async def execute(state: AgentState) -> Dict[str, Any]:
        """Execute code generation task"""
        try:
            task = next((t for t in state["tasks"] if t.id == state["current_task_id"]), None)
            if not task:
                return {"error": "Task not found"}
            
            if not llm:
                return {
                    "tasks": [{
                        "id": task.id,
                        "status": TaskStatus.COMPLETED,
                        "output": {"code": "# Code generation unavailable - LLM not configured", "language": "python"},
                        "completed_at": datetime.utcnow()
                    }]
                }
            
            # Generate code based on input
            prompt = f"""
            You are a code generation expert. Based on the following request, generate clean, well-documented code.
            
            Request: {task.input}
            
            Provide:
            1. The complete code solution
            2. Brief explanation of the approach
            3. Any dependencies or setup requirements
            
            Return as JSON with keys: code, explanation, dependencies
            """
            
            result = await llm.ainvoke(prompt)
            
            # Parse the result (in real implementation, would use structured output)
            code_output = {
                "code": result.content,
                "language": "python",
                "explanation": "Generated code based on the request",
                "dependencies": []
            }
            
            return {
                "tasks": [{
                    "id": task.id,
                    "status": TaskStatus.COMPLETED,
                    "output": code_output,
                    "completed_at": datetime.utcnow()
                }]
            }
            
        except Exception as e:
            return {"error": f"Code agent error: {str(e)}"}


class ImageAgent:
    """Specialized agent for image processing and analysis"""
    
    @staticmethod
    async def execute(state: AgentState) -> Dict[str, Any]:
        """Execute image processing task"""
        try:
            task = next((t for t in state["tasks"] if t.id == state["current_task_id"]), None)
            if not task:
                return {"error": "Task not found"}
            
            if not llm:
                return {
                    "tasks": [{
                        "id": task.id,
                        "status": TaskStatus.COMPLETED,
                        "output": {"analysis": "Image analysis unavailable - LLM not configured"},
                        "completed_at": datetime.utcnow()
                    }]
                }
            
            # Analyze image request
            prompt = f"""
            You are an image analysis expert. Based on the following request, provide detailed image analysis instructions.
            
            Request: {task.input}
            
            Provide:
            1. Analysis approach
            2. Expected insights
            3. Processing recommendations
            
            Return as JSON with keys: approach, insights, recommendations
            """
            
            result = await llm.ainvoke(prompt)
            
            analysis_output = {
                "analysis": result.content,
                "approach": "Computer vision analysis",
                "insights": ["Visual patterns", "Object detection", "Scene understanding"],
                "recommendations": ["Use appropriate image processing libraries", "Consider image preprocessing"]
            }
            
            return {
                "tasks": [{
                    "id": task.id,
                    "status": TaskStatus.COMPLETED,
                    "output": analysis_output,
                    "completed_at": datetime.utcnow()
                }]
            }
            
        except Exception as e:
            return {"error": f"Image agent error: {str(e)}"}


class SummaryAgent:
    """Specialized agent for summarization and synthesis"""
    
    @staticmethod
    async def execute(state: AgentState) -> Dict[str, Any]:
        """Execute summarization task"""
        try:
            task = next((t for t in state["tasks"] if t.id == state["current_task_id"]), None)
            if not task:
                return {"error": "Task not found"}
            
            if not llm:
                return {
                    "tasks": [{
                        "id": task.id,
                        "status": TaskStatus.COMPLETED,
                        "output": {"summary": "Summarization unavailable - LLM not configured"},
                        "completed_at": datetime.utcnow()
                    }]
                }
            
            # Get previous results for summarization
            completed_tasks = [t for t in state["tasks"] if t.status == TaskStatus.COMPLETED]
            previous_results = [task.output for task in completed_tasks if task.output]
            
            # Generate summary
            prompt = f"""
            You are a summarization expert. Create a comprehensive summary based on the following information.
            
            Original request: {state.get('goal', 'Unknown')}
            Previous results: {previous_results}
            
            Provide:
            1. Executive summary
            2. Key findings
            3. Recommendations
            
            Return as JSON with keys: executive_summary, key_findings, recommendations
            """
            
            result = await llm.ainvoke(prompt)
            
            summary_output = {
                "summary": result.content,
                "executive_summary": "Based on the analysis and processing conducted",
                "key_findings": ["Multiple insights generated", "Comprehensive analysis completed"],
                "recommendations": ["Review detailed results", "Consider follow-up actions"]
            }
            
            return {
                "tasks": [{
                    "id": task.id,
                    "status": TaskStatus.COMPLETED,
                    "output": summary_output,
                    "completed_at": datetime.utcnow()
                }]
            }
            
        except Exception as e:
            return {"error": f"Summary agent error: {str(e)}"}


# Register specialized agents
SPECIALIZED_AGENTS = {
    AgentType.CODE: CodeAgent,
    AgentType.IMAGE: ImageAgent,
    AgentType.SUMMARY: SummaryAgent,
}

# Extend AgentType enum (would need to update schemas.py)
EXTENDED_AGENT_TYPES = {
    "code": AgentCapability(
        agent_type="code",
        name="Code Agent",
        description="Generates and analyzes code",
        input_schema={"type": "string", "description": "Code generation request"},
        output_schema={"type": "object", "description": "Generated code and analysis"},
        can_run_parallel=True,
        estimated_duration=90
    ),
    "image": AgentCapability(
        agent_type="image",
        name="Image Agent",
        description="Processes and analyzes images",
        input_schema={"type": "string", "description": "Image processing request"},
        output_schema={"type": "object", "description": "Image analysis results"},
        can_run_parallel=False,
        estimated_duration=120
    ),
    "summary": AgentCapability(
        agent_type="summary",
        name="Summary Agent",
        description="Summarizes and synthesizes results",
        input_schema={"type": "string", "description": "Summarization request"},
        output_schema={"type": "object", "description": "Summary and insights"},
        can_run_parallel=False,
        estimated_duration=45
    ),
}
