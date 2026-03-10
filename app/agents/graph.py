from typing import TypedDict, Annotated, Sequence
import operator
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from ..services.mcp_service import run_mcp_tool

class AgentState(TypedDict):
    messages: Annotated[Sequence[dict], operator.add]
    mcp_config: dict  # כאן נשמור את ה-JSON של ה-MCP שהמשתמש העלה

llm = ChatOpenAI(model="gpt-4o")

# --- צומת RAG (הסוכן הישן) ---
async def rag_agent(state: AgentState):
    query = state['messages'][-1]['content']
    # כאן תקרא לפונקציית החיפוש ב-Qdrant (עם ה-Chunks)
    context = "Information from Qdrant..." 
    response = llm.invoke(f"Base on this context: {context}. Question: {query}")
    return {"messages": [{"role": "assistant", "content": response.content}]}

# --- צומת MCP (הסוכן החדש) ---
async def mcp_agent(state: AgentState):
    config = state.get['mcp_config', {}]
    query = state['messages'][-1]['content']
    
    # הסוכן מחליט באיזה כלי להשתמש מתוך ה-MCP
    # לצורך הפשטות, אנחנו מריצים כלי חיפוש דיפולטיבי מהקונפיג
    result = await run_mcp_tool(
        command=config['command'],
        args=config['args'],
        env=config.get('env'),
        tool_name=config['main_tool'],
        tool_args={"query": query}
    )
    return {"messages": [{"role": "assistant", "content": f"External Info: {result}"}]}

# --- הנתב (The Router) ---
# בתוך graph.py - נגדיר פונקציה חדשה שתעזור לנתב
def route_decision(state: AgentState):
    user_input = state['messages'][-1]['content'].lower()
    mcp_config = state.get('mcp_config', {})
    mcp_name = mcp_config.get('name', 'none')
    
    # ניצור פרומפט קצר שמסביר למודל את האפשרויות
    router_prompt = f"""Analyze the user query: "{user_input}"
    We have two agents:
    1. rag_agent: For general questions or info in uploaded files.
    2. mcp_agent: Specifically for queries about {mcp_name} or real-time external data.
    
    Which agent is more suitable? Respond ONLY with 'mcp_agent' or 'rag_agent'."""
    
    # קריאה מהירה ל-LLM (אפשר להשתמש במודל זול יותר כמו GPT-4o-mini כאן)
    decision = llm.invoke(router_prompt).content.strip().lower()
    
    if "mcp_agent" in decision:
        return "mcp_agent"
    return "rag_agent"

# בניית הגרף
workflow = StateGraph(AgentState)
workflow.add_node("rag_agent", rag_agent)
workflow.add_node("mcp_agent", mcp_agent)

workflow.set_conditional_entry_point(
    route_decision,
    {"rag_agent": "rag_agent", "mcp_agent": "mcp_agent"}
)

workflow.add_edge("rag_agent", END)
workflow.add_edge("mcp_agent", END)

graph = workflow.compile()