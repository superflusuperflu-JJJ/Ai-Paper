from __future__ import annotations

import requests

from app.collectors.base import Collector
from app.models.paper import Paper


class OpenReviewCollector(Collector):
    name = "openreview"
    urls = [
        "https://openreview.net/group?id=ICLR.cc/2026/Conference",
        "https://openreview.net/group?id=NeurIPS.cc/2025/Conference",
    ]

    def collect(self) -> list[Paper]:
        # OpenReview frequently blocks anonymous scraping/API access in some environments.
        # Keep the collector as optional support so it can be enabled where reachable.
        headers = {"User-Agent": "ai-paper-daily/1.0 (+local)"}
        for url in self.urls:
            resp = requests.get(url, timeout=20, headers=headers)
            if resp.status_code == 200 and "OpenReview" in resp.text:
                return []
        raise RuntimeError("OpenReview is not reachable from the current environment")
