from __future__ import annotations

import ast
import json
import logging
import re
from typing import Any

import requests

from app.config import settings
from app.models.paper import Paper


class PaperSummarizer:

    def summarize(self, paper: Paper) -> dict[str, str]:
        summary, _ = self.summarize_and_mindmap(paper)
        return summary

    def summarize_and_mindmap(self, paper: Paper) -> tuple[dict[str, str], dict[str, str]]:
        has_any_provider = False

        if settings.doubao_api_key and settings.doubao_model:
            has_any_provider = True
            try:
                return self._summarize_with_doubao(paper)
            except Exception:
                logging.getLogger("ai-paper-daily").warning("doubao summarize failed; fallback to gemini", exc_info=True)
        if settings.gemini_api_key:
            has_any_provider = True
            try:
                return self._summarize_with_gemini(paper)
            except Exception:
                logging.getLogger("ai-paper-daily").warning("gemini summarize failed; fallback to openai", exc_info=True)
        if settings.openai_api_key:
            has_any_provider = True
            try:
                return self._summarize_with_llm(paper)
            except Exception:
                logging.getLogger("ai-paper-daily").warning("openai summarize failed; fallback to template", exc_info=True)

        if not has_any_provider:
            raise RuntimeError("no LLM provider key found (DOUBAO/GEMINI/OPENAI)")

        raise RuntimeError("all LLM providers failed; refusing to use template fallback")

    def _summarize_with_llm(self, paper: Paper) -> tuple[dict[str, str], dict[str, str]]:
        prompt = (
            "请基于下面论文信息，输出中文 JSON，键必须是："
            "one_liner, background, problem, method, effectiveness, highlights, limitations, other_info, "
            "mindmap_core, mindmap_theory, mindmap_method, mindmap_experiments, mindmap_conclusion。"
            "每个字段 1-3 句话，内容要准确、克制、无夸大，不要编造实验数据。\n\n"
            f"标题：{paper.title}\n"
            f"摘要：{paper.abstract}\n"
            f"作者：{', '.join(paper.authors[:8])}\n"
            f"标签：{', '.join(paper.tags[:10])}\n"
        )
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        base_url = settings.openai_base_url or "https://api.openai.com/v1"
        payload: dict[str, Any] = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": "你是严谨的 AI 论文分析助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        resp = requests.post(f"{base_url}/chat/completions", json=payload, headers=headers, timeout=45)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        fallback = self._fallback_summary(paper)
        summary = {
            "one_liner": str(data.get("one_liner", "")).strip() or fallback["one_liner"],
            "background": str(data.get("background", "")).strip() or fallback["background"],
            "problem": str(data.get("problem", "")).strip() or fallback["problem"],
            "method": str(data.get("method", "")).strip() or fallback["method"],
            "effectiveness": str(data.get("effectiveness", "")).strip() or fallback["effectiveness"],
            "highlights": str(data.get("highlights", "")).strip() or fallback["highlights"],
            "limitations": str(data.get("limitations", "")).strip() or fallback["limitations"],
            "other_info": str(data.get("other_info", "")).strip() or fallback["other_info"],
        }
        fallback_map = self._fallback_mindmap(paper, summary)
        mindmap = {
            "research_core": str(data.get("mindmap_core", "")).strip() or fallback_map["research_core"],
            "theoretical_basis": str(data.get("mindmap_theory", "")).strip() or fallback_map["theoretical_basis"],
            "method": str(data.get("mindmap_method", "")).strip() or fallback_map["method"],
            "experiments": str(data.get("mindmap_experiments", "")).strip() or fallback_map["experiments"],
            "conclusion": str(data.get("mindmap_conclusion", "")).strip() or fallback_map["conclusion"],
        }
        return summary, mindmap

    def _summarize_with_doubao(self, paper: Paper) -> tuple[dict[str, str], dict[str, str]]:
        prompt = (
            "请基于下面论文信息，输出中文 JSON，键必须是："
            "one_liner, background, problem, method, effectiveness, highlights, limitations, other_info, "
            "mindmap_core, mindmap_theory, mindmap_method, mindmap_experiments, mindmap_conclusion。"
            "每个字段 1-3 句话，内容要准确、克制、无夸大，不要编造实验数据。"
            "只输出 JSON，不要 Markdown，不要额外说明。\n\n"
            f"标题：{paper.title}\n"
            f"摘要：{paper.abstract}\n"
            f"作者：{', '.join(paper.authors[:8])}\n"
            f"标签：{', '.join(paper.tags[:10])}\n"
        )
        base_url = settings.doubao_base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            base_url = base_url[: -len("/chat/completions")]
        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.doubao_api_key}",
        }
        payload: dict[str, Any] = {
            "model": settings.doubao_model,
            "messages": [
                {"role": "system", "content": "你是严谨的 AI 论文分析助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
        if resp.status_code >= 400:
            raise RuntimeError(f"Doubao request failed: {resp.status_code} {resp.text[:300]}")
        data = resp.json()
        text = ""
        try:
            text = data["choices"][0]["message"]["content"]
        except Exception:
            text = ""
        if not text:
            raise RuntimeError("Doubao empty response")
        parsed = self._safe_json_loads(text)
        fallback = self._fallback_summary(paper)
        summary = {
            "one_liner": str(parsed.get("one_liner", "")).strip() or fallback["one_liner"],
            "background": str(parsed.get("background", "")).strip() or fallback["background"],
            "problem": str(parsed.get("problem", "")).strip() or fallback["problem"],
            "method": str(parsed.get("method", "")).strip() or fallback["method"],
            "effectiveness": str(parsed.get("effectiveness", "")).strip() or fallback["effectiveness"],
            "highlights": str(parsed.get("highlights", "")).strip() or fallback["highlights"],
            "limitations": str(parsed.get("limitations", "")).strip() or fallback["limitations"],
            "other_info": str(parsed.get("other_info", "")).strip() or fallback["other_info"],
        }
        fallback_map = self._fallback_mindmap(paper, summary)
        mindmap = {
            "research_core": str(parsed.get("mindmap_core", "")).strip() or fallback_map["research_core"],
            "theoretical_basis": str(parsed.get("mindmap_theory", "")).strip()
            or fallback_map["theoretical_basis"],
            "method": str(parsed.get("mindmap_method", "")).strip() or fallback_map["method"],
            "experiments": str(parsed.get("mindmap_experiments", "")).strip() or fallback_map["experiments"],
            "conclusion": str(parsed.get("mindmap_conclusion", "")).strip() or fallback_map["conclusion"],
        }
        return summary, mindmap

    def _summarize_with_gemini(self, paper: Paper) -> tuple[dict[str, str], dict[str, str]]:
        prompt = (
            "请基于下面论文信息，输出中文 JSON，键必须是："
            "one_liner, background, problem, method, effectiveness, highlights, limitations, other_info, "
            "mindmap_core, mindmap_theory, mindmap_method, mindmap_experiments, mindmap_conclusion。"
            "每个字段 1-3 句话，内容要准确、克制、无夸大，不要编造实验数据。"
            "只输出 JSON，不要 Markdown，不要额外说明。\n\n"
            f"标题：{paper.title}\n"
            f"摘要：{paper.abstract}\n"
            f"作者：{', '.join(paper.authors[:8])}\n"
            f"标签：{', '.join(paper.tags[:10])}\n"
        )
        model_name = self._normalize_gemini_model(settings.gemini_model)
        url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent"
        headers = {
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
            },
        }
        params = {"key": settings.gemini_api_key} if settings.gemini_api_key else None
        resp = requests.post(url, json=payload, headers=headers, params=params, timeout=45)
        if resp.status_code in (400, 404) and settings.gemini_api_key:
            # Try auto-select a valid model once.
            alt = self._select_gemini_model(settings.gemini_api_key)
            if alt and alt != model_name:
                alt_url = f"https://generativelanguage.googleapis.com/v1beta/{alt}:generateContent"
                resp = requests.post(alt_url, json=payload, headers=headers, params=params, timeout=45)
        if resp.status_code == 429:
            raise RuntimeError(f"Gemini rate limited: {resp.status_code} {resp.text[:300]}")
        if resp.status_code >= 400:
            raise RuntimeError(f"Gemini request failed: {resp.status_code} {resp.text[:300]}")
        resp.raise_for_status()
        data = resp.json()
        text = ""
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            text = ""
        if not text:
            raise RuntimeError("Gemini empty response")
        try:
            parsed = self._safe_json_loads(text)
        except Exception as exc:
            raise RuntimeError(f"Gemini JSON parse failed: {exc}; raw={text[:200]}") from exc
        fallback = self._fallback_summary(paper)
        summary = {
            "one_liner": str(parsed.get("one_liner", "")).strip() or fallback["one_liner"],
            "background": str(parsed.get("background", "")).strip() or fallback["background"],
            "problem": str(parsed.get("problem", "")).strip() or fallback["problem"],
            "method": str(parsed.get("method", "")).strip() or fallback["method"],
            "effectiveness": str(parsed.get("effectiveness", "")).strip() or fallback["effectiveness"],
            "highlights": str(parsed.get("highlights", "")).strip() or fallback["highlights"],
            "limitations": str(parsed.get("limitations", "")).strip() or fallback["limitations"],
            "other_info": str(parsed.get("other_info", "")).strip() or fallback["other_info"],
        }
        fallback_map = self._fallback_mindmap(paper, summary)
        mindmap = {
            "research_core": str(parsed.get("mindmap_core", "")).strip() or fallback_map["research_core"],
            "theoretical_basis": str(parsed.get("mindmap_theory", "")).strip()
            or fallback_map["theoretical_basis"],
            "method": str(parsed.get("mindmap_method", "")).strip() or fallback_map["method"],
            "experiments": str(parsed.get("mindmap_experiments", "")).strip() or fallback_map["experiments"],
            "conclusion": str(parsed.get("mindmap_conclusion", "")).strip() or fallback_map["conclusion"],
        }
        return summary, mindmap

    @staticmethod
    def _normalize_gemini_model(model: str) -> str:
        if model.startswith("models/"):
            return model
        return f"models/{model}"

    @staticmethod
    def _select_gemini_model(api_key: str) -> str | None:
        try:
            resp = requests.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                params={"key": api_key},
                timeout=20,
            )
            if resp.status_code >= 400:
                return None
            data = resp.json()
        except Exception:
            return None
        models = data.get("models", [])
        # Prefer flash models that support generateContent
        candidates = []
        for m in models:
            name = m.get("name")
            methods = m.get("supportedGenerationMethods") or []
            if not name or "generateContent" not in methods:
                continue
            candidates.append(name)
        if not candidates:
            return None
        priority = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ]
        for p in priority:
            for name in candidates:
                if p in name:
                    return name
        return candidates[0]

    @staticmethod
    def _safe_json_loads(text: str) -> dict[str, Any]:
        content = (text or "").strip()

        # Common case: wrapped in markdown code fences.
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
        if fence:
            content = fence.group(1).strip()

        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        # Try to extract first object when pre/post text leaked.
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj_text = content[start : end + 1]
            # Remove trailing commas before object/array close.
            obj_text = re.sub(r",\s*([}\]])", r"\1", obj_text)
            try:
                data = json.loads(obj_text)
                if isinstance(data, dict):
                    return data
            except Exception:
                pass

            # Last resort: tolerate single-quoted dict-style output.
            try:
                lit = ast.literal_eval(obj_text)
                if isinstance(lit, dict):
                    return lit
            except Exception:
                pass

        raise RuntimeError("LLM response is not valid JSON")

    def _fallback_summary(self, paper: Paper) -> dict[str, str]:
        title = paper.title or "该论文"
        source_map = {
            "arxiv": "arXiv",
            "semantic_scholar": "Semantic Scholar",
            "huggingface": "Hugging Face Papers",
        }
        source_name = source_map.get(paper.source, paper.source)
        tag_hint = "、".join(paper.tags[:5]) if paper.tags else "未提供明确标签"
        return {
            "one_liner": f"《{title}》聚焦 AI 关键问题，提出了具备工程应用价值的方法框架。",
            "background": "研究背景指向当前方案在准确性、效率、泛化能力或可解释性上的现实瓶颈。",
            "problem": "核心问题是如何在真实任务中提升模型效果，并兼顾稳定性与可落地性。",
            "method": "从题目与元数据推断，作者通过模型结构改进、训练策略优化或任务流程重构来解决问题。",
            "effectiveness": "文献通常会以基准测试或消融实验验证有效性，具体提升幅度建议以正文实验表格为准。",
            "highlights": "亮点通常在于方法设计简洁、可迁移性较强，且对社区常见任务具有参考价值。",
            "limitations": "当前为自动摘要版本，缺少全文细节，仍需结合论文正文和代码仓做严格判断。",
            "other_info": f"来源: {source_name}；标签: {tag_hint}；建议结合原文与代码仓进一步评估可复现性。",
        }

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        raw = re.split(r"(?<=[。！？.!?])\s+|\n+", text or "")
        return [s.strip(" .;；") for s in raw if s and s.strip(" .;；")]

    def _fallback_mindmap(self, paper: Paper, summary: dict[str, str]) -> dict[str, str]:
        title = (paper.title or "该论文").strip()
        abstract_l = (paper.abstract or "").lower()
        title_l = title.lower()

        has_theory = any(k in abstract_l for k in ["theory", "theorem", "proof", "bayes", "analysis"])
        has_transformer = any(k in abstract_l + " " + title_l for k in ["transformer", "attention", "llm"])
        has_diffusion = any(k in abstract_l + " " + title_l for k in ["diffusion", "denoising"])
        has_rl = any(k in abstract_l + " " + title_l for k in ["reinforcement", "policy", "reward"])
        has_graph = any(k in abstract_l + " " + title_l for k in ["graph", "gnn"])
        has_exp = any(k in abstract_l for k in ["experiment", "benchmark", "dataset", "ablation", "sota"])

        method_hint = "模型结构改进与训练流程优化"
        if has_transformer:
            method_hint = "基于 Transformer/Attention 架构的建模与优化"
        elif has_diffusion:
            method_hint = "基于扩散式生成建模与采样策略优化"
        elif has_rl:
            method_hint = "基于强化学习策略迭代与奖励设计"
        elif has_graph:
            method_hint = "基于图结构建模与关系信息传播"

        theory_hint = "以统计学习与经验风险最小化为理论基础"
        if has_theory:
            theory_hint = "包含明确的理论分析或证明，解释方法有效性边界"

        exp_hint = "通过公开基准任务进行对比实验，验证方法在效果与稳定性上的收益"
        if not has_exp:
            exp_hint = "摘要未给出完整实验细节，建议重点查看实验章节与消融结果"

        core = f"围绕《{title}》所定义的关键任务，目标是在真实场景下提升性能与可用性。"
        theory = f"{theory_hint}，并结合任务约束组织模型假设。"
        method = f"方法主线为：{method_hint}，以解决现有方案在泛化或效率上的短板。"
        experiments = exp_hint + "。"
        conclusion = "结论显示该方案具备应用潜力，但最终价值仍需结合全文指标与复现实验综合判断。"
        return {
            "research_core": core,
            "theoretical_basis": theory,
            "method": method,
            "experiments": experiments,
            "conclusion": conclusion,
        }
