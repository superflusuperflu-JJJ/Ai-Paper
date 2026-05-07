from __future__ import annotations

import json
import re
from datetime import datetime

import requests

from app.collectors.base import Collector
from app.models.paper import Paper


class PapersWithCodeCollector(Collector):
    name = "paperswithcode"
    # Papers with Code latest now redirects to Hugging Face trending papers.
    trending_url = "https://huggingface.co/papers/trending"

    def collect(self) -> list[Paper]:
        resp = requests.get(self.trending_url, timeout=30, headers={"User-Agent": "ai-paper-daily/1.0 (+local)"})
        resp.raise_for_status()
        html = resp.text
        match = re.search(r'"dailyPapers":(\[.*?\]),"currentType"', html, re.DOTALL)
        if not match:
            raise RuntimeError("paperswithcode collector failed to locate trending payload")

        items = json.loads(match.group(1))
        total = max(1, len(items))
        papers: list[Paper] = []
        for idx, item in enumerate(items):
            paper = item.get("paper") or {}
            title = (item.get("title") or paper.get("title") or "").strip()
            if not title:
                continue

            published_raw = item.get("publishedAt") or paper.get("publishedAt")
            published_at = None
            if published_raw:
                try:
                    published_at = datetime.fromisoformat(str(published_raw).replace("Z", "+00:00"))
                except ValueError:
                    published_at = None

            upvotes = float(paper.get("upvotes") or item.get("upvotes") or 0)
            stars = float(paper.get("githubStars") or 0)
            rank_boost = max(0.0, 1.0 - idx / total)
            discussion = max(min(1.0, 0.2 + upvotes * 0.05), 0.35 + rank_boost * 0.45)
            trend = max(min(1.0, 0.3 + upvotes * 0.03), 0.4 + rank_boost * 0.45)
            code_score = 0.0
            if paper.get("githubRepo"):
                code_score = min(1.0, 0.45 + stars / 5000.0)
            elif paper.get("projectPage"):
                code_score = 0.35

            tags = list(paper.get("ai_keywords") or item.get("ai_keywords") or [])
            authors = [a.get("name") for a in (paper.get("authors") or []) if a.get("name")]
            papers.append(
                Paper(
                    source=self.name,
                    source_id=str(paper.get("id") or item.get("id") or title),
                    title=title,
                    abstract=(item.get("summary") or paper.get("summary") or "").strip(),
                    url=f"https://huggingface.co/papers/{paper.get('id')}" if paper.get("id") else self.trending_url,
                    published_at=published_at,
                    citation_count=0,
                    discussion_score=discussion,
                    trend_score=trend,
                    code_score=code_score,
                    venue_score=0.25,
                    review_score=0.15,
                    authors=authors,
                    tags=tags,
                    source_trace=[self.name],
                )
            )
        return papers
