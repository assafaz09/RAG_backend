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
        # יצירת embedding לשאילתה
        query_vectors = embed_texts([query])
        query_vector = query_vectors[0]
        
        # שליפת מידע רלוונטי מ-Qdrant
        hits = retrieve(query_vector, top_k=5)
        
        # בניית קונטקסט
        context = "\n---\n".join(hits) if hits else "No relevant context found in uploaded documents."
        
        # יצירת תשובה מבוססת קונטקסט
        system_prompt = "You are a helpful assistant. Use the provided context from uploaded documents to answer the user's question. If the context doesn't contain relevant information, say so politely."
        user_prompt = f"Context from documents:\n{context}\n\nQuestion: {query}"
        
        response_text = generate_answer(system_prompt, user_prompt)
        
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

        tool_selection = llm.invoke(tool_selection_prompt).content.strip()
        
        # אם ה-LLM אמר שאף כלי לא מתאים
        if tool_selection.lower() in ["none", "", "rag"] or tool_selection not in mcp_tools:
            return {"messages": [{"role": "assistant", "content": "I don't have a suitable MCP tool for this question. Let me search in your documents instead."}]}
        
        selected_tool_name = tool_selection
        selected_tool = mcp_tools[selected_tool_name]
        
        # הכנת פרמטרים לכלי לפי ה-schema
        schema = selected_tool.get('schema', {})
        properties = schema.get('properties', {})
        
        if properties:
            # יש פרמטרים - נבקש מה-LLM להכין אותם
            params_prompt = f"""Extract parameters for tool "{selected_tool_name}" from the user question.

Tool schema: {json.dumps(schema, indent=2)}

User question: "{query}"

Extract the parameters as a JSON object that matches the schema. If a parameter is not mentioned, use a reasonable default or null.

JSON:"""
            
            params_response = llm.invoke(params_prompt).content.strip()
            
            # ניקוי התשובה מ-markdown אם יש
            if params_response.startswith("```json"):
                params_response = params_response[7:]
            if params_response.endswith("```"):
                params_response = params_response[:-3]
            params_response = params_response.strip()
            
            try:
                tool_args = json.loads(params_response)
            except json.JSONDecodeError:
                # אם ה-JSON לא תקין, נשתמש בפרמטר פשוט
                tool_args = {"query": query}
        else:
            # אין פרמטרים נדרשים
            tool_args = {}
        
        # הפעלת הכלי הספציפי
        server_config = selected_tool['server_config']
        result = await run_mcp_tool(
            command=server_config.get('command', ''),
            args=server_config.get('args', []),
            env=server_config.get('env', {}),
            tool_name=selected_tool_name,
            tool_args=tool_args
        )
        
        # 🔥 שיפור הפורמט - חילוץ טקסט נקי מהתוצאה
        clean_result = extract_text_content(result)
        
        # 🔥 יצירת תשובה יפה עם system prompt
        final_response = f"{clean_result}"
        
        return {"messages": [{"role": "assistant", "content": final_response}]}
        
    except Exception as e:
        return {"messages": [{"role": "assistant", "content": f"Error running MCP tool: {str(e)}. Please check your MCP configuration."}]}

# --- הנתב (The Router) ---
def route_decision(state: AgentState):
    user_input = state['messages'][-1]['content'].lower()
    mcp_tools = state.get('mcp_tools', {})
    mcp_config = state.get('mcp_config', {})
    
    # אם אין כלים זמינים, תמיד השתמש ב-RAG
    if not mcp_tools:
        return "rag_agent"
    
    # אם יש כלים, נבדוק אם השאלה רלוונטית לאחד מהם
    available_tool_names = list(mcp_tools.keys())
    mcp_name = mcp_config.get('name', 'External Tools')
    
    router_prompt = f"""Analyze the user query: "{user_input}"

You have these tools available:
1. rag_agent: For questions about uploaded documents and files.
2. mcp_agent: For using external tools like: {', '.join(available_tool_names)}

Which agent is more suitable for this question?
Respond ONLY with 'mcp_agent' or 'rag_agent'."""
    
    # קריאה מהירה ל-LLM
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