from __future__ import annotations

from datetime import datetime

import requests

from app.collectors.base import Collector
from app.models.paper import Paper


class HuggingFacePapersCollector(Collector):
    name = "huggingface"
    # Public endpoint behind hf.co/papers; structure can change, so collector is tolerant.
    api_url = "https://huggingface.co/api/daily_papers"

    def collect(self) -> list[Paper]:
        resp = requests.get(self.api_url, timeout=20)
        resp.raise_for_status()
        payload = resp.json()

        items = payload if isinstance(payload, list) else payload.get("papers", [])
        papers: list[Paper] = []
        total = max(1, len(items))
        for idx, it in enumerate(items):
            pid = str(it.get("id") or it.get("paper", {}).get("id") or "")
            title = (it.get("title") or it.get("paper", {}).get("title") or "").strip()
            abstract = (it.get("summary") or it.get("paper", {}).get("summary") or "").strip()
            url = it.get("url") or it.get("paper", {}).get("url") or "https://huggingface.co/papers"
            published_raw = it.get("publishedAt") or it.get("published_at")
            published_at = None
            if published_raw:
                try:
                    published_at = datetime.fromisoformat(str(published_raw).replace("Z", "+00:00"))
                except ValueError:
                    published_at = None

            upvotes = float(it.get("upvotes") or it.get("votes") or 0)
            comments = float(it.get("comments") or 0)
            rank_boost = max(0.0, 1.0 - idx / total)
            discussion = min(1.0, upvotes * 0.03 + comments * 0.06)
            trend = min(1.0, 0.35 + upvotes * 0.01)
            # HF daily papers often has sparse numeric fields; apply rank fallback to keep outputs stable.
            discussion = max(discussion, 0.2 + rank_boost * 0.5)
            trend = max(trend, 0.3 + rank_boost * 0.5)
            code_score = 0.25 if "github" in abstract.lower() or "code" in abstract.lower() else 0.0
            papers.append(
                Paper(
                    source=self.name,
                    source_id=pid or title,
                    title=title,
                    abstract=abstract,
                    url=url,
                    published_at=published_at,
                    citation_count=0,
                    discussion_score=discussion,
                    trend_score=trend,
                    code_score=code_score,
                    venue_score=0.2,
                    review_score=0.1,
                    authors=it.get("authors") or [],
                    tags=it.get("tags") or [],
                    source_trace=[self.name],
                )
            )
        return [p for p in papers if p.title]
