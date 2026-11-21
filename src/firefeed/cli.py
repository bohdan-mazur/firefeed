"""Command line: ``firefeed run`` and ``firefeed evaluate``."""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import re
import sys
from pathlib import Path

import openai
from dotenv import load_dotenv

from firefeed import SYNTHETIC_NOTICE
from firefeed.analyze import QuotaExhausted, is_quota_error
from firefeed.budget import RequestLimitReached
from firefeed.config import Config, ConfigError, load_config
from firefeed.evaluate import evaluate, load_spec
from firefeed.export import write_json
from firefeed.ingest import IngestError
from firefeed.pipeline import ConfirmationRequired, MissingApiKey, TooManyRequests, run

DEFAULT_CONFIG = Path("firefeed.toml")
# API error texts can quote a masked key; keep even the masked form out of logs.
_KEY_LIKE = re.compile(r"sk-[A-Za-z0-9*_\-]{4,}")


def _setup_logging(verbose: bool, log_file: Path | None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )
    # The HTTP client logs request lines at INFO; keep the run log about the pipeline.
    for noisy in ("httpx", "httpx2", "httpcore", "httpcore2", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _config(args: argparse.Namespace) -> Config:
    path = args.config
    if path is None and DEFAULT_CONFIG.is_file():
        path = DEFAULT_CONFIG
    cfg = load_config(
        path,
        input_dir=getattr(args, "input", None),
        output_dir=getattr(args, "out", None),
        cache_dir=getattr(args, "cache", None),
    )
    load_dotenv(cfg.base_dir / ".env")
    load_dotenv(Path.cwd() / ".env")
    return cfg


def _cmd_run(args: argparse.Namespace) -> int:
    cfg = _config(args)
    if args.max_requests is not None:
        cfg = dataclasses.replace(
            cfg, limits=dataclasses.replace(cfg.limits, max_api_requests_per_run=args.max_requests)
        )
    _setup_logging(args.verbose, None if args.dry_run else cfg.output_dir / "run.log")
    if cfg.synthetic:
        logging.getLogger("firefeed").info(SYNTHETIC_NOTICE)
    summary = run(cfg, dry_run=args.dry_run, assume_yes=args.yes)
    return 1 if summary.errors else 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    cfg = _config(args)
    _setup_logging(args.verbose, None)
    spec_path = args.spec or cfg.spec
    if spec_path is None:
        raise ConfigError("no spec: pass --spec or set [dataset] spec")
    feed_path = args.feed or cfg.output_dir / "feed.json"
    out_path = args.out or cfg.output_dir / "evaluation.json"
    feed = json.loads(feed_path.read_text(encoding="utf-8"))
    report = evaluate(feed, load_spec(spec_path))
    write_json(out_path, report)
    log = logging.getLogger("firefeed.evaluate")
    log.info("compared %d calls with %s", report["calls_compared"], spec_path.name)
    for name, f in report["fields"].items():
        log.info("  %-14s %2d/%d", name, f["correct"], f["total"])
    g = report["grouping"]
    log.info(
        "  incidents      %2d/%d grouped exactly", g["incidents_exact"], g["incidents_expected"]
    )
    log.info("wrote %s", out_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="firefeed",
        description="Fire department radio traffic to text to structured incidents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="ingest, transcribe, analyze, group and export")
    run_p.add_argument("--config", type=Path, help="TOML file (default: ./firefeed.toml)")
    run_p.add_argument("--input", type=Path, help="folder with calls (.txt or audio + .json)")
    run_p.add_argument("--out", type=Path, help="output folder for feed.json")
    run_p.add_argument("--cache", type=Path, help="cache folder")
    run_p.add_argument(
        "--dry-run",
        action="store_true",
        help="count cache misses and estimate cost; make no API requests",
    )
    run_p.add_argument(
        "--yes",
        action="store_true",
        help="go ahead when the estimate is above [limits] confirm_above_usd",
    )
    run_p.add_argument(
        "--max-requests", type=int, help="override [limits] max_api_requests_per_run"
    )
    run_p.add_argument("-v", "--verbose", action="store_true")
    run_p.set_defaults(handler=_cmd_run)

    ev_p = sub.add_parser("evaluate", help="compare feed.json with the expected answers")
    ev_p.add_argument("--config", type=Path, help="TOML file (default: ./firefeed.toml)")
    ev_p.add_argument("--spec", type=Path, help="CSV with expected answers")
    ev_p.add_argument("--feed", type=Path, help="feed.json (default: output folder)")
    ev_p.add_argument("--out", type=Path, help="report path (default: output folder)")
    ev_p.add_argument("-v", "--verbose", action="store_true")
    ev_p.set_defaults(handler=_cmd_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (
        ConfigError,
        IngestError,
        MissingApiKey,
        TooManyRequests,
        ConfirmationRequired,
        RequestLimitReached,
        QuotaExhausted,
        FileNotFoundError,
        ValueError,
    ) as exc:
        logging.getLogger("firefeed").error("%s", exc)
        print(f"firefeed: {exc}", file=sys.stderr)
        return 1
    except openai.AuthenticationError:
        message = (
            "the API rejected the key (401). Check OPENAI_API_KEY in .env: the whole key, "
            "no quotes, spaces or line breaks inside it."
        )
    except openai.RateLimitError as exc:
        # Raised outside the analyzer (for example by transcription).
        message = str(QuotaExhausted()) if is_quota_error(exc) else "API rate limit (429)"
    except openai.OpenAIError as exc:
        # Unknown model, bad parameter: stop the run. Answers so far stay cached.
        status = getattr(exc, "status_code", None)
        detail = _KEY_LIKE.sub("sk-[hidden]", str(exc))
        message = f"API error{f' {status}' if status else ''}: {type(exc).__name__}: {detail}"
    logging.getLogger("firefeed").error("%s", message)
    print(f"firefeed: {message}", file=sys.stderr)
    return 1
