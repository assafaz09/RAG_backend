from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def generate_answer(question: str, context: str) -> str:
    prompt = f"""You are a helpful assistant. Use the following context to answer the user's question.
    If the answer is not in the context, say that you don't know based on the uploaded files.
    Use the context to answer the question.
    If the question is not related to the context, say that you don't know.
    If the question is not clear, ask the user to clarify.
    If the question is not related to the context, say that you don't know.
    Context:
    {context}

    Question: {question}
    Answer:"""

    # כאן הייתה הבעיה - הסרתי את הרווח המיותר בתחילת השורה
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
    )
    return resp.choices[0].message.content.strip()