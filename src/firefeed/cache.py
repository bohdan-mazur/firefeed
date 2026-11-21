"""File cache for API answers, keyed by a hash of everything that shapes the answer."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger("firefeed.cache")


def stable_hash(value: Any) -> str:
    """SHA-256 of a canonical JSON encoding of ``value``."""
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class JsonCache:
    """One JSON file per entry: ``<root>/<namespace>/<key>.json``."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def path(self, namespace: str, key: str) -> Path:
        return self.root / namespace / f"{key}.json"

    def get(self, namespace: str, key: str) -> dict | None:
        path = self.path(namespace, key)
        try:
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            log.warning("cache: %s is not valid JSON, treating it as a miss", path)
            return None

    def put(self, namespace: str, key: str, value: dict) -> Path:
        path = self.path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                json.dump(value, f, ensure_ascii=False, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return path
