from typing import Any

import ollama


def generation(messages: list[dict[str, str]], model: str = "llama3.2") -> str:
    response: Any = ollama.chat(model=model, messages=messages)
    return response["message"]["content"]