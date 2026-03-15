import json
from typing import TypedDict, Annotated, Sequence, Dict, Any
import operator
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from ..services.mcp_service import run_mcp_tool
from ..services.retrieval_service import retrieve
from ..services.embedding_service import embed_texts
from ..services.llm_service import generate_answer

class AgentState(TypedDict):
    messages: Annotated[Sequence[dict], operator.add]
    mcp_config: dict  # הגדרות ה-MCP
    mcp_tools: Dict[str, Any]  # כל הכלים שנמצאו {name: {description, schema, server_config}}

llm = ChatOpenAI(model="gpt-4o")


def extract_text_content(result) -> str:
    """
    מחלץ טקסט נקי מתוצאת MCP.
    מטפל ב-TextContent, list של TextContent, או string רגיל.
    """
    # אם זה list (כמו בתמונה שהראית)
    if isinstance(result, list):
        texts = []
        for item in result:
            if hasattr(item, 'text'):
                texts.append(item.text)
            elif isinstance(item, str):
                texts.append(item)
        return "\n".join(texts) if texts else str(result)
    
    # אם זה TextContent אובייקט
    if hasattr(result, 'text'):
        return result.text
    
    # אם זה string
    if isinstance(result, str):
        return result
    
    # ברירת מחדל
    return str(result)

# --- צומת RAG (הסוכן הישן) ---
async def rag_agent(state: AgentState):
    query = state['messages'][-1]['content']
    
    try:
        # Generate query embedding
        query_vectors = embed_texts([query])
        query_vector = query_vectors[0]
        
        # Retrieve relevant context with metadata
        hits = retrieve(query_vector, top_k=5)
        
        # Build context with citations
        context_parts = []
        sources = set()
        for hit in hits:
            text = hit["text"]
            source = hit["source"]
            context_parts.append(f"Content: {text}\nSource: {source}")
            sources.add(source)
            
        context = "\n---\n".join(context_parts) if hits else "No relevant context found in uploaded documents."
        
        # Create answer
        response_text = generate_answer(query, context)
        
        # Append source info to response if available
        if sources:
            source_list = ", ".join(list(sources))
            response_text += f"\n\nSources: {source_list}"
        
        return {"messages": [{"role": "assistant", "content": response_text}]}
        
    except Exception as e:
        return {"messages": [{"role": "assistant", "content": f"Sorry, I encountered an error while searching your documents: {str(e)}"}]}

# --- צומת MCP (הסוכן החדש) ---
async def mcp_agent(state: AgentState):
    mcp_tools = state.get('mcp_tools', {})
    query = state['messages'][-1]['content']
    
    # בדיקה אם יש כלים זמינים
    if not mcp_tools:
        return {"messages": [{"role": "assistant", "content": "No MCP tools configured. Please configure MCP first in the MCP Settings page."}]}

    try:
        # הסוכן בוחר איזה כלי להשתמש מתוך הרשימה
        available_tools = list(mcp_tools.keys())
        
        # יצירת תיאור של הכלים לפרומפט
        tools_description = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in mcp_tools.items()
        ])
        
        # שאלת ה-LLM איזה כלי מתאים
        tool_selection_prompt = f"""You have these MCP tools available:
{tools_description}

User question: "{query}"

Which tool should you use to answer this question? 
Respond ONLY with the tool name (one word), or say "none" if none of these tools are relevant.

Tool name:"""

        selection_response = await llm.ainvoke(tool_selection_prompt)
        selected_tool = selection_response.content.strip().lower()
        
        # אם אף כלי לא מתאים - חזור ל-RAG
        if selected_tool == "none" or selected_tool not in mcp_tools:
            # Fallback to RAG agent
            return await rag_agent(state)
        
        # הרצת הכלי שנבחר
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
            
            # עיבוד התוצאה
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

# --- צומת החלטה ---
async def route_decision(state: AgentState):
    """
    מחליט האם להשתמש ב-RAG או ב-MCP
    """
    query = state['messages'][-1]['content']
    mcp_tools = state.get('mcp_tools', {})
    
    # אם אין MCP מוגדר - תמיד לך ל-RAG
    if not mcp_tools:
        return "rag_agent"
    
    # שאל את ה-LLM איך לנתב
    routing_prompt = f"""You are a routing assistant. Based on the user query, decide which agent to use:

User query: "{query}"

Available MCP tools: {', '.join(mcp_tools.keys()) if mcp_tools else 'None'}

If the query is about external data (weather, time, external APIs) and MCP tools are available, respond with: MCP
If the query is about the user's uploaded documents or general knowledge, respond with: RAG

Respond with ONLY one word: MCP or RAG"""

    try:
        decision = await llm.ainvoke(routing_prompt)
        choice = decision.content.strip().upper()
        
        if "MCP" in choice and mcp_tools:
            return "mcp_agent"
        else:
            return "rag_agent"
    except Exception as e:
        print(f"Routing error: {e}")
        return "rag_agent"  # ברירת מחדל

# --- בניית הגרף ---
workflow = StateGraph(AgentState)

# הוספת הצמתים
workflow.add_node("rag_agent", rag_agent)
workflow.add_node("mcp_agent", mcp_agent)

# נקודת ההתחלה
workflow.set_conditional_entry_point(
    route_decision,
    {
        "rag_agent": "rag_agent",
        "mcp_agent": "mcp_agent"
    }
)

# סיום
workflow.add_edge("rag_agent", END)
workflow.add_edge("mcp_agent", END)

# קומפילציה
graph = workflow.compile()
