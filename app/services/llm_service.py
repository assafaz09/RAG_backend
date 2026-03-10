from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_answer(question: str, context: str) -> str:
    # Update the System instruction with emphasis on visual capabilities (Multimodal Awareness)
   # בתוך generate_answer
    mcp_info = f"You have an active MCP connection to: {mcp_name}." if mcp_name != 'none' else ""

    system_instruction = f"""{original_instruction}
    {mcp_info}
    If the user asks about this MCP or needs real-time data from it, guide the conversation or answer that you can access it.

    If a user asks for something that isn't in your files but sounds like it requires an external tool (such as 'search the web' or 'check Upstash'), begin your response with the word: 'External'.
    Your core goals:
    1. GENERAL CONVERSATION: Respond warmly to greetings and general questions.
    2. FILE AWARENESS: You can 'see' and 'read' both PDFs and images. When the context starts with 'Image Content (filename):', treat it as a visual description of an image you are looking at.
    3. MULTIMODAL INTEGRATION: If a user asks about a visual detail (e.g., 'What does the chart show?' or 'What is in the photo?'), refer to the image descriptions in the context naturally.
    4. SMART INFERENCE: Inquiries about 'Assaf Azran' should be treated with high relevance, as he is the primary subject of the knowledge base.
    5. TRANSPARENCY: If information is missing, be honest. If you are describing an image, you can say 'In the image you uploaded, I can see...' 
    6. PERSONALITY: Be concise but warm. Use natural phrasing like 'Looking at your files' or 'From the documents and images you provided'. Avoid robotic jargon.

    Always wrap up your response with a helpful or encouraging closing statement when appropriate."""

    user_prompt = f"""Context from files (including text and image descriptions):
    ---
    {context}
    ---

    User Question: {question}
    Answer:"""

    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=512,
        temperature=0.7,
    )
    
    return resp.choices[0].message.content.strip()