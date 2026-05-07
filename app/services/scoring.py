from __future__ import annotations

from datetime import datetime, timezone

from app.models.paper import Paper


class PaperScorer:
    def score(self, paper: Paper) -> float:
        citation_norm = min(1.0, paper.citation_count / 1000)
        discussion_norm = min(1.0, paper.discussion_score)
        trend_norm = min(1.0, paper.trend_score)
        code_norm = min(1.0, paper.code_score)
        venue_norm = min(1.0, paper.venue_score)
        review_norm = min(1.0, paper.review_score)

        recency_bonus = 0.0
        if paper.published_at:
            now = datetime.now(timezone.utc)
            age_days = max(0, (now - paper.published_at.astimezone(timezone.utc)).days)
            recency_bonus = max(0.0, 1.0 - age_days / 30.0)

        score = (
            0.26 * citation_norm
            + 0.20 * discussion_norm
            + 0.18 * trend_norm
            + 0.08 * recency_bonus
            + 0.16 * code_norm
            + 0.08 * venue_norm
            + 0.04 * review_norm
        )
        return round(score, 4)

    def reason(self, paper: Paper) -> str:
        return (
            f"综合评分={paper.score}；引用={paper.citation_count}；"
            f"讨论热度={round(paper.discussion_score, 3)}；趋势热度={round(paper.trend_score, 3)}；"
            f"代码信号={round(paper.code_score, 3)}；会议信号={round(paper.venue_score, 3)}；"
            f"评审信号={round(paper.review_score, 3)}"
        )
