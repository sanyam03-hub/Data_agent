import os

from dotenv import load_dotenv

load_dotenv()

def pick_llm(level: str):
    """
    Select a Groq LLM based on the capability level.

    low    -> GPT-OSS 20B
    medium -> Qwen 3.6 27B
    high   -> GPT-OSS 120B
    """

    # Prefer OpenAI models by default. The caller can set `OPENAI_API_KEY` in env.
    MODELS = {
        "low": "gpt-3.5-turbo",
        "medium": "gpt-4o-mini",
        "high": "gpt-4o",
    }

    # Provider selection: 'openai' (default) or 'groq'
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "groq":
        GROQ_BASE_URL = "https://api.groq.com/openai/v1"
        groq_key = os.getenv("GROQ_API_KEY")
        groq_model = os.getenv("GROQ_MODEL")
        if not groq_key:
            raise EnvironmentError("LLM_PROVIDER=groq but GROQ_API_KEY is not set.")
        if not groq_model:
            raise EnvironmentError(
                "LLM_PROVIDER=groq but GROQ_MODEL is not set. Set GROQ_MODEL to a valid Groq model name."
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=groq_model, api_key=groq_key, base_url=GROQ_BASE_URL, temperature=0)

    api_key = os.getenv("OPENAI_API_KEY")

    if level.lower() not in MODELS:
        raise ValueError(f"Unsupported level: {level}")

    if not api_key:
        raise EnvironmentError(
            "No OPENAI_API_KEY found. Set OPENAI_API_KEY in your environment or set LLM_PROVIDER=groq with GROQ_API_KEY/GROQ_MODEL."
        )

    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(
        model=MODELS[level.lower()],
        api_key=api_key,
        temperature=0,
    )

    return llm


if __name__ == "__main__":
    # Pick the LLM
    llm_obj = pick_llm("low")

    # Test the LLM
    print(llm_obj.invoke("What is the capital of France?"))