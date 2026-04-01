from __future__ import annotations

from datetime import datetime, timezone

from app.models.paper import Paper


class PaperScorer:
    def score(self, paper: Paper) -> float:
        citation_norm = min(1.0, paper.citation_count / 1000)
        discussion_norm = min(1.0, paper.discussion_score)
        trend_norm = min(1.0, paper.trend_score)

        recency_bonus = 0.0
        if paper.published_at:
            now = datetime.now(timezone.utc)
            age_days = max(0, (now - paper.published_at.astimezone(timezone.utc)).days)
            recency_bonus = max(0.0, 1.0 - age_days / 30.0)

        score = 0.40 * citation_norm + 0.30 * discussion_norm + 0.25 * trend_norm + 0.05 * recency_bonus
        return round(score, 4)

    def reason(self, paper: Paper) -> str:
        return (
            f"综合评分={paper.score}；引用={paper.citation_count}；"
            f"讨论热度={round(paper.discussion_score, 3)}；趋势热度={round(paper.trend_score, 3)}"
        )
