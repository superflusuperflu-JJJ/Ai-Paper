from __future__ import annotations

import argparse
from datetime import datetime
import json
from urllib.parse import urlencode

import uvicorn

from app.config import ensure_dirs, settings
from app.pipeline import DailyPipeline
from app.services.logger import build_logger
from app.services.notifier import notify_mac


def build_dashboard_url(run_date: str, *, cache_bust: str | None = None) -> str:
    params = {"date": run_date}
    if cache_bust:
        params["ts"] = cache_bust
    return f"{settings.dashboard_url}?{urlencode(params)}"


def cmd_run_once() -> None:
    ensure_dirs()
    log_file = settings.log_dir / f"daily-{datetime.now().strftime('%Y%m%d')}.log"
    status_file = settings.log_dir / "status.json"
    logger = build_logger(log_file)
    pipeline = DailyPipeline(logger)

    try:
        result = pipeline.run_once()
        opened_url = build_dashboard_url(
            result.get("run_date", datetime.now().date().isoformat()),
            cache_bust=datetime.now().strftime("%Y%m%d%H%M%S"),
        )
        logger.info("run success: %s", result)
        logger.info("open dashboard: %s", opened_url)
        status_file.write_text(
            json.dumps(
                {
                    "last_success_at": datetime.now().isoformat(timespec="seconds"),
                    "last_run_date": result.get("run_date"),
                    "count": result.get("count"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        notify_mac(
            settings.notify_title,
            f"今日论文已更新（{result.get('count', 0)}篇），点击打开页面。",
            opened_url,
        )
    except Exception as exc:
        logger.exception("run failed after retry")
        opened_url = build_dashboard_url(
            datetime.now().date().isoformat(),
            cache_bust=datetime.now().strftime("%Y%m%d%H%M%S"),
        )
        status_file.write_text(
            json.dumps(
                {
                    "last_failure_at": datetime.now().isoformat(timespec="seconds"),
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        notify_mac(settings.notify_title, f"日报任务失败：{exc}", opened_url)
        raise


def cmd_web(host: str, port: int) -> None:
    ensure_dirs()
    uvicorn.run("app.web.server:app", host=host, port=port, reload=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Paper Daily")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("run-once")
    web = sub.add_parser("web")
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8000)

    args = parser.parse_args()
    if args.cmd == "run-once":
        cmd_run_once()
    elif args.cmd == "web":
        cmd_web(args.host, args.port)


if __name__ == "__main__":
    main()
