import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    print("GROQ_API_KEY not set in environment.")
    raise SystemExit(1)

URL = "https://api.groq.com/openai/v1/chat/completions"

candidates = [
    "openai/gpt-oss-20b",
    "gpt-oss-20b",
    "groq/gpt-oss-20b",
    "qwen/qwen3.6-27b",
    "gpt-4o",
    "gpt-3.5-turbo",
    "gpt-4o-mini",
]

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

for model in candidates:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hello from test. State your model name."}],
        "max_tokens": 20,
    }
    try:
        r = requests.post(URL, headers=headers, json=payload, timeout=10)
    except Exception as e:
        print(f"{model}: request error: {e}")
        continue
    if r.status_code == 200:
        try:
            data = r.json()
            print(f"{model}: OK — response keys: {list(data.keys())}")
            # print a short content if available
            choice = data.get("choices")
            if choice:
                msg = choice[0].get("message", {}).get("content")
                print("  sample:", msg)
            break
        except Exception as e:
            print(f"{model}: OK but json parse failed: {e}")
            break
    else:
        print(f"{model}: HTTP {r.status_code} — {r.text}")
