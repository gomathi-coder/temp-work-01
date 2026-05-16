"""Structured JSON Lines logging for LinkWiki.

Two log files are written to the logs/ directory:
  - linkwiki.jsonl  — all records at the configured level (default INFO)
  - errors.jsonl    — ERROR and above only, for quick failure scanning

Each record is a single JSON object on its own line:
  {"ts":"2026-05-16T10:23:45.123456+00:00","level":"INFO","logger":"linkwiki.extractors.web",
   "msg":"HTTP response received","url":"https://example.com","status_code":200,"duration_ms":234}

Extra context fields are passed via logging's extra= parameter and merged into the top-level object.
"""

from __future__ import annotations
import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path

# Fields that belong to Python's LogRecord internals — excluded from JSON output
_INTERNAL_FIELDS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
})


class _JsonFormatter(logging.Formatter):
    """Formats each LogRecord as a single JSON object (no trailing newline — handler adds one)."""

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()
        obj: dict = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.message,
        }
        # Merge caller-supplied extra= fields
        for k, v in record.__dict__.items():
            if k not in _INTERNAL_FIELDS:
                obj[k] = v
        if record.exc_info:
            obj["exc"] = self.formatException(record.exc_info)
        return json.dumps(obj, default=str)


def setup_logging(log_dir: Path, level_str: str = "INFO") -> None:
    """Configure the 'linkwiki' logger hierarchy.

    Idempotent — calling it a second time is a no-op so CLI re-invocations
    inside the same process don't double-attach handlers.
    """
    root = logging.getLogger("linkwiki")
    if root.handlers:
        return

    level = getattr(logging, level_str.upper(), logging.INFO)
    root.setLevel(logging.DEBUG)  # handlers apply their own level filters

    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = _JsonFormatter()

    # ── Main log: all records at the configured level ──────────────────────
    main_h = logging.handlers.RotatingFileHandler(
        log_dir / "linkwiki.jsonl",
        maxBytes=10 * 1024 * 1024,  # 10 MB per file
        backupCount=5,
        encoding="utf-8",
    )
    main_h.setLevel(level)
    main_h.setFormatter(fmt)

    # ── Error log: ERROR and CRITICAL only ────────────────────────────────
    err_h = logging.handlers.RotatingFileHandler(
        log_dir / "errors.jsonl",
        maxBytes=5 * 1024 * 1024,  # 5 MB per file
        backupCount=3,
        encoding="utf-8",
    )
    err_h.setLevel(logging.ERROR)
    err_h.setFormatter(fmt)

    root.addHandler(main_h)
    root.addHandler(err_h)
