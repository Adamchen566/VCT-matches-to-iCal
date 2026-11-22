"""Read the calendars stored in this repository.

The GUI shows what the repository already holds (the live subscription
calendar plus every archived event) instead of scraping vlr.gg itself, so it
works offline and always matches what subscribers see.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from pathlib import Path
from urllib.parse import quote

from icalendar import Calendar


# PyInstaller unpacks bundled data files next to sys._MEIPASS.
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
LIVE_ICS_NAME = "vct_OnGoing.ics"
ARCHIVE_DIR_NAME = "Calendar_Files"

LIVE_SUBSCRIBE_URL = (
    "https://raw.githubusercontent.com/Adamchen566/VCT-matches-to-iCal/"
    "main/vct_OnGoing.ics"
)
ARCHIVE_SUBSCRIBE_BASE = (
    "https://adamchen566.github.io/VCT-matches-to-iCal/Calendar_Files/"
)

LIVE_GROUP = "当前"
OTHER_GROUP = "其他"

SCORE_PATTERN = re.compile(r"(?:Score|比分)\s*[:：]\s*(\d+)\s*:\s*(\d+)")
TAG_PATTERN = re.compile(r"^\[([^\]]+)\]\s*(.*)$")


@dataclass(frozen=True)
class CalendarEntry:
    """One calendar file the GUI can open."""

    group: str  # year such as "2026", or LIVE_GROUP / OTHER_GROUP
    title: str
    path: Path
    live: bool = False

    @property
    def subscribe_url(self) -> str:
        if self.live:
            return LIVE_SUBSCRIBE_URL
        return ARCHIVE_SUBSCRIBE_BASE + quote(self.path.name)


@dataclass(frozen=True)
class MatchRow:
    start: datetime | None
    region: str
    team1: str
    team2: str
    score1: int | None
    score2: int | None

    @property
    def score(self) -> str:
        if self.score1 is None or self.score2 is None:
            return "-"
        return f"{self.score1}:{self.score2}"

    def local_time_text(self) -> str:
        """Start time in the computer's own timezone."""
        if self.start is None:
            return "待定"
        return self.start.astimezone().strftime("%Y-%m-%d %H:%M")


def describe_archive_name(stem: str) -> tuple[str, str]:
    """Split "2026_Stage_2_CN" into the group "2026" and title "Stage 2 CN"."""
    year, _, rest = stem.partition("_")
    if re.fullmatch(r"\d{4}", year) and rest:
        return year, rest.replace("_", " ")
    return OTHER_GROUP, stem.replace("_", " ")


def list_calendars(root: Path | None = None) -> list[CalendarEntry]:
    """Live calendar first, then archives from the newest year to the oldest."""
    root = root or ROOT
    entries: list[CalendarEntry] = []

    live_path = root / LIVE_ICS_NAME
    if live_path.exists():
        entries.append(CalendarEntry(LIVE_GROUP, "当前赛事", live_path, live=True))

    archives: list[CalendarEntry] = []
    for path in (root / ARCHIVE_DIR_NAME).glob("*.ics"):
        group, title = describe_archive_name(path.stem)
        archives.append(CalendarEntry(group, title, path))

    def sort_key(entry: CalendarEntry) -> tuple[int, int, str]:
        if entry.group == OTHER_GROUP:
            return (1, 0, entry.title)
        return (0, -int(entry.group), entry.title)

    return entries + sorted(archives, key=sort_key)


def group_names(entries: list[CalendarEntry]) -> list[str]:
    """Distinct groups in display order."""
    names: list[str] = []
    for entry in entries:
        if entry.group not in names:
            names.append(entry.group)
    return names


def _as_utc(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time(), tzinfo=timezone.utc)
    return None


def parse_match(component) -> MatchRow | None:
    """Turn one VEVENT into a match, or None when it is not a match."""
    summary = str(component.get("SUMMARY") or "").strip()
    location = str(component.get("LOCATION") or "").strip()
    description = str(component.get("DESCRIPTION") or "")

    # Calendars written by update_calendar.py: "[CN] A vs B", LOCATION "VCT CN".
    # Older calendars: "A vs B" (or "[TBD] A vs B"), LOCATION "CN Score: 2:0".
    region = ""
    tagged = TAG_PATTERN.match(summary)
    if location.startswith("VCT "):
        region = location[4:].strip()
        if tagged:
            summary = tagged.group(2)
    else:
        region = location.split(" Score:")[0].strip()
        if tagged:
            summary = tagged.group(2)

    if " vs " not in summary:
        return None
    team1, team2 = (part.strip() for part in summary.split(" vs ", 1))

    score = SCORE_PATTERN.search(description) or SCORE_PATTERN.search(location)
    score1 = int(score.group(1)) if score else None
    score2 = int(score.group(2)) if score else None

    start = None
    if component.get("DTSTART") is not None:
        start = _as_utc(component.decoded("DTSTART"))

    return MatchRow(start, region, team1 or "TBD", team2 or "TBD", score1, score2)


def load_matches(path: Path) -> list[MatchRow]:
    """All matches in a calendar file, earliest first."""
    # Some older files carry doubled carriage returns ("\r\r\n"), which makes
    # every value end in a stray "\r"; normalise before parsing.
    data = re.sub(rb"\r+\n", b"\r\n", path.read_bytes())
    calendar = Calendar.from_ical(data)
    matches = [
        match
        for match in (parse_match(event) for event in calendar.walk("VEVENT"))
        if match is not None
    ]
    far_future = datetime.max.replace(tzinfo=timezone.utc)
    return sorted(
        matches,
        key=lambda match: (match.start or far_future, match.team1, match.team2),
    )


def score_matrix(matches: list[MatchRow]) -> tuple[list[str], list[list[int]]]:
    """Maps won by each row team against each column team."""
    totals: dict[tuple[str, str], int] = {}
    teams: set[str] = set()
    for match in matches:
        if match.score1 is None or match.score2 is None:
            continue
        if match.score1 == 0 and match.score2 == 0:
            continue  # not played yet in the older calendars
        teams.update((match.team1, match.team2))
        totals[(match.team1, match.team2)] = (
            totals.get((match.team1, match.team2), 0) + match.score1
        )
        totals[(match.team2, match.team1)] = (
            totals.get((match.team2, match.team1), 0) + match.score2
        )

    ordered = sorted(teams, key=str.casefold)
    matrix = [[totals.get((row, column), 0) for column in ordered] for row in ordered]
    return ordered, matrix
