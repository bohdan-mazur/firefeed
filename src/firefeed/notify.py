"""Alerts for new fire incidents through Telegram and a generic webhook. Off in the demo.

Already sent incidents are remembered in ``notified.json`` in the cache folder, so a re-run does
not send them again.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from firefeed.config import NotifyConfig

log = logging.getLogger("firefeed.notify")

PostJson = Callable[[str, dict[str, Any]], int]


def post_json(url: str, payload: dict[str, Any], timeout: float = 10.0) -> int:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status


def format_alert(incident: dict[str, Any]) -> str:
    lines = [f"Fire call: {incident['incident_type'].replace('_', ' ')}"]
    if incident.get("street"):
        lines.append(f"Location: {incident['street']}")
    if incident.get("units"):
        lines.append("Units: " + ", ".join(incident["units"]))
    lines.append(f"First heard: {incident['start']}")
    if incident.get("summary"):
        lines.append(incident["summary"])
    return "\n".join(lines)


def _incident_key(incident: dict[str, Any]) -> str:
    return f"{incident['call_ids'][0]}@{incident['start']}"


class Notifier:
    def __init__(
        self,
        cfg: NotifyConfig,
        env: Mapping[str, str],
        state_path: Path,
        post: PostJson = post_json,
    ) -> None:
        self.cfg = cfg
        self.env = env
        self.state_path = state_path
        self.post = post

    def _sent(self) -> set[str]:
        try:
            return set(json.loads(self.state_path.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return set()

    def _remember(self, keys: set[str]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(sorted(keys), indent=2) + "\n", encoding="utf-8")

    def _require(self, name: str) -> str:
        value = self.env.get(name, "")
        if not value:
            raise RuntimeError(f"{name} is not set; it is needed for notifications")
        return value

    def send_new(self, incidents: list[dict[str, Any]]) -> int:
        fire = [i for i in incidents if i["is_fire"]]
        if not self.cfg.enabled:
            log.info("notify: disabled in config, %d fire incident(s) not sent", len(fire))
            return 0
        sent = self._sent()
        count = 0
        for incident in fire:
            key = _incident_key(incident)
            if key in sent:
                continue
            if self.cfg.telegram:
                token = self._require("TELEGRAM_BOT_TOKEN")
                chat_id = self._require("TELEGRAM_CHAT_ID")
                self.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    {"chat_id": chat_id, "text": format_alert(incident)},
                )
            if self.cfg.webhook:
                self.post(
                    self._require("WEBHOOK_URL"), {"type": "fire_incident", "incident": incident}
                )
            sent.add(key)
            count += 1
            log.info("notify: sent %s", incident["id"])
        self._remember(sent)
        return count
