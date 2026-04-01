from __future__ import annotations

import logging
from pathlib import Path


def build_logger(log_file: Path) -> logging.Logger:
    logger = logging.getLogger("ai-paper-daily")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)

    fh = logging.FileHandler(log_file)
    fh.setFormatter(formatter)

    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger
