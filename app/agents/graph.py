import json
from typing import TypedDict, Annotated, Sequence, Dict, Any, Optional
import operator
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

# Handle missing API key gracefully
try:
    llm = ChatOpenAI(model="gpt-4o")
except Exception:
    llm = None

from ..services.mcp_service import run_mcp_tool
from ..services.retrieval_service import retrieve
from ..services.embedding_service import embed_texts
from ..services.llm_service import generate_answer

class AgentState(TypedDict):
    messages: Annotated[Sequence[dict], operator.add]
    mcp_config: dict  # MCP configurations
    mcp_tools: Dict[str, Any]  # All discovered tools {name: {description, schema, server_config}}
    user_id: str  # User identifier
    thread_id: Optional[str]  # Thread identifier
    filesystem_root: Optional[str]  # Filesystem root

def extract_text_content(result) -> str:
    """
    Extract clean text from MCP result.
    Handles TextContent, list of TextContent, or regular string.
    """
    # If it's a list (like in the image you showed)
    if isinstance(result, list):
        texts = []
        for item in result:
            if hasattr(item, 'text'):
                texts.append(item.text)
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join(texts) if texts else str(result)
    
    # If it's a TextContent object
    if hasattr(result, 'text'):
        return result.text
    
    # If it's a string
    if isinstance(result, str):
        return result
    
    # Default
    return str(result)

# --- RAG Node (the old agent) ---
async def research_node(state: AgentState) -> AgentState:
    """RAG node - retrieve relevant information"""
    messages = state["messages"]
    user_message = messages[-1]["content"]
    
    # Retrieve relevant information using hybrid search
    retrieved_docs = await retrieve(user_message, search_mode="hybrid", top_k=5)
    
    # Create prompt with retrieved information
    context = "\n".join([doc["text"] for doc in retrieved_docs])
    prompt = f"""Context: {context}

Question: {user_message}

Please provide a comprehensive answer based on the context above."""
    
    # Generate response
    response = await generate_answer(prompt)
    
    return {
        "messages": [
            *messages,
            {"role": "assistant", "content": response}
        ]
    }

# --- MCP Node ---
async def mcp_node(state: AgentState) -> AgentState:
    """MCP node - execute MCP tool"""
    messages = state["messages"]
    user_message = messages[-1]["content"]
    mcp_tools = state.get("mcp_tools", {})
    
    if not mcp_tools:
        # If no tools available, continue without MCP
        return state
    
    # Select first available tool (in practice will have smarter logic)
    tool_name = list(mcp_tools.keys())[0]
    tool_config = mcp_tools[tool_name]["server_config"]
    
    try:
        # Execute the tool
        result = await run_mcp_tool(tool_name, {"query": user_message}, tool_config)
        result_text = extract_text_content(result)
        
        return {
            "messages": [
                *messages,
                {"role": "tool", "content": f"MCP Tool ({tool_name}): {result_text}"}
            ]
        }
    except Exception as e:
        return {
            "messages": [
                *messages,
                {"role": "tool", "content": f"MCP Tool Error: {str(e)}"}
            ]
        }

# --- Final LLM Node ---
async def llm_node(state: AgentState) -> AgentState:
    """Final LLM node - summarize and generate final response"""
    messages = state["messages"]
    
    if not llm:
        # If no LLM, return last message
        return state
    
    # Run LLM on all messages
    response = await llm.ainvoke(messages)
    
    return {
        "messages": [
            *messages,
            {"role": "assistant", "content": response.content}
        ]
    }

# --- Build the graph ---
def build_graph():
    """Build LangGraph graph"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("research", research_node)
    workflow.add_node("mcp", mcp_node)
    workflow.add_node("llm", llm_node)
    
    # Set entry point
    workflow.set_entry_point("research")
    
    # Set conditions and transitions
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

# --- Create application ---
app = build_graph()

# --- Add to LangGraph Studio ---
if __name__ == "__main__":
    # Run LangGraph Studio
    import langgraph
    langgraph.debug = True
    
    print("Starting LangGraph Studio...")
    print("Open http://localhost:8123 in your browser")
    
    # Run graph with example
    async def test_run():
        initial_state = {
            "messages": [{"role": "user", "content": "What is RAG?"}],
            "mcp_config": {},
            "mcp_tools": {}
        }
        
        result = await app.ainvoke(initial_state)
        print("Result:", result)
    
    import asyncio
    asyncio.run(test_run())


# --- RAG Agent (legacy) ---
async def rag_agent(state: AgentState):
    query = state['messages'][-1]['content']
    
    try:
        # Use hybrid search (default mode)
        hits = await retrieve(query, search_mode="hybrid", top_k=5)
        
        # Build context with citations and search info
        context_parts = []
        sources = set()
        search_info = []
        
        for hit in hits:
            text = hit["text"]
            source = hit["source"]
            vector_score = hit.get("vector_score", 0.0)
            keyword_score = hit.get("keyword_score", 0.0)
            search_source = hit.get("search_source", "unknown")
            
            context_parts.append(f"Content: {text}\nSource: {source}")
            sources.add(source)
            
            # Track search sources for debugging
            if search_source not in search_info:
                search_info.append(search_source)
        
        context = "\n---\n".join(context_parts) if hits else "No relevant context found in uploaded documents."
        
        # Create answer
        response_text = generate_answer(query, context)
        
        # Append source and search info to response
        if sources:
            source_list = ", ".join(list(sources))
            response_text += f"\n\nSources: {source_list}"
        
        # Add search mode info for debugging
        if search_info:
            response_text += f"\n\nSearch modes used: {', '.join(search_info)}"
        
        return {"messages": [{"role": "assistant", "content": response_text}]}
        
    except Exception as e:
        return {"messages": [{"role": "assistant", "content": f"Sorry, I encountered an error while searching your documents: {str(e)}"}]}

# --- MCP Agent (new agent) ---
async def mcp_agent(state: AgentState):
    mcp_tools = state.get('mcp_tools', {})
    query = state['messages'][-1]['content']
    
    # Check if there are available tools
    if not mcp_tools:
        return {"messages": [{"role": "assistant", "content": "No MCP tools configured. Please configure MCP first in the MCP Settings page."}]}

    try:
        # Agent chooses which tool to use from the list
        available_tools = list(mcp_tools.keys())
        
        # Create description of tools for prompt
        tools_description = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in mcp_tools.items()
        ])
        
        # Ask LLM which tool is appropriate
        tool_selection_prompt = f"""You have these MCP tools available:
{tools_description}

User question: "{query}"

Which tool should you use to answer this question? 
Respond ONLY with the tool name (one word), or say "none" if none of these tools are relevant.

Tool name:"""

        selection_response = await llm.ainvoke(tool_selection_prompt) if llm else None
        selected_tool = selection_response.content.strip().lower() if selection_response else "none"
        
        # If no tool is suitable - return to RAG
        if selected_tool == "none" or selected_tool not in mcp_tools:
            # Fallback to RAG agent
            return await rag_agent(state)
        
        # Run the selected tool
        tool_info = mcp_tools[selected_tool]
        server_config = tool_info['server_config']
        
        try:
            result = await run_mcp_tool(
                command=server_config.get('command', ''),
                args=server_config.get('args', []),
                env=server_config.get('env', {}),
                tool_name=selected_tool,
                tool_args={"query": query}
            )
            
            # Process the result
            clean_result = extract_text_content(result)
            
            return {"messages": [{"role": "assistant", "content": clean_result}]}
            
        except Exception as tool_error:
            error_msg = f"Error running MCP tool '{selected_tool}': {str(tool_error)}"
            print(error_msg)
            # Fallback to RAG when MCP fails
            return await rag_agent(state)
        
    except Exception as e:
        error_msg = f"Error in MCP agent: {str(e)}"
        print(error_msg)
        # Fallback to RAG on any error
        return await rag_agent(state)

# --- Decision Node ---
def route_decision(state: AgentState):
    """
    Decide whether to use RAG or MCP
    """
    query = state['messages'][-1]['content']
    mcp_tools = state.get('mcp_tools', {})
    
    # If no MCP configured - always go to RAG
    if not mcp_tools:
        return "rag_agent"
    
    # Simple routing logic - if there are external data keywords, use MCP
    external_keywords = ["weather", "time", "api", "external", "current", "today", "now"]
    query_lower = query.lower()
    
    if any(keyword in query_lower for keyword in external_keywords):
        return "mcp_agent"
    else:
        return "rag_agent"

# --- Build the graph ---
workflow = StateGraph(AgentState)

# Add the nodes
workflow.add_node("rag_agent", rag_agent)
workflow.add_node("mcp_agent", mcp_agent)

# Starting point
workflow.set_conditional_entry_point(
    route_decision,
    {
        "rag_agent": "rag_agent",
        "mcp_agent": "mcp_agent"
    }
)

# End
workflow.add_edge("rag_agent", END)
workflow.add_edge("mcp_agent", END)

# Compile
graph = workflow.compile()
