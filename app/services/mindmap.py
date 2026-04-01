from __future__ import annotations

import json
from pathlib import Path
import re

try:
    import xmind  # type: ignore
except Exception:  # pragma: no cover
    xmind = None


def slugify_filename(text: str, max_len: int = 64) -> str:
    cleaned = re.sub(r"[^\w\-\u4e00-\u9fff]+", "-", text.strip().lower())
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    if not cleaned:
        cleaned = "paper"
    return cleaned[:max_len]


def build_paper_mindmap_tree(run_date: str, paper: dict) -> dict:
    mindmap = paper.get("mindmap_cn", {}) or {}
    summary = paper.get("summary_cn", {}) or {}
    core = mindmap.get("research_core") or summary.get("problem", "")
    theory = mindmap.get("theoretical_basis") or "论文通过理论分析或已有范式支撑方法设计。"
    method = mindmap.get("method") or summary.get("method", "")
    experiments = mindmap.get("experiments") or summary.get("effectiveness", "")
    conclusion = mindmap.get("conclusion") or summary.get("one_liner", "")
    return {
        "name": f"{paper.get('title', 'Untitled')}（{run_date}）",
        "children": [
            {"name": f"研究核心：{core}"},
            {"name": f"理论基础：{theory}"},
            {"name": f"方法：{method}"},
            {"name": f"实验成果：{experiments}"},
            {"name": f"结论：{conclusion}"},
        ],
    }


def export_mindmap_json(path: Path, tree: dict) -> None:
    path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")


def export_xmind(path: Path, tree: dict) -> None:
    if xmind is None:
        return

    workbook = xmind.load(str(path))
    sheet = workbook.getPrimarySheet()
    sheet.setTitle("AI Paper Daily")
    root_topic = sheet.getRootTopic()
    root_topic.setTitle(tree.get("name", "AI论文日报"))

    for p in tree.get("children", []):
        topic = root_topic.addSubTopic()
        topic.setTitle(p.get("name", "Untitled"))
        for d in p.get("children", []):
            sub = topic.addSubTopic()
            sub.setTitle(d.get("name", ""))

    xmind.save(workbook, str(path))
