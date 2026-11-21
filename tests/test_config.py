from pathlib import Path

import pytest

from firefeed.config import ConfigError, load_config

ROOT = Path(__file__).resolve().parents[1]


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "firefeed.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_demo_config_loads() -> None:
    cfg = load_config(ROOT / "firefeed.toml")

    assert cfg.input_dir == ROOT / "data" / "demo" / "calls"
    assert cfg.cache_dir == ROOT / "data" / "demo" / "cache"
    assert cfg.synthetic is True
    assert cfg.analysis.model == "gpt-6-luna"
    assert cfg.analysis.price_per_million.output == 0.50
    assert cfg.notify.enabled is False
    assert cfg.price_source and cfg.prices_checked


def test_paths_are_relative_to_the_file(tmp_path: Path) -> None:
    cfg = load_config(write(tmp_path, '[dataset]\ninput_dir = "calls"\n'))

    assert cfg.input_dir == (tmp_path / "calls").resolve()
    assert cfg.output_dir == (tmp_path / "out").resolve()
    assert cfg.cache_dir == (tmp_path / ".cache").resolve()


def test_command_line_overrides(tmp_path: Path) -> None:
    cfg = load_config(None, input_dir=tmp_path / "in", output_dir=tmp_path / "o")

    assert cfg.input_dir == (tmp_path / "in").resolve()
    assert cfg.output_dir == (tmp_path / "o").resolve()


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('[dataset]\ninput_dir = "c"\n[analysis]\nmodle = "x"\n', "unknown keys: modle"),
        ('[dataset]\ninput_dir = "c"\n[cluster]\nwindow_s = "120"\n', "wrong type"),
        ('[dataset]\ninput_dir = "c"\n[limits]\nconfirm_above_usd = true\n', "true/false"),
        ('[dataset]\ninput_dir = "c"\n[extra]\n', "unknown sections: extra"),
        ("[dataset]\n", "input folder is not set"),
    ],
)
def test_rejects_mistakes(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, text))


def test_empty_string_turns_an_option_off(tmp_path: Path) -> None:
    cfg = load_config(
        write(tmp_path, '[dataset]\ninput_dir = "c"\n[analysis]\nreasoning_effort = ""\n')
    )

    assert cfg.analysis.reasoning_effort is None
