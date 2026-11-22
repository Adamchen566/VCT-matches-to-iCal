from __future__ import annotations

import argparse
import json
import re
import time
import tomllib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "events.toml"
DATA_PATH = ROOT / "data" / "matches.json"
ICS_PATH = ROOT / "vct_OnGoing.ics"
TEXT_PATH = ROOT / "vct_OnGoing.txt"

VLR_BASE_URL = "https://www.vlr.gg"
USER_AGENT = (
    "VCTCalendar/3.0 "
    "(+https://github.com/Adamchen566/VCT-matches-to-iCal)"
)
REQUEST_TIMEOUT = (10, 30)
REQUEST_ATTEMPTS = 3
VLR_DETAIL_TIMEZONE = ZoneInfo("America/Havana")
UTC = timezone.utc
CACHE_SCHEMA_VERSION = 3

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


@dataclass(frozen=True)
class EventConfig:
    region: str
    event_id: int
    slug: str
    name: str
    min_matches: int = 0

    @property
    def matches_url(self) -> str:
        return (
            f"{VLR_BASE_URL}/event/matches/{self.event_id}/"
            f"{self.slug}/?group=all&series_id=all"
        )

    @property
    def ical_url(self) -> str:
        return f"{VLR_BASE_URL}/event/ical/{self.event_id}"


@dataclass(frozen=True)
class CalendarConfig:
    name: str
    display_timezone: ZoneInfo
    events: tuple[EventConfig, ...]

    @property
    def event_ids(self) -> set[int]:
        return {event.event_id for event in self.events}


def parse_config(data: dict[str, Any]) -> CalendarConfig:
    calendar = data.get("calendar")
    if not isinstance(calendar, dict) or not calendar.get("name"):
        raise CalendarUpdateError("配置缺少 [calendar] name")

    timezone_name = calendar.get("display_timezone", "Australia/Sydney")
    try:
        display_timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise CalendarUpdateError(
            f"配置里的 display_timezone 无效: {timezone_name}"
        ) from exc

    raw_events = data.get("events")
    if not isinstance(raw_events, list) or not raw_events:
        raise CalendarUpdateError("配置里至少要有一个 [[events]]")

    events: list[EventConfig] = []
    for index, raw in enumerate(raw_events, start=1):
        missing = [
            key
            for key in ("region", "event_id", "slug", "name")
            if not raw.get(key)
        ]
        if missing:
            raise CalendarUpdateError(
                f"第 {index} 个 [[events]] 缺少字段: {', '.join(missing)}"
            )
        if not isinstance(raw["event_id"], int):
            raise CalendarUpdateError(
                f"第 {index} 个 [[events]] 的 event_id 必须是整数"
            )
        min_matches = raw.get("min_matches", 0)
        if not isinstance(min_matches, int) or min_matches < 0:
            raise CalendarUpdateError(
                f"第 {index} 个 [[events]] 的 min_matches 必须是非负整数"
            )
        events.append(
            EventConfig(
                region=str(raw["region"]),
                event_id=raw["event_id"],
                slug=str(raw["slug"]),
                name=str(raw["name"]),
                min_matches=min_matches,
            )
        )

    event_ids = [event.event_id for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise CalendarUpdateError("配置里出现重复的 event_id")

    return CalendarConfig(
        name=str(calendar["name"]),
        display_timezone=display_timezone,
        events=tuple(events),
    )


def load_config(path: Path = CONFIG_PATH) -> CalendarConfig:
    if not path.exists():
        raise CalendarUpdateError(f"找不到赛事配置文件: {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise CalendarUpdateError(f"赛事配置文件格式错误: {exc}") from exc
    return parse_config(data)


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


def parse_score(value: str) -> int | None:
    value = value.strip()
    return int(value) if value.isdigit() else None


def parse_event_html(html: str, event: EventConfig) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    matches: list[dict[str, Any]] = []

    for item in soup.select("a.wf-module-item.match-item[href]"):
        href = item.get("href", "")
        match_url = urljoin(VLR_BASE_URL, href)
        match_id = match_id_from_url(match_url)

        team_nodes = item.select(".match-item-vs-team-name")
        if len(team_nodes) != 2:
            raise CalendarUpdateError(
                f"{event.name} 比赛 {match_id} 的队伍数量不是 2"
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
                "event_id": event.event_id,
                "event_name": event.name,
                "region": event.region,
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

    ids = [match["match_id"] for match in matches]
    if len(ids) != len(set(ids)):
        raise CalendarUpdateError(f"{event.name} 出现重复的 VLR match ID")
    return matches


def check_match_count(
    event: EventConfig,
    scraped: int,
    cached: int,
    *,
    allow_shrink: bool = False,
) -> None:
    """Refuse to publish when a scrape looks incomplete."""
    if scraped < event.min_matches:
        raise CalendarUpdateError(
            f"{event.name} 只抓到 {scraped} 场，少于配置的 "
            f"min_matches={event.min_matches}，拒绝覆盖现有日历"
        )
    if scraped < cached and not allow_shrink:
        raise CalendarUpdateError(
            f"{event.name} 只抓到 {scraped} 场，少于上次已发布的 "
            f"{cached} 场，拒绝覆盖现有日历"
            "（确认是 VLR 真的删了比赛时，加 --allow-shrink 重跑）"
        )


def parse_event_page(event: EventConfig) -> list[dict[str, Any]]:
    matches = parse_event_html(str(get_url(event.matches_url)), event)
    print(f"{event.name}: 赛事页抓到 {len(matches)} 场")
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
    event: EventConfig,
) -> dict[str, dict[str, Any]]:
    payload = get_url(event.ical_url, binary=True)
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

    print(f"{event.name}: VLR 官方 ICS 提供 {len(result)} 场未来比赛时间")
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


def load_cache(path: Path | None = None) -> dict[str, dict[str, Any]]:
    path = path or DATA_PATH
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != CACHE_SCHEMA_VERSION:
        print(
            f"缓存 schema {data.get('schema_version')} 已过期，"
            "将重新读取历史比赛时间"
        )
        return {}
    if not isinstance(data.get("events"), dict):
        raise CalendarUpdateError(f"缓存格式不受支持: {path}")
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


def build_calendar(
    events: dict[str, dict[str, Any]],
    config: CalendarConfig,
) -> bytes:
    calendar = Calendar()
    calendar.add("PRODID", "-//VCT Calendar//Adamchen566//EN")
    calendar.add("VERSION", "2.0")
    calendar.add("CALSCALE", "GREGORIAN")
    calendar.add("METHOD", "PUBLISH")
    calendar.add("X-WR-CALNAME", config.name)
    calendar.add("X-WR-TIMEZONE", config.display_timezone.key)
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
        event.add("CATEGORIES", [record["event_name"], record["region"]])
        calendar.add_component(event)

    return calendar.to_ical()


def build_text(
    events: dict[str, dict[str, Any]],
    config: CalendarConfig,
) -> str:
    lines = [
        config.name,
        f"Timezone: {config.display_timezone.key}",
        "",
    ]
    if not events:
        lines.append("VLR 尚未公布这些赛事的赛程，公布后会自动出现在这里。")
    for record in sorted_records(events):
        local_time = parse_utc(record["start_utc"]).astimezone(
            config.display_timezone
        )
        lines.append(
            f"{local_time:%Y-%m-%d %H:%M %Z} | "
            f"{record['region']:<4} | "
            f"{record['team1']} vs {record['team2']} | "
            f"{score_text(record):<5} | "
            f"{record['status']} | {record['url']}"
        )
    return "\n".join(lines) + "\n"


def build_cache_json(
    events: dict[str, dict[str, Any]],
    config: CalendarConfig,
) -> str:
    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "calendar": config.name,
        "events": events,
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def validate_records(
    events: dict[str, dict[str, Any]],
    config: CalendarConfig,
) -> None:
    counts = Counter()
    for record in events.values():
        event_id = record.get("event_id")
        if event_id not in config.event_ids:
            raise CalendarUpdateError(
                f"缓存里有不在配置中的赛事 event_id={event_id}，"
                "请重新运行更新"
            )
        counts[event_id] += 1
        parse_utc(record["start_utc"])
        parse_utc(record["end_utc"])
        parse_utc(record["updated_at"])

    for event in config.events:
        if counts[event.event_id] < event.min_matches:
            raise CalendarUpdateError(
                f"{event.name} 只有 {counts[event.event_id]} 场，少于配置的 "
                f"min_matches={event.min_matches}"
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


def run_update(config: CalendarConfig, *, allow_shrink: bool = False) -> None:
    cache = load_cache()
    cached_counts = Counter(record.get("event_id") for record in cache.values())
    all_matches: list[dict[str, Any]] = []
    official_times: dict[str, dict[str, Any]] = {}

    for event in config.events:
        matches = parse_event_page(event)
        check_match_count(
            event,
            len(matches),
            cached_counts[event.event_id],
            allow_shrink=allow_shrink,
        )
        all_matches.extend(matches)
        official_times.update(fetch_official_upcoming_times(event))

    all_ids = [match["match_id"] for match in all_matches]
    if len(all_ids) != len(set(all_ids)):
        raise CalendarUpdateError("不同赛事之间出现重复 VLR match ID")

    resolve_match_timings(all_matches, official_times, cache)
    events = merge_with_cache(all_matches, cache)
    validate_records(events, config)

    ical_bytes = build_calendar(events, config)
    validate_calendar(ical_bytes, events)

    changes = {
        str(ICS_PATH.relative_to(ROOT)): write_if_changed(ICS_PATH, ical_bytes),
        str(TEXT_PATH.relative_to(ROOT)): write_if_changed(
            TEXT_PATH, build_text(events, config)
        ),
        str(DATA_PATH.relative_to(ROOT)): write_if_changed(
            DATA_PATH, build_cache_json(events, config)
        ),
    }

    counts = Counter(record["event_id"] for record in events.values())
    print(
        "更新完成: "
        + ", ".join(
            f"{event.region}={counts[event.event_id]}" for event in config.events
        )
        + f", total={len(events)}"
    )
    for path, changed in changes.items():
        print(f"{path}: {'updated' if changed else 'unchanged'}")


def check_existing_outputs(config: CalendarConfig) -> None:
    if not DATA_PATH.exists() or not ICS_PATH.exists() or not TEXT_PATH.exists():
        raise CalendarUpdateError("日历、文本或缓存文件不存在")
    events = load_cache()
    validate_records(events, config)
    validate_calendar(ICS_PATH.read_bytes(), events)
    print(f"本地输出验证通过，共 {len(events)} 场比赛")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="按 events.toml 更新 VCT 订阅日历"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="只验证现有输出，不访问 VLR",
    )
    parser.add_argument(
        "--allow-shrink",
        action="store_true",
        help="允许某个赛事的场次比上次发布的少（VLR 确实删除比赛时使用）",
    )
    args = parser.parse_args()

    try:
        config = load_config()
        if args.check:
            check_existing_outputs(config)
        else:
            run_update(config, allow_shrink=args.allow_shrink)
    except (CalendarUpdateError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
