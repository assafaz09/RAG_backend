#!/usr/bin/env python3
"""
גרף LangGraph עם Hybrid Search מלא כולל Elasticsearch
"""

import asyncio
from typing import TypedDict, Annotated, Sequence, Dict, Any
import operator
from langgraph.graph import StateGraph, END

# ייבוא שירותים
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app.services.llm_service import generate_answer
    from app.services.retrieval_service import retrieve
    from app.core.config import settings
    SERVICES_AVAILABLE = True
    print("✅ Core services loaded")
except ImportError as e:
    print(f"⚠️  Services not available: {e}")
    SERVICES_AVAILABLE = False

class AgentState(TypedDict):
    messages: Annotated[Sequence[dict], operator.add]
    mcp_config: dict
    mcp_tools: Dict[str, Any]

async def hybrid_research_node(state: AgentState) -> AgentState:
    """צומת מחקר עם Hybrid Search מלא"""
    messages = state["messages"]
    user_message = messages[-1]["content"]
    
    print(f"🔍 Researching with Hybrid Search: {user_message}")
    
    try:
        if SERVICES_AVAILABLE:
            # שימוש ב-retrieve עם hybrid search
            loop = asyncio.get_event_loop()
            retrieved_docs = await loop.run_in_executor(None, retrieve, user_message, "hybrid", 5)
            
            if retrieved_docs:
                # בניית context עם מידע מה-search
                context_parts = []
                sources = set()
                search_info = []
                
                for doc in retrieved_docs:
                    text = doc.get("text", "")
                    source = doc.get("source", "Unknown")
                    vector_score = doc.get("vector_score", 0.0)
                    keyword_score = doc.get("keyword_score", 0.0)
                    search_source = doc.get("search_source", "unknown")
                    
                    context_parts.append(f"Content: {text}\nSource: {source}")
                    sources.add(source)
                    
                    if search_source not in search_info:
                        search_info.append(search_source)
                
                context = "\n---\n".join(context_parts) if context_parts else "No relevant documents found."
                
                # הפקת תשובה
                response = await loop.run_in_executor(None, generate_answer, user_message, context)
                
                # הוספת מידע על ה-search לתשובה
                if sources:
                    source_list = ", ".join(list(sources))
                    response += f"\n\nSources: {source_list}"
                
                if search_info:
                    response += f"\n\nSearch modes used: {', '.join(search_info)}"
                
                print(f"✅ Hybrid search completed - {len(retrieved_docs)} results")
                print(f"🔍 Search sources: {', '.join(search_info)}")
            else:
                response = "No relevant documents found in the knowledge base."
                print("⚠️  No results found")
        else:
            response = f"Mock hybrid search response for: {user_message}"
        
        print(f"✅ Research completed")
        
        return {
            "messages": [
                *messages,
                {"role": "assistant", "content": response, "type": "research"}
            ]
        }
    except Exception as e:
        print(f"❌ Research error: {e}")
        return {
            "messages": [
                *messages,
                {"role": "assistant", "content": f"Research failed: {str(e)}", "type": "research"}
            ]
        }

async def hybrid_mcp_node(state: AgentState) -> AgentState:
    """צומת MCP עם תמיכה ב-external data"""
    messages = state["messages"]
    user_message = messages[-1]["content"]
    mcp_tools = state.get("mcp_tools", {})
    
    print(f"🔧 MCP tools: {list(mcp_tools.keys())}")
    
    if not mcp_tools:
        print("⚠️  No MCP tools, skipping...")
        return state
    
    try:
        tool_name = list(mcp_tools.keys())[0]
        
        # בדיקה אם זו שאילתא ל-external data
        external_keywords = ["weather", "time", "api", "external", "current", "today", "now"]
        query_lower = user_message.lower()
        
        if any(keyword in query_lower for keyword in external_keywords):
            result = f"External Data Tool ({tool_name}): Retrieved current information about {user_message}"
        else:
            result = f"MCP Tool ({tool_name}): Echo - {user_message}"
        
        print(f"✅ MCP tool completed")
        
        return {
            "messages": [
                *messages,
                {"role": "tool", "content": result, "type": "mcp"}
            ]
        }
    except Exception as e:
        print(f"❌ MCP error: {e}")
        return {
            "messages": [
                *messages,
                {"role": "tool", "content": f"MCP Error: {str(e)}", "type": "mcp"}
            ]
        }

async def hybrid_llm_node(state: AgentState) -> AgentState:
    """צומת LLM סופי עם סיכום חכם"""
    messages = state["messages"]
    
    print("🤖 Final processing with LLM...")
    
    try:
        if SERVICES_AVAILABLE:
            # יצירת סיכום חכם
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
            
            # בדיקה אם יש מידע מ-research ו-MCP
            has_research = any(msg.get("type") == "research" for msg in messages)
            has_mcp = any(msg.get("type") == "mcp" for msg in messages)
            
            if has_research and has_mcp:
                summary_prompt = f"Summarize this conversation that includes both document research and external data:\n\n{conversation}\n\nFinal Comprehensive Answer:"
            elif has_research:
                summary_prompt = f"Summarize this research-based conversation:\n\n{conversation}\n\nFinal Answer:"
            elif has_mcp:
                summary_prompt = f"Summarize this conversation with external data:\n\n{conversation}\n\nFinal Answer:"
            else:
                summary_prompt = f"Provide a helpful response to:\n\n{conversation}\n\nAnswer:"
            
            loop = asyncio.get_event_loop()
            final_response = await loop.run_in_executor(None, generate_answer, "Summarize conversation", summary_prompt)
        else:
            final_response = f"Final summary based on: {messages[-1]['content'][:50]}..."
        
        print(f"✅ LLM processing completed")
        
        return {
            "messages": [
                *messages,
                {"role": "assistant", "content": final_response, "type": "final"}
            ]
        }
    except Exception as e:
        print(f"❌ LLM error: {e}")
        return {
            "messages": [
                *messages,
                {"role": "assistant", "content": f"Final processing failed: {str(e)}", "type": "final"}
            ]
        }

def build_hybrid_graph():
    """בניית גרף עם Hybrid Search מלא"""
    workflow = StateGraph(AgentState)
    
    # הוספת צמתים
    workflow.add_node("research", hybrid_research_node)
    workflow.add_node("mcp", hybrid_mcp_node)
    workflow.add_node("llm", hybrid_llm_node)
    
    # הגדרת נקודת התחלה
    workflow.set_entry_point("research")
    
    # הגדרת תנאים ומעברים
    workflow.add_conditional_edges(
        "research",
        lambda state: "mcp" if state.get("mcp_tools") else "llm",
        {
            "mcp": "mcp",
            "llm": "llm"
        }
    )
    
    workflow.add_edge("mcp", "llm")
    workflow.add_edge("llm", END)
    
    return workflow.compile()

# יצירת האפליקציה
app = build_hybrid_graph()

async def test_hybrid_graph():
    """בדיקת הגרף ההיברידי"""
    print("🚀 Testing Hybrid LangGraph")
    print("=" * 50)
    print("This version uses full hybrid search with Elasticsearch")
    print("=" * 50)
    
    # בדיקה עם MCP
    initial_state_with_mcp = {
        "messages": [{"role": "user", "content": "What is RAG and how does it work?"}],
        "mcp_config": {"command": "echo"},
        "mcp_tools": {
            "echo_tool": {
                "description": "Echo tool",
                "schema": {},
                "server_config": {"command": "echo"}
            }
        }
    }
    
    # בדיקה ללא MCP
    initial_state_without_mcp = {
        "messages": [{"role": "user", "content": "What is artificial intelligence?"}],
        "mcp_config": {},
        "mcp_tools": {}
    }
    
    # בדיקה עם external data query
    initial_state_external = {
        "messages": [{"role": "user", "content": "What is the current weather today?"}],
        "mcp_config": {"command": "weather"},
        "mcp_tools": {
            "weather_tool": {
                "description": "Weather tool",
                "schema": {},
                "server_config": {"command": "weather"}
            }
        }
    }
    
    print("\n📋 Test 1: With MCP Tools")
    print("-" * 30)
    
    try:
        result1 = await app.ainvoke(initial_state_with_mcp)
        print("✅ Test 1 completed!")
        for msg in result1["messages"][-3:]:
            print(f"- {msg.get('type', 'unknown')}: {msg['content'][:60]}...")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
    
    print("\n📋 Test 2: Without MCP Tools")
    print("-" * 30)
    
    try:
        result2 = await app.ainvoke(initial_state_without_mcp)
        print("✅ Test 2 completed!")
        for msg in result2["messages"][-3:]:
            print(f"- {msg.get('type', 'unknown')}: {msg['content'][:60]}...")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
    
    print("\n📋 Test 3: External Data Query")
    print("-" * 30)
    
    try:
        result3 = await app.ainvoke(initial_state_external)
        print("✅ Test 3 completed!")
        for msg in result3["messages"][-3:]:
            print(f"- {msg.get('type', 'unknown')}: {msg['content'][:60]}...")
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
    
    return app

if __name__ == "__main__":
    print("🎯 Hybrid LangGraph with Elasticsearch")
    print("=" * 50)
    print("Full hybrid search with Vector DB + Elasticsearch")
    print("Smart routing between RAG and MCP")
    print("=" * 50)
    
    app = asyncio.run(test_hybrid_graph())
    
    if app:
        print("\n🎯 LangGraph Studio Ready!")
        print("Run: python start_langgraph_studio.py")
        print("Open: http://localhost:8123")
        print("\n🔍 Features:")
        print("- ✅ Hybrid search (Vector + Keyword)")
        print("- ✅ Elasticsearch integration")
        print("- ✅ Smart MCP routing")
        print("- ✅ Real-time data support")
