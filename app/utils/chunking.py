from typing import List


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if chunk_size <= 0:
        return [text]
    tokens = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        tokens.append(text[start:end])
        start = end - overlap if end < text_len else end
    return tokens
