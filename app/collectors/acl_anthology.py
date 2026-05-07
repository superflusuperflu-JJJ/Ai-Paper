from __future__ import annotations

import re
from datetime import datetime
from html import unescape

import requests

from app.collectors.base import Collector
from app.models.paper import Paper


class ACLAnthologyCollector(Collector):
    name = "acl_anthology"
    event_urls = [
        "https://aclanthology.org/events/acl-2025/",
        "https://aclanthology.org/events/emnlp-2024/",
        "https://aclanthology.org/events/naacl-2025/",
    ]

    def collect(self) -> list[Paper]:
        papers: list[Paper] = []
        for url in self.event_urls:
            try:
                papers.extend(self._collect_event(url))
            except Exception:
                continue
        return papers

    def _collect_event(self, url: str) -> list[Paper]:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "ai-paper-daily/1.0 (+local)"})
        resp.raise_for_status()
        html = resp.text

        blocks = re.findall(
            r'<div class="d-sm-flex align-items-stretch mb-3">(.*?)</span></div><div class="card bg-light mb-2 mb-lg-3 collapse abstract-collapse".*?<div class="card-body p-3 small">(.*?)</div></div>',
            html,
            re.DOTALL,
        )
        event_slug = url.rstrip("/").split("/")[-1]
        venue_score = 0.9 if event_slug.startswith(("acl-", "emnlp-", "naacl-")) else 0.75
        review_score = 0.8 if event_slug.startswith(("acl-", "emnlp-", "naacl-")) else 0.65

        results: list[Paper] = []
        for meta_html, abstract_html in blocks[:80]:
            title_match = re.search(r'<strong><a class=align-middle href=([^ >]+)>(.*?)</a></strong>', meta_html, re.DOTALL)
            if not title_match:
                continue
            rel_url = title_match.group(1).strip('"')
            title = self._clean(title_match.group(2))
            if not title:
                continue

            pdf_match = re.search(r'href=(https://aclanthology\.org/[^ >]+\.pdf)', meta_html)
            authors = [self._clean(a) for a in re.findall(r'>([^<>]+)</a>', meta_html)]
            authors = [a for a in authors if a and a != title]
            abstract = self._clean(abstract_html)
            code_score = 0.25 if re.search(r"\bcode\b|\bgithub\b|\bopenly released\b", abstract, re.IGNORECASE) else 0.05
            trend_score = 0.55 if re.search(r"\bllm\b|\blarge language model\b|\bmulti", abstract, re.IGNORECASE) else 0.4
            discussion_score = 0.35

            results.append(
                Paper(
                    source=self.name,
                    source_id=rel_url.strip("/"),
                    title=title,
                    abstract=abstract,
                    url=pdf_match.group(1) if pdf_match else f"https://aclanthology.org{rel_url}",
                    published_at=datetime(2025, 1, 1),
                    citation_count=0,
                    discussion_score=discussion_score,
                    trend_score=trend_score,
                    code_score=code_score,
                    venue_score=venue_score,
                    review_score=review_score,
                    authors=authors[:12],
                    tags=[event_slug.upper()],
                    source_trace=[self.name],
                )
            )
        return results

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text or "")
        text = unescape(text)
        return re.sub(r"\s+", " ", text).strip()
