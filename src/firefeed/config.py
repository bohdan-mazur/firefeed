"""Load firefeed.toml. Secrets come from the environment (and .env), never from this file."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """The configuration is missing a value or has a wrong one."""


@dataclass(frozen=True)
class Prices:
    """USD per 1M tokens."""

    input: float = 0.10
    cached_input: float = 0.01
    output: float = 0.50


@dataclass(frozen=True)
class AnalysisConfig:
    model: str = "gpt-6-luna"
    reasoning_effort: str | None = "low"
    max_output_tokens: int = 2000
    use_gazetteer_hints: bool = True
    estimated_output_tokens: int = 400
    price_per_million: Prices = field(default_factory=Prices)


@dataclass(frozen=True)
class TranscribeConfig:
    model: str = "gpt-transcribe"
    language: str | None = "en"
    prompt: str | None = None
    price_per_minute: float = 0.0045


@dataclass(frozen=True)
class ClusterConfig:
    window_s: int = 120
    max_gap_s: int = 3600


@dataclass(frozen=True)
class LimitsConfig:
    max_api_requests_per_run: int = 60
    confirm_above_usd: float = 0.50


@dataclass(frozen=True)
class NotifyConfig:
    enabled: bool = False
    telegram: bool = False
    webhook: bool = False


@dataclass(frozen=True)
class Config:
    input_dir: Path
    output_dir: Path
    cache_dir: Path
    base_dir: Path
    gazetteer: Path | None = None
    spec: Path | None = None
    dataset_name: str = "Untitled dataset"
    synthetic: bool = False
    price_source: str | None = None
    prices_checked: str | None = None
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    transcribe: TranscribeConfig = field(default_factory=TranscribeConfig)
    cluster: ClusterConfig = field(default_factory=ClusterConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    notify: NotifyConfig = field(default_factory=NotifyConfig)


# Field annotations are strings here (``from __future__ import annotations``).
_ALLOWED_TYPES: dict[str, tuple[type, ...]] = {
    "str": (str,),
    "str | None": (str,),  # TOML has no null; an empty string means "not set"
    "int": (int,),
    "float": (int, float),
    "bool": (bool,),
}


def _section(cls: type, table: dict[str, Any], name: str) -> Any:
    """Build a config dataclass from a TOML table, rejecting unknown keys and wrong types."""
    known = {f.name: f for f in fields(cls)}
    unknown = sorted(set(table) - set(known))
    if unknown:
        raise ConfigError(f"[{name}] has unknown keys: {', '.join(unknown)}")
    values: dict[str, Any] = {}
    for key, raw in table.items():
        annotation = str(known[key].type)
        if annotation == "Prices":
            if not isinstance(raw, dict):
                raise ConfigError(f"[{name}.{key}] must be a table")
            values[key] = _section(Prices, raw, f"{name}.{key}")
            continue
        allowed = _ALLOWED_TYPES[annotation]
        if isinstance(raw, bool) and bool not in allowed:
            raise ConfigError(f"[{name}] {key} must not be true/false")
        if not isinstance(raw, allowed):
            raise ConfigError(f"[{name}] {key} has the wrong type: {raw!r}")
        if annotation == "float":
            raw = float(raw)
        elif annotation == "str | None" and raw == "":
            raw = None
        values[key] = raw
    return cls(**values)


def _path(base: Path, value: Any, key: str) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError(f"[dataset] {key} must be a non-empty string")
    return (base / value).resolve()


def load_config(
    path: Path | None = None,
    *,
    input_dir: Path | None = None,
    output_dir: Path | None = None,
    cache_dir: Path | None = None,
) -> Config:
    """Read the TOML file (if any) and apply command-line overrides.

    Paths inside the file are relative to the file; paths given on the command line are relative
    to the current directory.
    """
    data: dict[str, Any] = {}
    base = Path.cwd()
    if path is not None:
        if not path.is_file():
            raise ConfigError(f"config file not found: {path}")
        with path.open("rb") as f:
            try:
                data = tomllib.load(f)
            except tomllib.TOMLDecodeError as exc:
                raise ConfigError(f"{path}: {exc}") from exc
        base = path.resolve().parent

    allowed_sections = {
        "dataset",
        "analysis",
        "transcribe",
        "prices",
        "cluster",
        "limits",
        "notify",
    }
    unknown = sorted(set(data) - allowed_sections)
    if unknown:
        raise ConfigError(f"unknown sections: {', '.join(unknown)}")

    ds = dict(data.get("dataset", {}))
    dataset_keys = {
        "name",
        "synthetic",
        "input_dir",
        "output_dir",
        "cache_dir",
        "gazetteer",
        "spec",
    }
    unknown = sorted(set(ds) - dataset_keys)
    if unknown:
        raise ConfigError(f"[dataset] has unknown keys: {', '.join(unknown)}")

    resolved_input = (
        input_dir.resolve() if input_dir else _path(base, ds.get("input_dir"), "input_dir")
    )
    if resolved_input is None:
        raise ConfigError("input folder is not set: pass --input or set [dataset] input_dir")
    resolved_output = (
        output_dir.resolve()
        if output_dir
        else _path(base, ds.get("output_dir", "out"), "output_dir")
    )
    resolved_cache = (
        cache_dir.resolve()
        if cache_dir
        else _path(base, ds.get("cache_dir", ".cache"), "cache_dir")
    )

    prices = data.get("prices", {})
    unknown = sorted(set(prices) - {"source", "checked"})
    if unknown:
        raise ConfigError(f"[prices] has unknown keys: {', '.join(unknown)}")

    name = ds.get("name", "Untitled dataset")
    synthetic = ds.get("synthetic", False)
    if not isinstance(name, str) or not isinstance(synthetic, bool):
        raise ConfigError("[dataset] name must be a string and synthetic true/false")

    assert resolved_output is not None and resolved_cache is not None
    return Config(
        input_dir=resolved_input,
        output_dir=resolved_output,
        cache_dir=resolved_cache,
        base_dir=base,
        gazetteer=_path(base, ds.get("gazetteer"), "gazetteer"),
        spec=_path(base, ds.get("spec"), "spec"),
        dataset_name=name,
        synthetic=synthetic,
        price_source=prices.get("source"),
        prices_checked=prices.get("checked"),
        analysis=_section(AnalysisConfig, data.get("analysis", {}), "analysis"),
        transcribe=_section(TranscribeConfig, data.get("transcribe", {}), "transcribe"),
        cluster=_section(ClusterConfig, data.get("cluster", {}), "cluster"),
        limits=_section(LimitsConfig, data.get("limits", {}), "limits"),
        notify=_section(NotifyConfig, data.get("notify", {}), "notify"),
    )
