from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Paper:
    source: str
    source_id: str
    title: str
    abstract: str
    url: str
    published_at: datetime | None = None
    citation_count: int = 0
    discussion_score: float = 0.0
    trend_score: float = 0.0
    code_score: float = 0.0
    venue_score: float = 0.0
    review_score: float = 0.0
    authors: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    source_trace: list[str] = field(default_factory=list)
    score: float = 0.0
    selected_reason: str = ""
    summary_cn: dict[str, str] = field(default_factory=dict)
    mindmap_cn: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_id": self.source_id,
            "title": self.title,
            "abstract": self.abstract,
            "url": self.url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "citation_count": self.citation_count,
            "discussion_score": self.discussion_score,
            "trend_score": self.trend_score,
            "code_score": self.code_score,
            "venue_score": self.venue_score,
            "review_score": self.review_score,
            "authors": self.authors,
            "tags": self.tags,
            "source_trace": self.source_trace,
            "score": self.score,
            "selected_reason": self.selected_reason,
            "summary_cn": self.summary_cn,
            "mindmap_cn": self.mindmap_cn,
        }
