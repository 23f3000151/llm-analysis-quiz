import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def llm_solve(prompt: str, model="gpt-4o-mini", max_tokens=800):
    """
    Async wrapper around the new OpenAI client (v1.x)
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def call():
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Respond ONLY with JSON. No explanation."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0
        )
        return response.choices[0].message.content

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, call)


def strict_json_parse(text: str):
    """
    Extracts first JSON object from text.
    """
    text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON found in LLM output")

    json_str = text[start:end+1]
    return json.loads(json_str)
