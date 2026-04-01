from __future__ import annotations

import json
from datetime import date

from tenacity import retry, stop_after_attempt, wait_fixed

from app.collectors.arxiv import ArxivCollector
from app.collectors.huggingface import HuggingFacePapersCollector
from app.collectors.semantic_scholar import SemanticScholarCollector
from app.config import settings
from app.models.paper import Paper
from app.services.database import PaperDB
from app.services.mindmap import build_paper_mindmap_tree, export_mindmap_json, export_xmind, slugify_filename
from app.services.scoring import PaperScorer
from app.services.summarizer import PaperSummarizer


class DailyPipeline:
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

        all_papers: list[Paper] = []
        for c in collectors:
            try:
                papers = c.collect()
                self.logger.info("collector=%s fetched=%s", c.name, len(papers))
                all_papers.extend(papers)
            except Exception as exc:
                self.logger.warning("collector=%s failed: %s", c.name, exc)
        return all_papers

    @staticmethod
    def _dedupe(papers: list[Paper]) -> list[Paper]:
        seen: set[str] = set()
        results: list[Paper] = []
        for p in papers:
            key = (p.title or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            results.append(p)
        return results

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
