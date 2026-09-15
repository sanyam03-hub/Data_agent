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


def pick_llm(level: str):
    """
    Select a Groq LLM based on the capability level.

    low    -> GPT-OSS 20B
    medium -> Qwen 3.6 27B
    high   -> GPT-OSS 120B
    """

    if level.lower() == "low":
        llm = ChatOpenAI(
            model=MODELS["low"],
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=GROQ_BASE_URL,
            temperature=0,
        )

    elif level.lower() == "medium":
        llm = ChatOpenAI(
            model=MODELS["medium"],
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=GROQ_BASE_URL,
            temperature=0,
        )

    elif level.lower() == "high":
        llm = ChatOpenAI(
            model=MODELS["high"],
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=GROQ_BASE_URL,
            temperature=0,
        )

    else:
        raise ValueError(f"Unsupported level: {level}")

    return llm


# Pick the LLM
llm_obj = pick_llm("low")

# Test the LLM
print(llm_obj.invoke("What is the capital of France?"))