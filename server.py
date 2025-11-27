import os
import json
import asyncio
import secrets as py_secrets
from typing import Any, Dict
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from playwright_fetcher import fetch_page_text
from llm_client import llm_solve, strict_json_parse

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

STUDENT_SECRETS = {
    os.getenv("STUDENT_EMAIL", "student@example.com"): os.getenv("STUDENT_SECRET", "my-secret")
}

OVERALL_TIMEOUT = 180

app = FastAPI(title="LLM Analysis Quiz Solver")


class QuizRequest(BaseModel):
    email: str
    secret: str
    url: str


def verify_secret(email: str, provided: str) -> bool:
    expected = STUDENT_SECRETS.get(email)
    if expected is None:
        return False
    return py_secrets.compare_digest(expected, provided)


async def solve_quiz_flow(payload: QuizRequest) -> Dict[str, Any]:
    page_text = await fetch_page_text(payload.url)

    # Remove Playwright error check (no longer needed)

    # -------------------------
    # Extract submit URL (even if origin is inserted by JS)
    # -------------------------
    import re
    from urllib.parse import urlparse

    # 1) Try normal full submit URL
    submit_urls = re.findall(r"https?://[^\s\"']*submit[^\s\"']*", page_text, re.IGNORECASE)

    # 2) If not found, detect relative /submit
    if not submit_urls:
        if "/submit" in page_text:
            parsed = urlparse(payload.url)
            origin = f"{parsed.scheme}://{parsed.netloc}"
            submit_urls = [origin + "/submit"]

    submit_url = submit_urls[0] if submit_urls else None

    print(">>> DEBUG: Final submit URL:", submit_url)



    # Ask LLM
    prompt = f"""
You MUST output ONLY JSON with key "answer".

Page content:
\"\"\"{page_text[:4000]}\"\"\""""

    llm_response = await llm_solve(prompt)

    try:
        parsed = strict_json_parse(llm_response)
    except:
        parsed = {"answer": llm_response.strip()}

    result = {"llm_parsed": parsed}

    # Submit answer
    if submit_url:
        import httpx
        submission = {
            "email": payload.email,
            "secret": payload.secret,
            "url": payload.url,
            "answer": parsed["answer"]
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(submit_url, json=submission)
            try:
                resp_json = resp.json()
            except:
                resp_json = {"text": resp.text}

        result["submit"] = {"status": resp.status_code, "response": resp_json}
    else:
        result["submit"] = {"status": None, "response": "no submit url found"}

    return result


@app.post("/solve")
async def solve(request: Request):
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="invalid json")

    try:
        payload = QuizRequest(**body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid payload: {str(e)}")

    if not verify_secret(payload.email, payload.secret):
        raise HTTPException(status_code=403, detail="invalid secret")

    try:
        result = await asyncio.wait_for(
            solve_quiz_flow(payload),
            timeout=OVERALL_TIMEOUT - 5
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="solver timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "result": result}


@app.get("/")
def home():
    return {"status": "running", "message": "LLM Analysis Quiz Solver API"}
