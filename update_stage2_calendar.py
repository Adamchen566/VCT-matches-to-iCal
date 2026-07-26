from __future__ import annotations

import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "vct_stage2_matches.json"
ICS_PATH = ROOT / "vct_OnGoing.ics"
TEXT_PATH = ROOT / "vct_OnGoing.txt"

VLR_BASE_URL = "https://www.vlr.gg"
USER_AGENT = (
    "VCTCalendar/2.0 "
    "(+https://github.com/Adamchen566/VCT-matches-to-iCal)"
)
REQUEST_TIMEOUT = (10, 30)
REQUEST_ATTEMPTS = 3
DISPLAY_TIMEZONE = ZoneInfo("Australia/Sydney")
VLR_DETAIL_TIMEZONE = ZoneInfo("America/Havana")
UTC = timezone.utc
CACHE_SCHEMA_VERSION = 2

STAGE_2_EVENTS = {
    "AMER": {
        "event_id": 2977,
        "name": "VCT 2026: Americas Stage 2",
        "slug": "vct-2026-americas-stage-2",
        "expected_matches": 30,
    },
    "PAC": {
        "event_id": 2776,
        "name": "VCT 2026: Pacific Stage 2",
        "slug": "vct-2026-pacific-stage-2",
        "expected_matches": 30,
    },
    "EMEA": {
        "event_id": 2976,
        "name": "VCT 2026: EMEA Stage 2",
        "slug": "vct-2026-emea-stage-2",
        "expected_matches": 30,
    },
    "CN": {
        "event_id": 2978,
        "name": "VCT 2026: China Stage 2",
        "slug": "vct-2026-china-stage-2",
        "expected_matches": 36,
    },
}

SEMANTIC_FIELDS = (
    "match_id",
    "event_id",
    "event_name",
    "region",
    "url",
    "team1",
    "team2",
    "score1",
    "score2",
    "status",
    "phase",
    "best_of",
    "start_utc",
    "end_utc",
)


class CalendarUpdateError(RuntimeError):
    """Raised when a complete and valid calendar cannot be produced."""


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def parse_vlr_detail_timestamp(value: str) -> datetime:
    # VLR's data-utc-ts attribute is historically named but is expressed in
    # America/Havana local time. Convert it explicitly so GitHub runner
    # location and daylight-saving transitions cannot shift match times.
    local_time = datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=VLR_DETAIL_TIMEZONE
    )
    return local_time.astimezone(UTC)


def get_url(url: str, *, binary: bool = False) -> bytes | str:
    last_error: Exception | None = None
    for attempt in range(1, REQUEST_ATTEMPTS + 1):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.content if binary else response.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt < REQUEST_ATTEMPTS:
                time.sleep(attempt * 1.5)
    raise CalendarUpdateError(f"无法获取 {url}: {last_error}")


def match_id_from_url(url: str) -> str:
    match = re.search(r"/(\d+)/", url)
    if not match:
        raise CalendarUpdateError(f"无法从 URL 提取 VLR match ID: {url}")
    return match.group(1)


def event_matches_url(config: dict[str, Any]) -> str:
    return (
        f"{VLR_BASE_URL}/event/matches/{config['event_id']}/"
        f"{config['slug']}/?group=all&series_id=all"
    )


def parse_score(value: str) -> int | None:
    value = value.strip()
    return int(value) if value.isdigit() else None


def parse_event_page(region: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    url = event_matches_url(config)
    html = str(get_url(url))
    soup = BeautifulSoup(html, "html.parser")
    matches: list[dict[str, Any]] = []

    for item in soup.select("a.wf-module-item.match-item[href]"):
        href = item.get("href", "")
        match_url = urljoin(VLR_BASE_URL, href)
        match_id = match_id_from_url(match_url)

        team_nodes = item.select(".match-item-vs-team-name")
        if len(team_nodes) != 2:
            raise CalendarUpdateError(
                f"{region} 比赛 {match_id} 的队伍数量不是 2"
            )
        team1, team2 = [
            node.get_text(" ", strip=True) or "TBD" for node in team_nodes
        ]

        score_nodes = item.select(".match-item-vs-team-score")
        score1 = (
            parse_score(score_nodes[0].get_text(strip=True))
            if len(score_nodes) > 0
            else None
        )
        score2 = (
            parse_score(score_nodes[1].get_text(strip=True))
            if len(score_nodes) > 1
            else None
        )

        status_node = item.select_one(".ml-status")
        status = status_node.get_text(" ", strip=True) if status_node else "Unknown"

        phase_node = item.select_one(".match-item-event")
        phase = phase_node.get_text(" ", strip=True) if phase_node else ""

        matches.append(
            {
                "match_id": match_id,
                "event_id": config["event_id"],
                "event_name": config["name"],
                "region": region,
                "url": match_url,
                "team1": team1,
                "team2": team2,
                "score1": score1,
                "score2": score2,
                "status": status,
                "phase": phase,
                "best_of": None,
                "start_utc": None,
                "end_utc": None,
            }
        )

    expected_matches = int(config["expected_matches"])
    if len(matches) < expected_matches:
        raise CalendarUpdateError(
            f"{region} 只抓到 {len(matches)} 场，少于已确认的 "
            f"{expected_matches} 场，拒绝覆盖现有日历"
        )

    ids = [match["match_id"] for match in matches]
    if len(ids) != len(set(ids)):
        raise CalendarUpdateError(f"{region} 出现重复的 VLR match ID")

    print(f"{region}: 赛事页抓到 {len(matches)} 场")
    return matches


def decoded_datetime(component: Event, key: str) -> datetime | None:
    value = component.get(key)
    if value is None:
        return None
    decoded = component.decoded(key)
    if not isinstance(decoded, datetime):
        return None
    if decoded.tzinfo is None:
        decoded = decoded.replace(tzinfo=UTC)
    return decoded.astimezone(UTC)


def fetch_official_upcoming_times(
    config: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    url = f"{VLR_BASE_URL}/event/ical/{config['event_id']}"
    payload = get_url(url, binary=True)
    calendar = Calendar.from_ical(payload)
    result: dict[str, dict[str, Any]] = {}

    for component in calendar.walk("VEVENT"):
        event_url = str(component.get("URL") or component.get("DESCRIPTION") or "")
        if not event_url:
            continue
        match_id = match_id_from_url(event_url)
        start = decoded_datetime(component, "DTSTART")
        end = decoded_datetime(component, "DTEND")
        if start is None:
            continue
        if end is None:
            end = start + timedelta(hours=3)
        result[match_id] = {
            "start_utc": format_utc(start),
            "end_utc": format_utc(end),
        }

    print(
        f"{config['name']}: VLR 官方 ICS 提供 "
        f"{len(result)} 场未来比赛时间"
    )
    return result


def fetch_match_detail_timing(match_url: str) -> dict[str, Any]:
    html = str(get_url(match_url))
    soup = BeautifulSoup(html, "html.parser")
    timestamp_node = soup.find(attrs={"data-utc-ts": True})
    if timestamp_node is None:
        raise CalendarUpdateError(f"比赛详情页没有 UTC 时间戳: {match_url}")

    raw_timestamp = str(timestamp_node["data-utc-ts"])
    start = parse_vlr_detail_timestamp(raw_timestamp)

    note_node = soup.select_one(".match-header-vs-note")
    note = note_node.get_text(" ", strip=True) if note_node else ""
    best_of_match = re.search(r"\bBo(\d+)\b", note, re.IGNORECASE)
    best_of = int(best_of_match.group(1)) if best_of_match else None

    duration = timedelta(hours=5 if best_of == 5 else 3)
    return {
        "start_utc": format_utc(start),
        "end_utc": format_utc(start + duration),
        "best_of": best_of,
    }


def load_cache() -> dict[str, dict[str, Any]]:
    if not DATA_PATH.exists():
        return {}
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    if data.get("schema_version") != CACHE_SCHEMA_VERSION:
        print(
            f"缓存 schema {data.get('schema_version')} 已过期，"
            "将重新读取历史比赛时间"
        )
        return {}
    if not isinstance(data.get("events"), dict):
        raise CalendarUpdateError(f"缓存格式不受支持: {DATA_PATH}")
    return data["events"]


def resolve_match_timings(
    matches: list[dict[str, Any]],
    official_times: dict[str, dict[str, Any]],
    cache: dict[str, dict[str, Any]],
) -> None:
    detail_targets: dict[str, dict[str, Any]] = {}

    for match in matches:
        match_id = match["match_id"]
        previous = cache.get(match_id)
        official = official_times.get(match_id)

        if official:
            match.update(official)
            if previous:
                match["best_of"] = previous.get("best_of")
            continue

        if previous and previous.get("start_utc") and match["status"].lower() == "completed":
            match["start_utc"] = previous["start_utc"]
            match["end_utc"] = previous["end_utc"]
            match["best_of"] = previous.get("best_of")
            continue

        detail_targets[match_id] = match

    if detail_targets:
        print(f"需要从比赛详情页补充 {len(detail_targets)} 场 UTC 时间")
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_id = {
                executor.submit(fetch_match_detail_timing, match["url"]): match_id
                for match_id, match in detail_targets.items()
            }
            for future in as_completed(future_to_id):
                match_id = future_to_id[future]
                detail_targets[match_id].update(future.result())

    unresolved = [
        match["match_id"]
        for match in matches
        if not match.get("start_utc") or not match.get("end_utc")
    ]
    if unresolved:
        raise CalendarUpdateError(
            "以下比赛缺少 UTC 时间，拒绝发布: " + ", ".join(unresolved)
        )


def merge_with_cache(
    matches: list[dict[str, Any]],
    cache: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    now = format_utc(utc_now())
    merged: dict[str, dict[str, Any]] = {}

    for match in matches:
        match_id = match["match_id"]
        previous = cache.get(match_id)
        record = {key: match.get(key) for key in SEMANTIC_FIELDS}
        changed = previous is None or any(
            previous.get(key) != record.get(key) for key in SEMANTIC_FIELDS
        )

        if previous is None:
            sequence = 0
            updated_at = now
        elif changed:
            sequence = int(previous.get("sequence", 0)) + 1
            updated_at = now
        else:
            sequence = int(previous.get("sequence", 0))
            updated_at = previous["updated_at"]

        record["sequence"] = sequence
        record["updated_at"] = updated_at
        merged[match_id] = record

    return dict(sorted(merged.items(), key=lambda item: int(item[0])))


def sorted_records(events: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        events.values(),
        key=lambda event: (
            parse_utc(event["start_utc"]),
            event["region"],
            int(event["match_id"]),
        ),
    )


def score_text(record: dict[str, Any]) -> str:
    if record.get("score1") is None or record.get("score2") is None:
        return "TBD"
    return f"{record['score1']}:{record['score2']}"


def ics_description_text(value: Any) -> str:
    """Keep visible spacing without creating Git trailing-space false positives."""
    return str(value).replace(" ", "\N{NO-BREAK SPACE}")


def build_calendar(events: dict[str, dict[str, Any]]) -> bytes:
    calendar = Calendar()
    calendar.add("PRODID", "-//VCT Stage 2 Calendar//Adamchen566//EN")
    calendar.add("VERSION", "2.0")
    calendar.add("CALSCALE", "GREGORIAN")
    calendar.add("METHOD", "PUBLISH")
    calendar.add("X-WR-CALNAME", "VCT 2026 Stage 2 - AMER PAC EMEA CN")
    calendar.add("X-WR-TIMEZONE", "Australia/Sydney")
    calendar.add("X-PUBLISHED-TTL", "PT24H")

    for record in sorted_records(events):
        event = Event()
        updated_at = parse_utc(record["updated_at"])
        start = parse_utc(record["start_utc"])
        end = parse_utc(record["end_utc"])

        event.add("UID", f"vlr-{record['match_id']}@vct-calendar")
        event.add("DTSTAMP", updated_at)
        event.add("LAST-MODIFIED", updated_at)
        event.add("SEQUENCE", int(record["sequence"]))
        event.add("DTSTART", start)
        event.add("DTEND", end)
        event.add(
            "SUMMARY",
            f"[{record['region']}] {record['team1']} vs {record['team2']}",
        )
        event.add("LOCATION", f"VCT {record['region']}")
        event.add(
            "DESCRIPTION",
            "\n".join(
                [
                    ics_description_text(record["event_name"]),
                    f"状态：{ics_description_text(record['status'] or '待定')}",
                    f"阶段：{ics_description_text(record['phase'] or '待定')}",
                    f"比分：{score_text(record)}",
                    f"VLR：{record['url']}",
                ]
            ),
        )
        event.add("URL", record["url"])
        event.add("STATUS", "CONFIRMED")
        event.add("TRANSP", "TRANSPARENT")
        event.add(
            "CATEGORIES",
            ["VCT 2026", "Stage 2", record["region"]],
        )
        calendar.add_component(event)

    return calendar.to_ical()


def build_text(events: dict[str, dict[str, Any]]) -> str:
    lines = [
        "VCT 2026 Stage 2 | AMER + PAC + EMEA + CN",
        "Timezone: Australia/Sydney",
        "",
    ]
    for record in sorted_records(events):
        local_time = parse_utc(record["start_utc"]).astimezone(DISPLAY_TIMEZONE)
        lines.append(
            f"{local_time:%Y-%m-%d %H:%M %Z} | "
            f"{record['region']:<4} | "
            f"{record['team1']} vs {record['team2']} | "
            f"{score_text(record):<5} | "
            f"{record['status']} | {record['url']}"
        )
    return "\n".join(lines) + "\n"


def build_cache_json(events: dict[str, dict[str, Any]]) -> str:
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "calendar": "VCT 2026 Stage 2 - AMER PAC EMEA CN",
        "events": events,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def validate_records(events: dict[str, dict[str, Any]]) -> None:
    counts = {region: 0 for region in STAGE_2_EVENTS}
    for record in events.values():
        region = record.get("region")
        if region not in counts:
            raise CalendarUpdateError(f"未知赛区: {region}")
        counts[region] += 1
        parse_utc(record["start_utc"])
        parse_utc(record["end_utc"])
        parse_utc(record["updated_at"])

    for region, count in counts.items():
        expected_matches = int(STAGE_2_EVENTS[region]["expected_matches"])
        if count < expected_matches:
            raise CalendarUpdateError(
                f"{region} 只有 {count} 场，少于已确认的 "
                f"{expected_matches} 场"
            )


def validate_calendar(ical_bytes: bytes, events: dict[str, dict[str, Any]]) -> None:
    calendar = Calendar.from_ical(ical_bytes)
    calendar_events = list(calendar.walk("VEVENT"))
    if len(calendar_events) != len(events):
        raise CalendarUpdateError(
            f"ICS 有 {len(calendar_events)} 场，缓存有 {len(events)} 场"
        )

    uids = [str(event.get("UID")) for event in calendar_events]
    if len(uids) != len(set(uids)):
        raise CalendarUpdateError("ICS 中存在重复 UID")

    expected_uids = {
        f"vlr-{match_id}@vct-calendar" for match_id in events
    }
    if set(uids) != expected_uids:
        raise CalendarUpdateError("ICS UID 与缓存中的 VLR match ID 不一致")


def write_if_changed(path: Path, content: bytes | str) -> bool:
    data = content.encode("utf-8") if isinstance(content, str) else content
    if path.exists() and path.read_bytes() == data:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)
    return True


def run_update() -> None:
    cache = load_cache()
    all_matches: list[dict[str, Any]] = []
    official_times: dict[str, dict[str, Any]] = {}

    for region, config in STAGE_2_EVENTS.items():
        all_matches.extend(parse_event_page(region, config))
        official_times.update(fetch_official_upcoming_times(config))

    all_ids = [match["match_id"] for match in all_matches]
    if len(all_ids) != len(set(all_ids)):
        raise CalendarUpdateError("四个赛区之间出现重复 VLR match ID")

    resolve_match_timings(all_matches, official_times, cache)
    events = merge_with_cache(all_matches, cache)
    validate_records(events)

    ical_bytes = build_calendar(events)
    validate_calendar(ical_bytes, events)

    changes = {
        str(ICS_PATH.relative_to(ROOT)): write_if_changed(ICS_PATH, ical_bytes),
        str(TEXT_PATH.relative_to(ROOT)): write_if_changed(
            TEXT_PATH, build_text(events)
        ),
        str(DATA_PATH.relative_to(ROOT)): write_if_changed(
            DATA_PATH, build_cache_json(events)
        ),
    }

    region_counts = {
        region: sum(
            record["region"] == region for record in events.values()
        )
        for region in STAGE_2_EVENTS
    }
    print(
        "更新完成: "
        + ", ".join(f"{region}={count}" for region, count in region_counts.items())
        + f", total={len(events)}"
    )
    for path, changed in changes.items():
        print(f"{path}: {'updated' if changed else 'unchanged'}")


def check_existing_outputs() -> None:
    if not DATA_PATH.exists() or not ICS_PATH.exists() or not TEXT_PATH.exists():
        raise CalendarUpdateError("日历、文本或缓存文件不存在")
    events = load_cache()
    validate_records(events)
    validate_calendar(ICS_PATH.read_bytes(), events)
    print(f"本地输出验证通过，共 {len(events)} 场比赛")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="更新 VCT 2026 Stage 2 四赛区合并日历"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只验证现有输出，不访问 VLR",
    )
    args = parser.parse_args()

    try:
        if args.check:
            check_existing_outputs()
        else:
            run_update()
    except (CalendarUpdateError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
