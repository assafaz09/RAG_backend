from fastapi import APIRouter
from typing import Dict, Any, List
import json

router = APIRouter()

@router.get("/structure")
async def get_graph_structure():
    """
    Returns the LangGraph structure for visualization
    """
    try:
        # This would typically come from the actual LangGraph instance
        # For now, return the actual structure from the graph.py file
        nodes = [
            {
                "id": "start",
                "name": "Start",
                "type": "start",
                "position": {"x": 100, "y": 50},
                "status": "completed"
            },
            {
                "id": "rag",
                "name": "RAG Agent",
                "type": "agent",
                "position": {"x": 300, "y": 50},
                "status": "completed"
            },
            {
                "id": "mcp_tools",
                "name": "MCP Tools",
                "type": "tool",
                "position": {"x": 500, "y": 50},
                "status": "pending"
            },
            {
                "id": "llm",
                "name": "LLM",
                "type": "agent", 
                "position": {"x": 700, "y": 50},
                "status": "pending"
            },
            {
                "id": "end",
                "name": "End",
                "type": "end",
                "position": {"x": 900, "y": 50},
                "status": "pending"
            }
        ]
        
        edges = [
            {"from": "start", "to": "rag", "label": "query"},
            {"from": "rag", "to": "mcp_tools", "label": "need_tools"},
            {"from": "mcp_tools", "to": "llm", "label": "context"},
            {"from": "rag", "to": "llm", "label": "direct"},
            {"from": "llm", "to": "end", "label": "response"}
        ]
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "graph_type": "langgraph"
            }
        }
        
    except Exception as e:
        return {
            "nodes": [],
            "edges": [],
            "error": str(e)
        }
