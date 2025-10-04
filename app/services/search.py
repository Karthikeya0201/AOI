from dataclasses import dataclass
from typing import List, Optional
import re
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib.parse import quote_plus

@dataclass
class SearchResult:
    url: str
    title: str
    score: float

SEARCH_ENGINES = [
    "https://duckduckgo.com/html/?q={query}",
    "https://www.google.com/search?q={query}",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ICMarkingVerifier/0.1)"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def _score_url(url: str, title: str, part_number: str) -> float:
    score = 0.0
    pn = part_number.lower()
    text = f"{url} {title}".lower()
    if pn in text:
        score += 2.0
    for token in ["marking", "package marking", "top marking", "laser marking"]:
        if token in text:
            score += 1.5
    for token in ["datasheet", "data sheet", "product specification", "product brief"]:
        if token in text:
            score += 1.0
    for oem_hint in [".com", ".co", ".cn", ".eu"]:
        if pn.split()[0] in url and url.endswith(oem_hint):
            score += 0.5
    return score


async def find_marking_documents(part_number: str, preferred_url: Optional[str]) -> List[SearchResult]:
    if preferred_url:
        return [SearchResult(url=preferred_url, title="Preferred", score=10.0)]

    query_string = quote_plus(f"{part_number} marking datasheet")
    results: List[SearchResult] = []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for engine in SEARCH_ENGINES:
            url = engine.format(query=query_string)
            try:
                html = await _fetch_text(client, url)
            except Exception:
                continue

            # naive link scraping
            for href, title in re.findall(r'<a[^>]+href="(http[^"]+)"[^>]*>(.*?)</a>', html, flags=re.I|re.S):
                clean_title = re.sub('<[^<]+?>', '', title)
                if any(bad in href for bad in ["duckduckgo.com/y.js", "/d.js", "googleusercontent", "/preferences"]) or len(clean_title) < 3:
                    continue
                score = _score_url(href, clean_title, part_number)
                if score > 1.0:
                    results.append(SearchResult(url=href, title=clean_title[:120], score=score))

    # de-duplicate by url keeping best score
    dedup = {}
    for r in results:
        if r.url not in dedup or dedup[r.url].score < r.score:
            dedup[r.url] = r

    ranked = sorted(dedup.values(), key=lambda r: r.score, reverse=True)
    return ranked[:10]
