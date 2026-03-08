from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_answer(question: str, context: str) -> str:
    # System instruction with a focus on document awareness and human-like personality
    system_instruction = """You are a professional yet friendly and human-like AI assistant. 
    You have access to a knowledge base (RAG) containing the user's uploaded files.

    Your core goals:
    1. GENERAL CONVERSATION: Respond warmly to greetings and general questions. Use your general knowledge for non-document-related queries.
    2. FILE AWARENESS: If the user asks about their CV, documents, or personal info (like 'Who is Assaf Azran?'), use the provided context to answer. Acknowledge that you can 'see' or 'read' these details in the files.
    3. SMART INFERENCE: If the context contains information about 'Assaf Azran', treat inquiries about him with high relevance as he is the likely owner/subject of the documents.
    4. TRANSPARENCY: If a specific detail is missing from both the context and your knowledge, honestly tell the user, but try to be as helpful as possible with what you DO have.
    5. PERSONALITY: Be concise but warm. Avoid overly robotic phrases like 'Based on the provided context'. Instead, use more natural phrasing like 'From what I can see in your files' or 'According to your CV'.

    Always wrap up your response with a helpful or encouraging closing statement when appropriate."""

    user_prompt = f"""Context from files:
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