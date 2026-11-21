from pathlib import Path
from typing import Any

import pytest

from firefeed.config import NotifyConfig
from firefeed.notify import Notifier, format_alert

INCIDENT = {
    "id": "inc-01",
    "call_ids": ["c1", "c2"],
    "start": "2026-10-17T13:04:12-05:00",
    "incident_type": "structure_fire",
    "is_fire": True,
    "street": "Bellwether Avenue",
    "units": ["Engine 1", "Ladder 1"],
    "summary": "Structure fire dispatch.",
}
NOT_FIRE = {**INCIDENT, "id": "inc-02", "call_ids": ["c9"], "is_fire": False}
ENV = {
    "TELEGRAM_BOT_TOKEN": "test-token",
    "TELEGRAM_CHAT_ID": "42",
    "WEBHOOK_URL": "https://hooks.example.test/firefeed",
}


class Recorder:
    def __init__(self) -> None:
        self.posts: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, url: str, payload: dict[str, Any]) -> int:
        self.posts.append((url, payload))
        return 200


def test_alert_text() -> None:
    assert format_alert(INCIDENT) == (
        "Fire call: structure fire\nLocation: Bellwether Avenue\nUnits: Engine 1, Ladder 1\n"
        "First heard: 2026-10-17T13:04:12-05:00\nStructure fire dispatch."
    )


def test_disabled_sends_nothing(tmp_path: Path) -> None:
    post = Recorder()
    cfg = NotifyConfig(enabled=False, telegram=True, webhook=True)

    assert Notifier(cfg, ENV, tmp_path / "notified.json", post).send_new([INCIDENT]) == 0
    assert post.posts == []
    assert not (tmp_path / "notified.json").exists()


def test_sends_each_fire_incident_once(tmp_path: Path) -> None:
    post = Recorder()
    notifier = Notifier(
        NotifyConfig(enabled=True, telegram=True, webhook=True),
        ENV,
        tmp_path / "notified.json",
        post,
    )

    assert notifier.send_new([INCIDENT, NOT_FIRE]) == 1
    assert notifier.send_new([INCIDENT]) == 0

    telegram, webhook = post.posts
    assert telegram[0] == "https://api.telegram.org/bottest-token/sendMessage"
    assert telegram[1]["chat_id"] == "42"
    assert "Location: Bellwether Avenue" in telegram[1]["text"]
    assert webhook == (ENV["WEBHOOK_URL"], {"type": "fire_incident", "incident": INCIDENT})


def test_missing_secret_is_a_clear_error(tmp_path: Path) -> None:
    notifier = Notifier(
        NotifyConfig(enabled=True, telegram=True), {}, tmp_path / "n.json", Recorder()
    )

    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN is not set"):
        notifier.send_new([INCIDENT])
