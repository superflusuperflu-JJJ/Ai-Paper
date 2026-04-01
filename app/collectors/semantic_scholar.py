from __future__ import annotations

import time

import requests

from app.collectors.base import Collector
from app.config import settings
from app.models.paper import Paper


class SemanticScholarCollector(Collector):
    name = "semantic_scholar"
    api_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    def collect(self) -> list[Paper]:
        params = {
            "query": "artificial intelligence OR machine learning",
            "limit": 50,
            "fields": "paperId,title,abstract,url,year,citationCount,authors,publicationDate",
            "sort": "citationCount:desc",
        }
        headers = {"User-Agent": "ai-paper-daily/1.0 (+local)"}
        if settings.semantic_scholar_api_key:
            headers["x-api-key"] = settings.semantic_scholar_api_key

        resp = None
        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                resp = requests.get(self.api_url, params=params, headers=headers, timeout=30)
                if resp.status_code == 429:
                    if attempt < 3:
                        wait_s = min(30, 2 ** (attempt + 1))
                        time.sleep(wait_s)
                        continue
                    resp.raise_for_status()
                resp.raise_for_status()
                break
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < 3:
                    time.sleep(2 ** (attempt + 1))
        if resp is None:
            raise RuntimeError(f"Semantic Scholar fetch failed after retries: {last_exc}")
        data = resp.json().get("data", [])

        papers: list[Paper] = []
        for item in data:
            title = (item.get("title") or "").strip()
            if not title:
                continue
            citation = int(item.get("citationCount") or 0)
            papers.append(
                Paper(
                    source=self.name,
                    source_id=item.get("paperId") or title,
                    title=title,
                    abstract=(item.get("abstract") or "").strip(),
                    url=item.get("url") or "",
                    citation_count=citation,
                    discussion_score=min(1.0, citation / 2000),
                    trend_score=0.55,
                    authors=[a.get("name") for a in item.get("authors", []) if a.get("name")],
                    tags=[],
                )
            )
        return papers
