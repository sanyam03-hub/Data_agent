import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MODELS = {
    "low": "openai/gpt-oss-20b",
    "medium": "qwen/qwen3.6-27b",
    "high": "openai/gpt-oss-120b",
}


def pick_llm(model_level: str) -> ChatOpenAI:
    """Return a Groq-backed chat model for the requested capability tier."""
    try:
        model = MODELS[model_level.lower()]
    except KeyError as error:
        raise ValueError("Invalid model level. Choose from 'low', 'medium', or 'high'.") from error

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured. Add it to your .env file.")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=GROQ_BASE_URL,
        temperature=0,
    )
