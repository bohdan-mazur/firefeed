"""Local knowledge: street names, unit names and radio codes, with forgiving matching.

Speech-to-text splits and bends street names ("Bell weather Avenue", "Thimble Crick Road"),
so streets are matched on normalized words first and then with a fuzzy comparison.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

_NUMBER_WORDS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
}
_ABBREVIATIONS = {
    "st": "street",
    "str": "street",
    "ave": "avenue",
    "av": "avenue",
    "rd": "road",
    "dr": "drive",
    "ln": "lane",
    "wy": "way",
    "ct": "court",
    "blvd": "boulevard",
    "pl": "place",
    "hwy": "highway",
    "pkwy": "parkway",
    "cir": "circle",
}
_STREET_SUFFIXES = frozenset(_ABBREVIATIONS.values()) | {"way", "terrace", "trail", "crossing"}

FUZZY_THRESHOLD = 0.8
# A core name shorter than this ("main") is matched only together with its suffix ("main street").
MIN_CORE_CHARS = 6


def normalize(text: str) -> str:
    """Lowercase, drop punctuation, expand street abbreviations and number words."""
    words = re.sub(r"[^0-9a-z]+", " ", text.lower()).split()
    return " ".join(_NUMBER_WORDS.get(w, _ABBREVIATIONS.get(w, w)) for w in words)


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


@dataclass(frozen=True)
class Street:
    name: str
    variants: tuple[str, ...]

    @classmethod
    def build(cls, name: str, aliases: list[str] | tuple[str, ...] = ()) -> Street:
        variants: list[str] = []
        for form in (name, *aliases):
            words = normalize(form).split()
            if not words:
                continue
            core = words[:-1] if len(words) > 1 and words[-1] in _STREET_SUFFIXES else words
            # Short or common cores stay with their suffix to avoid matching ordinary words.
            variant = " ".join(core if len("".join(core)) >= MIN_CORE_CHARS else words)
            if variant not in variants:
                variants.append(variant)
        return cls(name=name, variants=tuple(variants))


def _find(words: list[str], variant: str) -> tuple[int, float] | None:
    """Earliest position of ``variant`` in ``words``: exact first, then fuzzy."""
    target_words = variant.split()
    n = len(target_words)
    for i in range(len(words) - n + 1):
        if words[i : i + n] == target_words:
            return i, 1.0
    target = variant.replace(" ", "")
    best: tuple[int, float] | None = None
    for size in range(max(1, n - 1), n + 2):
        for i in range(len(words) - size + 1):
            chunk = "".join(words[i : i + size])
            if abs(len(chunk) - len(target)) > 3 or _digits(chunk) != _digits(target):
                continue
            score = SequenceMatcher(None, chunk, target).ratio()
            if score >= FUZZY_THRESHOLD and (best is None or (i, -score) < (best[0], -best[1])):
                best = (i, score)
    return best


@dataclass
class Gazetteer:
    name: str = ""
    streets: list[Street] = field(default_factory=list)
    units: list[str] = field(default_factory=list)
    unit_aliases: dict[str, str] = field(default_factory=dict)
    channels: list[str] = field(default_factory=list)
    dispatcher: str | None = None
    radio_codes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> Gazetteer:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        streets = [Street.build(s["name"], s.get("aliases", [])) for s in data.get("streets", [])]
        units = [u["name"] for u in data.get("units", [])]
        aliases = {a: u["name"] for u in data.get("units", []) for a in u.get("aliases", [])}
        return cls(
            name=data.get("name", ""),
            streets=streets,
            units=units,
            unit_aliases=aliases,
            channels=list(data.get("channels", [])),
            dispatcher=data.get("dispatcher"),
            radio_codes=dict(data.get("radio_codes", {})),
        )

    def match_street(self, text: str | None) -> str | None:
        """The gazetteer street named first in ``text``, or None."""
        if not text or not self.streets:
            return None
        words = normalize(text).split()
        best: tuple[int, float, str] | None = None
        for street in self.streets:
            for variant in street.variants:
                found = _find(words, variant)
                if found and (best is None or (found[0], -found[1]) < (best[0], -best[1])):
                    best = (found[0], found[1], street.name)
        return best[2] if best else None

    def normalize_units(self, names: list[str]) -> tuple[list[str], list[str]]:
        """Canonical unit names in order of mention, and the ones the gazetteer does not know."""
        lookup = {normalize(u): u for u in self.units}
        lookup.update({normalize(a): u for a, u in self.unit_aliases.items()})
        units: list[str] = []
        unknown: list[str] = []
        for raw in names:
            norm = normalize(raw)
            if not norm:
                continue
            canonical = lookup.get(norm)
            if canonical is None:
                canonical = " ".join(w.capitalize() for w in norm.split())
                if self.units and canonical not in unknown:
                    unknown.append(canonical)
            if canonical not in units:
                units.append(canonical)
        return units, unknown

    def hints(self) -> str | None:
        """Local knowledge for the analysis prompt."""
        lines = []
        if self.streets:
            lines.append("Known streets: " + "; ".join(s.name for s in self.streets) + ".")
        if self.units:
            lines.append("Known units: " + "; ".join(self.units) + ".")
        if self.dispatcher:
            lines.append(f'"{self.dispatcher}" is the call sign of the dispatcher.')
        if self.radio_codes:
            codes = "; ".join(f"{code} = {meaning}" for code, meaning in self.radio_codes.items())
            lines.append(f"Local radio codes: {codes}.")
        return "\n".join(lines) or None
