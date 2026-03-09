import base64
from openai import OpenAI
import io

client = OpenAI() # Ensure API KEY is set in Environment Variables

async def process_image_for_rag(image_bytes: bytes, filename: str):
    """
    Convert image to text and save it in Qdrant as part of RAG.
    """
    # 1. Encode the image to Base64 for the API
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # 2. Get description from AI (using Vision)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in detail. If there is text, transcribe it. If it is a graph, explain the data."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
    )
    
    description = response.choices[0].message.content
    return {
        "text": f"Image Content ({filename}): {description}",
        "metadata": {"type": "image", "original_filename": filename}
    }