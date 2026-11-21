from __future__ import annotations

import dataclasses
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from firefeed.config import Config
from firefeed.gazetteer import Gazetteer
from helpers import GAZETTEER


@pytest.fixture
def gazetteer_path(tmp_path: Path) -> Path:
    path = tmp_path / "gazetteer.json"
    path.write_text(json.dumps(GAZETTEER), encoding="utf-8")
    return path


@pytest.fixture
def gazetteer(gazetteer_path: Path) -> Gazetteer:
    return Gazetteer.load(gazetteer_path)


@pytest.fixture
def make_config(tmp_path: Path, gazetteer_path: Path) -> Callable[..., Config]:
    def make(**overrides: object) -> Config:
        cfg = Config(
            input_dir=tmp_path / "calls",
            output_dir=tmp_path / "out",
            cache_dir=tmp_path / "cache",
            base_dir=tmp_path,
            gazetteer=gazetteer_path,
            dataset_name="Test County",
            synthetic=True,
        )
        return dataclasses.replace(cfg, **overrides)

    return make
