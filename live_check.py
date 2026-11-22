"""Decide whether a match is on right now, without touching the network.

The hourly workflow runs this against the committed cache and only starts a
full calendar update while a match is about to start or still in progress.
Standard library only, so the workflow needs no dependency install.

Exit status: 0 when an update is worth running, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parent / "data" / "matches.json"

# Start polling shortly before the scheduled start (times move, teams get
# confirmed) and keep going long enough to cover a delayed best-of-five.
LEAD_TIME = timedelta(minutes=90)
MAX_MATCH_LENGTH = timedelta(hours=12)


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def active_matches(
    records: dict[str, dict[str, Any]],
    now: datetime,
) -> list[dict[str, Any]]:
    """Matches that are not finished and are inside the polling window."""
    active = []
    for record in records.values():
        if str(record.get("status", "")).lower() == "completed":
            continue
        start = parse_utc(record["start_utc"])
        if start - LEAD_TIME <= now <= start + MAX_MATCH_LENGTH:
            active.append(record)
    return sorted(active, key=lambda record: record["start_utc"])


def main() -> int:
    if not DATA_PATH.exists():
        print("没有比赛缓存，不需要加密更新")
        return 1
    records = json.loads(DATA_PATH.read_text(encoding="utf-8")).get("events", {})
    now = datetime.now(timezone.utc)
    active = active_matches(records, now)
    if not active:
        print(f"当前没有进行中或即将开始的比赛（共 {len(records)} 场已知比赛）")
        return 1
    for record in active:
        print(
            f"{record['start_utc']} [{record['region']}] "
            f"{record['team1']} vs {record['team2']} ({record['status']})"
        )
    print(f"有 {len(active)} 场比赛在更新窗口内，需要更新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
