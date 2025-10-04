from typing import List, Dict
import re
import os
import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from pdfminer.high_level import extract_text
from loguru import logger

DATA_DIR = "data/downloads"
CACHE_DIR = "data/cache"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
async def _download_file(url: str, dest_path: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        r = await client.get(url, timeout=60)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)
    return dest_path


def _safe_filename(url: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", url)[:180]


async def fetch_and_extract_marking_sections(results: List) -> Dict[str, str]:
    sections: Dict[str, str] = {}

    for res in results[:5]:
        url = res.url
        filename = _safe_filename(url)
        download_path = os.path.join(DATA_DIR, filename)
        text_cache_path = os.path.join(CACHE_DIR, f"{filename}.txt")

        if os.path.exists(text_cache_path):
            with open(text_cache_path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            try:
                if any(url.lower().endswith(ext) for ext in [".pdf"]):
                    await _download_file(url, download_path)
                    text = extract_text(download_path)
                else:
                    # HTML page, try to extract textual content
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        resp = await client.get(url, timeout=30)
                        resp.raise_for_status()
                        soup = BeautifulSoup(resp.text, "lxml")
                        # Remove script/style
                        for tag in soup(["script", "style", "noscript"]):
                            tag.decompose()
                        text = soup.get_text(" ")
                with open(text_cache_path, "w", encoding="utf-8", errors="ignore") as f:
                    f.write(text)
            except Exception as e:
                logger.warning(f"Failed to retrieve {url}: {e}")
                continue

        # Find marking sections heuristically
        lower = text.lower()
        markers = [
            "marking", "top marking", "laser marking", "package marking",
            "ic marking", "device marking"
        ]
        best_idx = -1
        best_term = None
        for term in markers:
            idx = lower.find(term)
            if idx != -1 and (best_idx == -1 or idx < best_idx):
                best_idx = idx
                best_term = term

        if best_idx != -1:
            start = max(0, best_idx - 400)
            end = min(len(text), best_idx + 2000)
            snippet = text[start:end]
            sections[url] = snippet
        else:
            # fallback: capture around part number occurrences
            sections[url] = text[:2500]

    return sections
