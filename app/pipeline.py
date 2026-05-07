from __future__ import annotations

import json
from datetime import date

from tenacity import retry, stop_after_attempt, wait_fixed

from app.collectors.arxiv import ArxivCollector
from app.collectors.acl_anthology import ACLAnthologyCollector
from app.collectors.huggingface import HuggingFacePapersCollector
from app.collectors.openreview import OpenReviewCollector
from app.collectors.paperswithcode import PapersWithCodeCollector
from app.collectors.semantic_scholar import SemanticScholarCollector
from app.config import settings
from app.models.paper import Paper
from app.services.database import PaperDB
from app.services.mindmap import build_paper_mindmap_tree, export_mindmap_json, export_xmind, slugify_filename
from app.services.scoring import PaperScorer
from app.services.summarizer import PaperSummarizer


class DailyPipeline:
    source_priority = {
        "semantic_scholar": 5,
        "acl_anthology": 4,
        "paperswithcode": 3,
        "huggingface": 2,
        "openreview": 2,
        "arxiv": 1,
    }

    def __init__(self, logger) -> None:
        self.logger = logger
        self.db = PaperDB(settings.db_path, settings.database_url)
        self.scorer = PaperScorer()
        self.summarizer = PaperSummarizer()

    def _collect_all(self) -> list[Paper]:
        collectors = []
        if settings.enable_arxiv:
            collectors.append(ArxivCollector())
        if settings.enable_semantic_scholar:
            collectors.append(SemanticScholarCollector())
        if settings.enable_huggingface:
            collectors.append(HuggingFacePapersCollector())
        if settings.enable_paperswithcode:
            collectors.append(PapersWithCodeCollector())
        if settings.enable_acl:
            collectors.append(ACLAnthologyCollector())
        if settings.enable_openreview:
            collectors.append(OpenReviewCollector())

        all_papers: list[Paper] = []
        for c in collectors:
            try:
                papers = c.collect()
                self.logger.info("collector=%s fetched=%s", c.name, len(papers))
                all_papers.extend(papers)
            except Exception as exc:
                self.logger.warning("collector=%s failed: %s", c.name, exc)
        return all_papers

    def _dedupe(self, papers: list[Paper]) -> list[Paper]:
        merged: dict[str, Paper] = {}
        for p in papers:
            key = (p.title or "").strip().lower()
            if not key:
                continue
            if key not in merged:
                merged[key] = p
                continue
            merged[key] = self._merge_paper(merged[key], p)
        return list(merged.values())

    def _merge_paper(self, base: Paper, incoming: Paper) -> Paper:
        if self.source_priority.get(incoming.source, 0) > self.source_priority.get(base.source, 0):
            base.source = incoming.source
            base.source_id = incoming.source_id
            if incoming.url:
                base.url = incoming.url
        if incoming.abstract and len(incoming.abstract) > len(base.abstract):
            base.abstract = incoming.abstract
        if incoming.url and not base.url:
            base.url = incoming.url
        if incoming.published_at and (base.published_at is None or incoming.published_at > base.published_at):
            base.published_at = incoming.published_at

        base.citation_count = max(base.citation_count, incoming.citation_count)
        base.discussion_score = max(base.discussion_score, incoming.discussion_score)
        base.trend_score = max(base.trend_score, incoming.trend_score)
        base.code_score = max(base.code_score, incoming.code_score)
        base.venue_score = max(base.venue_score, incoming.venue_score)
        base.review_score = max(base.review_score, incoming.review_score)
        base.authors = list(dict.fromkeys(base.authors + incoming.authors))
        base.tags = list(dict.fromkeys(base.tags + incoming.tags))
        base.source_trace = list(dict.fromkeys((base.source_trace or [base.source]) + (incoming.source_trace or [incoming.source])))
        return base

    def _dedupe_recent(self, papers: list[Paper]) -> list[Paper]:
        recent_titles = self.db.get_recent_titles(settings.dedupe_days)
        if not recent_titles:
            return papers
        results: list[Paper] = []
        for p in papers:
            key = (p.title or "").strip().lower()
            if not key or key in recent_titles:
                continue
            results.append(p)
        return results

    @retry(wait=wait_fixed(5), stop=stop_after_attempt(2), reraise=True)
    def run_once(self) -> dict:
        run_date = date.today()
        all_papers = self._dedupe(self._collect_all())
        all_papers = self._dedupe_recent(all_papers)

        for p in all_papers:
            p.score = self.scorer.score(p)
            p.selected_reason = self.scorer.reason(p)

        selected = [p for p in sorted(all_papers, key=lambda x: x.score, reverse=True) if p.score >= settings.min_score]
        selected = selected[: settings.daily_limit]

        for p in selected:
            p.summary_cn, p.mindmap_cn = self.summarizer.summarize_and_mindmap(p)

        self.db.upsert_daily(run_date, selected)

        month_dir = run_date.strftime("%Y-%m")
        day_dir = run_date.isoformat()
        output_path = settings.output_dir / month_dir / f"{day_dir}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        selected_dicts = [p.to_dict() for p in selected]
        output_path.write_text(json.dumps(selected_dicts, ensure_ascii=False, indent=2), encoding="utf-8")

        day_json_dir = settings.output_dir / month_dir / day_dir / "mindmaps"
        day_xmind_dir = settings.xmind_dir / month_dir / day_dir
        day_json_dir.mkdir(parents=True, exist_ok=True)
        day_xmind_dir.mkdir(parents=True, exist_ok=True)

        mindmaps: list[dict] = []
        for idx, paper in enumerate(selected_dicts, start=1):
            tree = build_paper_mindmap_tree(run_date.isoformat(), paper)
            stem = f"{idx:02d}-{slugify_filename(paper.get('title', 'paper'))}"
            map_json_path = day_json_dir / f"{stem}.json"
            xmind_path = day_xmind_dir / f"{stem}.xmind"
            export_mindmap_json(map_json_path, tree)
            export_xmind(xmind_path, tree)
            mindmaps.append({"paper_title": paper.get("title", ""), "json": str(map_json_path), "xmind": str(xmind_path)})

        return {
            "run_date": run_date.isoformat(),
            "count": len(selected),
            "json": str(output_path),
            "mindmaps": mindmaps,
        }
