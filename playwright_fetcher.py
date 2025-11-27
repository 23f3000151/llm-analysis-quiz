import httpx

async def fetch_page_text(url: str) -> str:
    print(f">>> DEBUG: Fetching (HTTPX only): {url}")

    async with httpx.AsyncClient(
       timeout=30,
       headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Safari/537.36"}
) as client:
       r = await client.get(url)
       print(">>> DEBUG: RAW HTML RECEIVED:\n", r.text[:1000], "\n------ END ------")
       return r.text

