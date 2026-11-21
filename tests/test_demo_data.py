"""Checks on the committed demo dataset and on the repository itself."""

import csv
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest

from firefeed.gazetteer import Gazetteer, normalize
from firefeed.ingest import load_calls
from firefeed.schema import INCIDENT_TYPES, STATUSES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CALLS = DATA / "demo" / "calls"


@pytest.fixture(scope="module")
def spec() -> list[dict[str, str]]:
    with (DATA / "spec.csv").open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def gazetteer() -> Gazetteer:
    return Gazetteer.load(DATA / "gazetteer.json")


def transcript(call_id: str) -> str:
    return (CALLS / f"{call_id}.txt").read_text(encoding="utf-8")


def test_spec_matches_the_input_folder(spec: list[dict[str, str]]) -> None:
    calls = load_calls(CALLS)

    assert [c.id for c in calls] == [row["call_id"] for row in spec]
    for call, row in zip(calls, spec, strict=True):
        assert call.timestamp.isoformat() == row["timestamp"]
        assert call.channel == row["channel"]
        assert call.text_path is not None


def test_labels_use_known_values(spec: list[dict[str, str]], gazetteer: Gazetteer) -> None:
    streets = {s.name for s in gazetteer.streets}
    for row in spec:
        assert row["incident_type"] in INCIDENT_TYPES, row["call_id"]
        assert row["status"] in STATUSES, row["call_id"]
        assert row["is_fire"] in ("true", "false"), row["call_id"]
        assert row["channel"] in gazetteer.channels, row["call_id"]
        assert not row["street"] or row["street"] in streets, row["call_id"]
        for unit in filter(None, row["units"].split(";")):
            assert unit in gazetteer.units, row["call_id"]
        about_incident = row["status"] != "none"
        assert about_incident == (row["incident_type"] != "not_incident"), row["call_id"]
        assert about_incident == bool(row["incident_id"]), row["call_id"]


def test_distribution_follows_the_plan(spec: list[dict[str, str]]) -> None:
    assert 40 <= len(spec) <= 60
    not_fire = sum(row["is_fire"] == "false" for row in spec) / len(spec)
    assert 0.25 <= not_fire <= 0.35
    sizes = Counter(row["incident_id"] for row in spec if row["incident_id"])
    assert 6 <= sum(1 for n in sizes.values() if n > 1) <= 10


def test_labels_agree_with_the_transcripts(
    spec: list[dict[str, str]], gazetteer: Gazetteer
) -> None:
    for row in spec:
        text = transcript(row["call_id"])
        named = [u for u in gazetteer.units if re.search(rf"\b{normalize(u)}\b", normalize(text))]
        assert sorted(named) == sorted(filter(None, row["units"].split(";"))), row["call_id"]
        if row["status"] != "none":
            assert gazetteer.match_street(text) == (row["street"] or None), row["call_id"]


# Built from parts so this file does not match itself.
FORBIDDEN = [
    "open" + "mhz",
    "sele" + "nium",
    "scp" + "25",
    "troy" + "fd",
    "ruser" + "name",
    "mrvulpes" + "tech",
]
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b"),
    re.compile(r"asst_[A-Za-z0-9]{16,}"),
]
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
BINARY_SUFFIXES = {".png", ".jpg", ".ico", ".woff2", ".wav", ".mp3"}


def repository_files() -> list[Path]:
    """Files git would publish: tracked or untracked, minus ignored ones such as .env."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout.decode("utf-8")
        paths = [ROOT / p for p in listed.split("\0") if p]
    except (OSError, subprocess.CalledProcessError):  # no git: walk the tree instead
        paths = [
            p
            for p in ROOT.rglob("*")
            if not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts)
            and not (p.name.startswith(".env") and p.name != ".env.example")
        ]
    return [p for p in paths if p.is_file() and p.suffix not in BINARY_SUFFIXES]


def test_no_traces_of_the_old_collector_or_secrets() -> None:
    problems = []
    for path in repository_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lowered = text.lower()
        problems += [f"{path.name}: {word}" for word in FORBIDDEN if word in lowered]
        problems += [f"{path.name}: secret-like text" for p in SECRET_PATTERNS if p.search(text)]
    assert problems == []
