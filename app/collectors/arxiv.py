from __future__ import annotations

from datetime import datetime
import time
from xml.etree import ElementTree

import requests

from app.collectors.base import Collector
from app.models.paper import Paper


class ArxivCollector(Collector):
    name = "arxiv"
    feed_url = "https://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL&sortBy=lastUpdatedDate&max_results=50"

    def collect(self) -> list[Paper]:
        headers = {"User-Agent": "ai-paper-daily/1.0 (+local)"}
        last_exc: Exception | None = None
        resp = None
        for attempt in range(3):
            try:
                resp = requests.get(self.feed_url, headers=headers, timeout=30)
                resp.raise_for_status()
                break
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        if resp is None:
            raise RuntimeError(f"arXiv fetch failed after retries: {last_exc}")
        root = ElementTree.fromstring(resp.text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        papers: list[Paper] = []
        for entry in root.findall("atom:entry", ns):
            pid = (entry.findtext("atom:id", default="", namespaces=ns) or "").split("/")[-1]
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip().replace("\n", " ")
            abstract = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip().replace("\n", " ")
            published_raw = entry.findtext("atom:published", default="", namespaces=ns)
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00")) if published_raw else None
            authors = [n.text.strip() for n in entry.findall("atom:author/atom:name", ns) if n.text]
            tags = [n.attrib.get("term", "") for n in entry.findall("atom:category", ns) if n.attrib.get("term")]

            papers.append(
                Paper(
                    source=self.name,
                    source_id=pid,
                    title=title,
                    abstract=abstract,
                    url=entry.findtext("atom:id", default="", namespaces=ns),
                    published_at=published_at,
                    citation_count=0,
                    discussion_score=0.25,
                    trend_score=0.45,
                    code_score=0.05 if "github" in abstract.lower() or "code" in abstract.lower() else 0.0,
                    venue_score=0.1,
                    review_score=0.0,
                    authors=authors,
                    tags=tags,
                    source_trace=[self.name],
                )
            )
        return papers
