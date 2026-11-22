"""Collect VCT match statistics from VLR.gg into CSV tables.

Three steps, each restartable:

    python vlr_stats.py events    # which events exist  -> data/stats/events.csv
    python vlr_stats.py crawl     # download match pages -> .cache/vlr/ (not committed)
    python vlr_stats.py build     # parse the cache      -> data/stats/<year>/*.csv
    python vlr_stats.py check     # how complete the tables are

Pages are downloaded once and kept compressed, so the tables can be rebuilt
after a parser fix without asking VLR for anything again.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from bs4 import BeautifulSoup

import update_calendar as uc

ROOT = Path(__file__).resolve().parent
STATS_DIR = ROOT / "data" / "stats"
CACHE_DIR = ROOT / ".cache" / "vlr"
FIRST_YEAR = 2021
REQUEST_DELAY = 1.0  # seconds between requests; one request at a time
MAX_CONSECUTIVE_FAILURES = 5
REGULATION_ROUNDS = 24  # the economy tab draws no overtime rounds

TABS = {
    "overview": "",
    "performance": "?game=all&tab=performance",
    "economy": "?game=all&tab=economy",
}
TIERS = ("international", "league", "qualifier", "challengers")

LEAGUE_SLUG = re.compile(
    r"^(?:vct|champions-tour)-\d{4}-(americas|pacific|emea|china)-"
    r"(?:league|kickoff|stage-\d)$"
)
INTERNATIONAL_SLUG = re.compile(
    r"^valorant-champions-tour-stage-\d-masters-|^champions-tour-\d{4}-masters-"
    r"|^valorant-masters-|^valorant-champions-\d{4}$|lock-in"
)
REGION_KEYWORDS = (
    ("AMER", ("americas", "north-america", "brazil", "latam", "latin-america",
              "south-america")),
    ("EMEA", ("emea", "europe", "turkey", "cis", "arabia")),
    ("CN", ("china",)),
    ("PAC", ("pacific", "korea", "japan", "sea-", "east-asia", "malaysia",
             "indonesia", "thailand", "philippines", "vietnam", "hong-kong",
             "oceania", "skyesports", "conquerors")),
)

# Column name in the CSV -> data-col attribute on the page. Every one of
# these comes in three flavours: whole map, attack half, defence half.
SIDED_STATS = (
    ("rating", "rating2"),
    ("acs", "acs"),
    ("kills", "kills"),
    ("deaths", "deaths"),
    ("assists", "assists"),
    ("kast", "kast"),
    ("adr", "adr"),
    ("hs", "hsp"),
    ("fk", "fb"),
    ("fd", "fd"),
)
SIDES = (("", "mod-both"), ("_atk", "mod-t"), ("_def", "mod-ct"))
ADVANCED_STATS = (
    "k2", "k3", "k4", "k5",
    "clutch_1v1", "clutch_1v2", "clutch_1v3", "clutch_1v4", "clutch_1v5",
    "econ", "plants", "defuses",
)
BUY_TYPES = {"mod-bp": "pistol", "mod-b1": "eco", "mod-b2": "half", "mod-b3": "full"}
WIN_TYPES = {"elim": "elimination", "defuse": "defuse", "boom": "detonation",
             "time": "time"}

EVENT_FIELDS = ("event_id", "year", "tier", "region", "name", "slug", "status")
MATCH_FIELDS = (
    "match_id", "event_id", "series", "start_utc", "patch", "best_of",
    "team1_id", "team1", "team1_tag", "team2_id", "team2", "team2_tag",
    "score1", "score2", "winner", "url",
)
VETO_FIELDS = ("match_id", "step", "team", "team_tag", "action", "map")
MAP_FIELDS = (
    "game_id", "match_id", "map_no", "map", "picked_by", "duration",
    "score1", "score2", "winner",
    "team1_atk", "team1_def", "team1_ot", "team2_atk", "team2_def", "team2_ot",
    "team1_comp", "team2_comp",
)
ROUND_FIELDS = (
    "game_id", "round", "winner", "winner_side", "win_type",
    "team1_buy", "team2_buy", "team1_loadout", "team2_loadout",
    "team1_bank", "team2_bank",
)
PLAYER_FIELDS = (
    ("game_id", "match_id", "team", "team_id", "team_tag", "player_id",
     "player", "country", "agent")
    + tuple(f"{name}{suffix}" for name, _ in SIDED_STATS for suffix, _ in SIDES)
    + ADVANCED_STATS
)
TEAM_FIELDS = ("team_id", "name", "tag", "other_names", "first_match",
               "last_match", "matches", "maps", "map_wins")
PLAYER_INDEX_FIELDS = ("player_id", "name", "country", "other_names", "teams",
                       "first_match", "last_match", "maps", "top_agents")


class StatsError(RuntimeError):
    """Raised when a page cannot be understood."""


# ---------------------------------------------------------------- events


def classify_event(slug: str) -> str:
    if "qualifier" in slug:
        return "qualifier"
    if LEAGUE_SLUG.match(slug):
        return "league"
    if INTERNATIONAL_SLUG.search(slug):
        return "international"
    return "challengers"


def event_region(slug: str, tier: str) -> str:
    if tier == "international":
        return uc.INTERNATIONAL_REGION
    for region, keywords in REGION_KEYWORDS:
        if any(keyword in slug for keyword in keywords):
            return region
    return ""


def parse_year_page(html: str, year: int) -> list[dict[str, Any]]:
    events = []
    for event_id, info in sorted(uc.parse_events_list(html).items()):
        tier = classify_event(info["slug"])
        events.append(
            {
                "event_id": event_id,
                "year": year,
                "tier": tier,
                "region": event_region(info["slug"], tier),
                "name": info["name"],
                "slug": info["slug"],
                "status": info["status"],
            }
        )
    return events


# ----------------------------------------------------------------- cache


def cache_path(kind: str, name: str) -> Path:
    return CACHE_DIR / kind / f"{name}.html.gz"


def read_cache(path: Path) -> str | None:
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return handle.read()


def write_cache(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        handle.write(html)
    temporary.replace(path)


def download(path: Path, url: str, *, refresh: bool = False,
             must_contain: str = "") -> str:
    """Return a page from the cache, fetching it politely when missing."""
    if not refresh:
        cached = read_cache(path)
        if cached is not None:
            return cached
    html = uc.get_url(url)
    time.sleep(REQUEST_DELAY)
    if must_contain and must_contain not in html:
        raise StatsError(f"{url} 返回的页面不含 {must_contain!r}")
    write_cache(path, html)
    return html


# --------------------------------------------------------------- parsing


def clean(node: Any) -> str:
    if node is None:
        return ""
    return " ".join(node.get_text(" ", strip=True).split())


def figure(value: str) -> str:
    """Normalise a stat as printed on the page: '71%' -> '71', '+3' -> '3'."""
    value = value.replace("\xa0", " ").strip().rstrip("%").lstrip("+")
    return "" if value in {"", "-", "–"} else value


def thousands(value: str) -> str:
    """'LOUD 3.9k' -> '3900'."""
    match = re.search(r"(\d+(?:\.\d+)?)k\s*$", value.strip())
    return str(round(float(match.group(1)) * 1000)) if match else ""


def id_from_href(node: Any, kind: str) -> str:
    match = re.search(rf"/{kind}/(\d+)", node.get("href", "")) if node else None
    return match.group(1) if match else ""


def parse_event_listing(html: str) -> list[dict[str, str]]:
    """Matches on an event's match list: id, path and status."""
    soup = BeautifulSoup(html, "html.parser")
    matches = []
    for item in soup.select("a.wf-module-item.match-item[href]"):
        href = item["href"]
        found = re.match(r"^/(\d+)/", href)
        if not found:
            continue
        matches.append(
            {
                "match_id": found.group(1),
                "path": href,
                "status": clean(item.select_one(".ml-status")),
            }
        )
    return matches


def played_games(soup: BeautifulSoup) -> list[Any]:
    games = []
    for game in soup.select(".vm-stats-game"):
        if (game.get("data-game-id") or "").isdigit():
            games.append(game)
    return games


def parse_overview(html: str, match_id: str, url: str = "") -> dict[str, Any]:
    """Everything on a match's overview tab.

    Returns {"match": {...}, "vetoes": [...], "maps": [...], "rounds": [...],
    "players": [...]}. Maps that were never played are left out.
    """
    soup = BeautifulSoup(html, "html.parser")
    header = soup.select_one(".match-header")
    if header is None:
        raise StatsError(f"比赛 {match_id} 的页面没有 match-header")

    event_link = header.select_one("a.match-header-event")
    time_node = header.select_one(".match-header-date [data-utc-ts]")
    start_utc = ""
    if time_node is not None and time_node.get("data-utc-ts"):
        start_utc = uc.format_utc(
            uc.parse_vlr_detail_timestamp(time_node["data-utc-ts"])
        )
    patch = re.search(r"Patch\s+([\d.]+)", clean(header.select_one(".match-header-date")))
    notes = " ".join(clean(node) for node in header.select(".match-header-vs-note"))
    best_of = re.search(r"\bBo(\d)\b", notes, re.IGNORECASE)

    teams = []
    for number in (1, 2):
        link = header.select_one(f"a.match-header-link.mod-{number}")
        teams.append(
            {
                "id": id_from_href(link, "team"),
                "name": clean(link.select_one(".wf-title-med")) if link else "",
            }
        )
    scores = [
        clean(node)
        for node in header.select(
            ".match-header-vs-score .match-header-vs-score-winner, "
            ".match-header-vs-score .match-header-vs-score-loser"
        )
    ]
    score1, score2 = (scores + ["", ""])[:2]

    nav_order = {}
    for item in soup.select(".vm-stats-gamesnav-item"):
        number = re.match(r"\s*(\d+)", clean(item))
        if number:
            nav_order[item.get("data-game-id", "")] = number.group(1)

    maps: list[dict[str, Any]] = []
    rounds: list[dict[str, Any]] = []
    players: list[dict[str, Any]] = []
    tag_votes: list[Counter] = [Counter(), Counter()]

    for position, game in enumerate(played_games(soup), start=1):
        game_id = game["data-game-id"]
        game_header = game.select_one(".vm-stats-game-header")
        if game_header is None:
            continue
        sides = game_header.select(".team")
        if len(sides) != 2:
            continue
        map_scores = [clean(side.select_one(".score")) for side in sides]
        if not all(score.isdigit() for score in map_scores):
            continue

        name_node = game_header.select_one(".map-name")
        picked = game_header.select_one(".picked")
        picked_by = ""
        if picked is not None:
            picked_by = "1" if "mod-1" in picked.get("class", []) else "2"
        map_name = clean(name_node).replace("PICK", "").strip()
        record = {
            "game_id": game_id,
            "match_id": match_id,
            "map_no": nav_order.get(game_id, str(position)),
            "map": map_name,
            "picked_by": picked_by,
            "duration": clean(game_header.select_one(".map-duration")),
            "score1": map_scores[0],
            "score2": map_scores[1],
            "winner": "1" if int(map_scores[0]) > int(map_scores[1]) else "2",
        }
        for number, side in enumerate(sides, start=1):
            for key, css in (("atk", ".mod-t"), ("def", ".mod-ct"), ("ot", ".mod-ot")):
                record[f"team{number}_{key}"] = figure(clean(side.select_one(css)))

        comps: list[list[str]] = [[], []]
        for number, table in enumerate(game.select(".ovw-table")[:2], start=1):
            for row in table.select(".ovw-row"):
                if "mod-head" in row.get("class", []):
                    continue
                link = row.select_one("a[href^='/player/']")
                flag = row.select_one("i.flag")
                tag = clean(row.select_one(".ovw-player-tag"))
                agents = [
                    (img.get("title") or img.get("alt") or "").strip()
                    for img in row.select(".mod-agents img")
                ]
                player = {
                    "game_id": game_id,
                    "match_id": match_id,
                    "team": str(number),
                    "team_id": teams[number - 1]["id"],
                    "team_tag": tag,
                    "player_id": id_from_href(link, "player"),
                    "player": clean(row.select_one(".ovw-player-name")),
                    "country": (flag.get("title") or "").strip() if flag else "",
                    "agent": "|".join(agent for agent in agents if agent),
                }
                for name, column in SIDED_STATS:
                    cell = row.select_one(f"[data-col='{column}']")
                    for suffix, css in SIDES:
                        value = cell.select_one(f".side.{css}") if cell else None
                        player[f"{name}{suffix}"] = figure(clean(value))
                players.append(player)
                if tag:
                    tag_votes[number - 1][tag] += 1
                if player["agent"]:
                    comps[number - 1].append(player["agent"])
        record["team1_comp"] = "|".join(sorted(comps[0])) if len(comps[0]) == 5 else ""
        record["team2_comp"] = "|".join(sorted(comps[1])) if len(comps[1]) == 5 else ""
        maps.append(record)

        for column in game.select(".vlr-rounds-row-col"):
            number_node = column.select_one(".rnd-num")
            squares = column.select(".rnd-sq")
            if number_node is None or len(squares) != 2:
                continue
            for team_number, square in enumerate(squares, start=1):
                classes = square.get("class", [])
                if "mod-win" not in classes:
                    continue
                icon = square.select_one("img")
                icon_name = Path(icon.get("src", "")).stem if icon else ""
                rounds.append(
                    {
                        "game_id": game_id,
                        "round": clean(number_node),
                        "winner": str(team_number),
                        "winner_side": "atk" if "mod-t" in classes
                        else "def" if "mod-ct" in classes else "",
                        "win_type": WIN_TYPES.get(icon_name, icon_name),
                    }
                )

    tags = [votes.most_common(1)[0][0] if votes else "" for votes in tag_votes]

    vetoes = []
    veto_text = clean(header.select_one(".match-header-note"))
    for step, part in enumerate(filter(None, map(str.strip, veto_text.split(";"))), 1):
        found = re.match(r"^(.+?)\s+(ban|pick)\s+(.+)$", part)
        remains = re.match(r"^(.+?)\s+remains$", part)
        if found:
            tag, action, map_name = found.groups()
        elif remains:
            tag, action, map_name = "", "remains", remains.group(1)
        else:
            continue
        team = ""
        for number, known in enumerate(tags, start=1):
            if tag and known and tag.casefold() == known.casefold():
                team = str(number)
        vetoes.append(
            {
                "match_id": match_id,
                "step": str(step),
                "team": team,
                "team_tag": tag,
                "action": action,
                "map": map_name,
            }
        )

    winner = ""
    if score1.isdigit() and score2.isdigit() and score1 != score2:
        winner = "1" if int(score1) > int(score2) else "2"
    match = {
        "match_id": match_id,
        "event_id": id_from_href(event_link, "event"),
        "series": clean(header.select_one(".match-header-event-series")),
        "start_utc": start_utc,
        "patch": patch.group(1) if patch else "",
        "best_of": best_of.group(1) if best_of else "",
        "team1_id": teams[0]["id"],
        "team1": teams[0]["name"],
        "team1_tag": tags[0],
        "team2_id": teams[1]["id"],
        "team2": teams[1]["name"],
        "team2_tag": tags[1],
        "score1": score1,
        "score2": score2,
        "winner": winner,
        "url": url,
    }
    return {"match": match, "vetoes": vetoes, "maps": maps, "rounds": rounds,
            "players": players}


def parse_performance(html: str) -> dict[tuple[str, str, str], dict[str, str]]:
    """Multi-kills, clutches, plants and defuses: (game, tag, player) -> stats."""
    soup = BeautifulSoup(html, "html.parser")
    result: dict[tuple[str, str, str], dict[str, str]] = {}
    for game in played_games(soup):
        table = game.select_one("table.mod-adv-stats")
        if table is None:
            continue
        for row in table.select("tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) < 2 + len(ADVANCED_STATS):
                continue
            tag_node = cells[0].select_one(".team-tag")
            tag = clean(tag_node)
            if tag_node is not None:
                tag_node.extract()
            name = clean(cells[0])
            stats = {}
            for key, cell in zip(ADVANCED_STATS, cells[2:]):
                square = cell.select_one(".stats-sq")
                first = square.find(string=True, recursive=False) if square else None
                stats[key] = figure(str(first)) if first else ""
            result[(game["data-game-id"], tag, name)] = stats
    return result


def parse_economy(html: str) -> dict[tuple[str, str], dict[str, str]]:
    """Per-round money: (game, round) -> buy type, loadout value and bank.

    The page always draws a full grid, so rounds that were never played come
    back with an empty "winner".
    """
    soup = BeautifulSoup(html, "html.parser")
    result: dict[tuple[str, str], dict[str, str]] = {}
    for game in played_games(soup):
        number = 0
        for column in game.select(".ecs .vlr-rounds-row-col"):
            classes = column.get("class", [])
            if "mod-teams" in classes or "mod-spacing" in classes:
                continue
            number += 1
            record = {"winner": ""}
            for team in (1, 2):
                bank = column.select_one(f".ecr-bank.mod-t{team}")
                loadout = column.select_one(f".ecc-c.mod-t{team}")
                square = loadout.select_one(".ecc-sq") if loadout else None
                buy = ""
                classes = square.get("class", []) if square is not None else []
                for css, label in BUY_TYPES.items():
                    if css in classes:
                        buy = label
                if "mod-win" in classes:
                    record["winner"] = str(team)
                record[f"team{team}_buy"] = buy
                record[f"team{team}_loadout"] = thousands(loadout.get("title", "")) if loadout else ""
                record[f"team{team}_bank"] = thousands(bank.get("title", "")) if bank else ""
            result[(game["data-game-id"], str(number))] = record
    return result


def parse_match(match_id: str, overview: str, performance: str | None,
                economy: str | None, url: str = "") -> dict[str, Any]:
    """Combine a match's tabs into one set of records."""
    data = parse_overview(overview, match_id, url)
    advanced = parse_performance(performance) if performance else {}
    for player in data["players"]:
        stats = advanced.get(
            (player["game_id"], player["team_tag"], player["player"]), {}
        )
        for key in ADVANCED_STATS:
            player[key] = stats.get(key, "")

    money = parse_economy(economy) if economy else {}
    # Rounds are matched by position, so only trust a map's economy when it
    # names the same winner for every round it covers. The economy grid stops
    # at round 24, so overtime rounds are left without economy.
    mismatched = {
        row["game_id"] for row in data["rounds"]
        if ((row["game_id"], row["round"]) in money or int(row["round"]) <= REGULATION_ROUNDS)
        and money.get((row["game_id"], row["round"]), {}).get("winner") != row["winner"]
    }
    for row in data["rounds"]:
        record = {}
        if row["game_id"] not in mismatched:
            record = money.get((row["game_id"], row["round"]), {})
        for key in ROUND_FIELDS[5:]:
            row[key] = record.get(key, "")
    return data


# -------------------------------------------------------------- commands


def write_csv(path: Path, fields: Iterable[str], rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields),
                                lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1
    return count


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_events() -> list[dict[str, str]]:
    path = STATS_DIR / "events.csv"
    if not path.exists():
        raise StatsError("还没有 data/stats/events.csv，先运行 events 子命令")
    return read_csv(path)


def select_events(events: list[dict[str, str]], tiers: list[str],
                  years: list[int] | None) -> list[dict[str, str]]:
    chosen = [
        event for event in events
        if event["tier"] in tiers and (not years or int(event["year"]) in years)
    ]
    # Newest first, and the biggest stages before the qualifiers.
    chosen.sort(key=lambda e: (-int(e["year"]), TIERS.index(e["tier"]), int(e["event_id"])))
    return chosen


def command_events(args: argparse.Namespace) -> int:
    events: dict[int, dict[str, Any]] = {}
    for year in range(FIRST_YEAR, datetime.now(uc.UTC).year + 2):
        try:
            html = download(cache_path("years", str(year)),
                            f"{uc.VLR_BASE_URL}/vct-{year}", refresh=args.refresh)
        except uc.CalendarUpdateError as exc:
            print(f"vct-{year}: 跳过（{exc}）")
            continue
        for event in parse_year_page(html, year):
            events.setdefault(event["event_id"], event)
    rows = sorted(events.values(), key=lambda e: (e["year"], e["event_id"]))
    write_csv(STATS_DIR / "events.csv", EVENT_FIELDS, rows)
    summary = Counter((row["year"], row["tier"]) for row in rows)
    for (year, tier), count in sorted(summary.items()):
        print(f"{year} {tier}: {count}")
    print(f"共 {len(rows)} 个赛事 -> data/stats/events.csv")
    return 0


def event_matches(event: dict[str, str], *, refresh: bool = False) -> list[dict[str, str]]:
    url = f"{uc.VLR_BASE_URL}/event/matches/{event['event_id']}/?series_id=all"
    stale = refresh or event["status"] != "completed"
    html = download(cache_path("events", event["event_id"]), url, refresh=stale,
                    must_contain="wf-nav")
    return parse_event_listing(html)


def command_crawl(args: argparse.Namespace) -> int:
    events = select_events(load_events(), args.tier, args.year)
    print(f"{len(events)} 个赛事，标签页：{', '.join(args.tabs)}", flush=True)
    todo: list[tuple[dict[str, str], dict[str, str]]] = []
    for event in events:
        try:
            listed = event_matches(event, refresh=args.refresh_lists)
        except (uc.CalendarUpdateError, StatsError) as exc:
            print(f"  赛事 {event['event_id']} 列表失败：{exc}", flush=True)
            continue
        done = [m for m in listed if m["status"].lower() == "completed"]
        todo.extend((event, match) for match in done)
    print(f"已结束的比赛：{len(todo)} 场", flush=True)

    fetched = failed = streak = 0
    started = time.monotonic()
    for tab in args.tabs:
        pending = [
            (event, match) for event, match in todo
            if not cache_path("matches", f"{match['match_id']}.{tab}").exists()
        ]
        print(f"[{tab}] 待下载 {len(pending)} 场", flush=True)
        for index, (event, match) in enumerate(pending, start=1):
            if args.limit and fetched >= args.limit:
                break
            url = f"{uc.VLR_BASE_URL}{match['path']}"
            if TABS[tab]:
                url = f"{url.rstrip('/')}/{TABS[tab]}"
            try:
                download(cache_path("matches", f"{match['match_id']}.{tab}"), url,
                         must_contain="match-header")
                fetched += 1
                streak = 0
            except (uc.CalendarUpdateError, StatsError) as exc:
                failed += 1
                streak += 1
                print(f"  失败 {match['match_id']} {tab}: {exc}", flush=True)
                if streak >= MAX_CONSECUTIVE_FAILURES:
                    print("连续失败过多，停止。稍后重跑会从断点继续。", flush=True)
                    return 1
                time.sleep(10 * streak)
            if index % 50 == 0:
                minutes = (time.monotonic() - started) / 60
                print(f"  [{tab}] {index}/{len(pending)}  已用 {minutes:.0f} 分钟",
                      flush=True)
    print(f"完成：下载 {fetched}，失败 {failed}", flush=True)
    return 1 if failed else 0


def build_tables(events: list[dict[str, str]]) -> dict[str, Any]:
    """Parse every cached match of the given events."""
    per_year: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"matches": [], "vetoes": [], "maps": [], "rounds": [], "players": []}
    )
    problems: list[str] = []
    seen: set[str] = set()
    for event in events:
        listing = read_cache(cache_path("events", event["event_id"]))
        if listing is None:
            continue
        for match in parse_event_listing(listing):
            match_id = match["match_id"]
            overview = read_cache(cache_path("matches", f"{match_id}.overview"))
            if overview is None or match_id in seen:
                continue
            seen.add(match_id)
            try:
                data = parse_match(
                    match_id,
                    overview,
                    read_cache(cache_path("matches", f"{match_id}.performance")),
                    read_cache(cache_path("matches", f"{match_id}.economy")),
                    url=f"{uc.VLR_BASE_URL}{match['path']}",
                )
            except StatsError as exc:
                problems.append(str(exc))
                continue
            # The match belongs to the event whose list it was found on.
            data["match"]["event_id"] = event["event_id"]
            tables = per_year[event["year"]]
            tables["matches"].append(data["match"])
            for name in ("vetoes", "maps", "rounds", "players"):
                tables[name].extend(data[name])
    return {"years": per_year, "problems": problems}


def summarise_teams(years: dict[str, dict[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    teams: dict[str, dict[str, Any]] = {}
    for year in sorted(years):
        tables = years[year]
        by_match = {match["match_id"]: match for match in tables["matches"]}
        for match in sorted(tables["matches"], key=lambda m: m["start_utc"]):
            for number in ("1", "2"):
                team_id = match[f"team{number}_id"]
                if not team_id:
                    continue
                team = teams.setdefault(team_id, {
                    "team_id": team_id, "names": Counter(), "first_match": match["start_utc"],
                    "matches": 0, "maps": 0, "map_wins": 0,
                })
                team["name"] = match[f"team{number}"]
                team["tag"] = match[f"team{number}_tag"] or team.get("tag", "")
                team["names"][match[f"team{number}"]] += 1
                team["last_match"] = match["start_utc"]
                team["matches"] += 1
        for game in tables["maps"]:
            match = by_match[game["match_id"]]
            for number in ("1", "2"):
                team = teams.get(match[f"team{number}_id"])
                if team is None:
                    continue
                team["maps"] += 1
                team["map_wins"] += game["winner"] == number
    rows = []
    for team in teams.values():
        others = [name for name in team["names"] if name != team["name"]]
        rows.append({**team, "other_names": "|".join(sorted(others))})
    return sorted(rows, key=lambda row: int(row["team_id"]))


def summarise_players(years: dict[str, dict[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    players: dict[str, dict[str, Any]] = {}
    for year in sorted(years):
        tables = years[year]
        starts = {match["match_id"]: match["start_utc"] for match in tables["matches"]}
        names = {}
        for match in tables["matches"]:
            names[(match["match_id"], "1")] = match["team1"]
            names[(match["match_id"], "2")] = match["team2"]
        for row in sorted(tables["players"], key=lambda r: starts.get(r["match_id"], "")):
            if not row["player_id"]:
                continue
            start = starts.get(row["match_id"], "")
            player = players.setdefault(row["player_id"], {
                "player_id": row["player_id"], "names": Counter(), "teams": [],
                "agents": Counter(), "first_match": start, "maps": 0,
            })
            player["name"] = row["player"]
            player["country"] = row["country"] or player.get("country", "")
            player["names"][row["player"]] += 1
            player["last_match"] = start
            player["maps"] += 1
            team_name = names.get((row["match_id"], row["team"]), "")
            if team_name and (not player["teams"] or player["teams"][-1] != team_name):
                player["teams"].append(team_name)
            for agent in filter(None, row["agent"].split("|")):
                player["agents"][agent] += 1
    rows = []
    for player in players.values():
        others = [name for name in player["names"] if name != player["name"]]
        rows.append({
            **player,
            "other_names": "|".join(sorted(others)),
            "teams": "|".join(player["teams"]),
            "top_agents": "|".join(agent for agent, _ in player["agents"].most_common(3)),
        })
    return sorted(rows, key=lambda row: int(row["player_id"]))


def command_build(args: argparse.Namespace) -> int:
    result = build_tables(load_events())
    years = result["years"]
    totals: Counter = Counter()
    for year in sorted(years):
        tables = years[year]
        folder = STATS_DIR / year
        for name, fields, key in (
            ("matches", MATCH_FIELDS, lambda r: (r["start_utc"], int(r["match_id"]))),
            ("vetoes", VETO_FIELDS, lambda r: (int(r["match_id"]), int(r["step"]))),
            ("maps", MAP_FIELDS, lambda r: (int(r["match_id"]), int(r["map_no"]))),
            ("rounds", ROUND_FIELDS, lambda r: (int(r["game_id"]), int(r["round"]))),
            ("players", PLAYER_FIELDS, lambda r: (int(r["game_id"]), r["team"])),
        ):
            file_name = "player_stats.csv" if name == "players" else f"{name}.csv"
            count = write_csv(folder / file_name, fields, sorted(tables[name], key=key))
            totals[name] += count
        print(f"{year}: {len(tables['matches'])} 场比赛，{len(tables['maps'])} 张图，"
              f"{len(tables['players'])} 条选手数据")
    totals["teams"] = write_csv(STATS_DIR / "teams.csv", TEAM_FIELDS, summarise_teams(years))
    totals["player_index"] = write_csv(
        STATS_DIR / "players.csv", PLAYER_INDEX_FIELDS, summarise_players(years)
    )
    print("合计：" + "，".join(f"{name} {count}" for name, count in totals.items()))
    for problem in result["problems"][:20]:
        print(f"  无法解析：{problem}")
    return 0


def command_check(args: argparse.Namespace) -> int:
    """Report how complete the tables are, year by year."""
    failed = False
    for folder in sorted(path for path in STATS_DIR.iterdir() if path.is_dir() and path.name.isdigit()):
        matches = read_csv(folder / "matches.csv")
        maps = read_csv(folder / "maps.csv")
        rounds = Counter(row["game_id"] for row in read_csv(folder / "rounds.csv"))
        priced = Counter(
            row["game_id"] for row in read_csv(folder / "rounds.csv") if row["team1_buy"]
        )
        players = read_csv(folder / "player_stats.csv")
        rows_per_map = Counter(row["game_id"] for row in players)
        wins = Counter((game["match_id"], game["winner"]) for game in maps)

        no_maps = len({m["match_id"] for m in matches} - {g["match_id"] for g in maps})
        wrong_series = sum(
            1 for m in matches
            if (m["match_id"], "1") in wins or (m["match_id"], "2") in wins
            if (str(wins[(m["match_id"], "1")]), str(wins[(m["match_id"], "2")]))
            != (m["score1"], m["score2"])
        )
        wrong_rounds = sum(
            1 for g in maps if rounds[g["game_id"]] != int(g["score1"]) + int(g["score2"])
        )
        not_ten = sum(1 for g in maps if rows_per_map[g["game_id"]] != 10)
        share = lambda count, total: f"{100 * count / total:.0f}%" if total else "-"
        print(
            f"{folder.name}: {len(matches)} 场比赛（{no_maps} 场没有地图数据），{len(maps)} 张图\n"
            f"  选手数据不是 10 行的图 {not_ten}，回合数对不上比分的图 {wrong_rounds}，"
            f"地图胜场对不上大比分的比赛 {wrong_series}\n"
            f"  有评分 {share(sum(bool(r['rating']) for r in players), len(players))}，"
            f"有特工 {share(sum(bool(r['agent']) for r in players), len(players))}，"
            f"有多杀和残局 {share(sum(bool(r['econ']) for r in players), len(players))}，"
            f"有经济数据的图 {share(sum(1 for g in maps if priced[g['game_id']]), len(maps))}，"
            f"有禁选记录的比赛 {share(len({v['match_id'] for v in read_csv(folder / 'vetoes.csv')}), len(matches))}"
        )
        failed = failed or bool(wrong_series)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cache", type=Path, help="页面缓存目录（默认 .cache/vlr）")
    commands = parser.add_subparsers(dest="command", required=True)

    events = commands.add_parser("events", help="从 VLR 的年度页面列出赛事")
    events.add_argument("--refresh", action="store_true", help="重新下载年度页面")
    events.set_defaults(run=command_events)

    crawl = commands.add_parser("crawl", help="下载比赛页面到缓存")
    crawl.add_argument("--tier", nargs="+", choices=TIERS,
                       default=["international", "league", "qualifier"])
    crawl.add_argument("--year", nargs="+", type=int)
    crawl.add_argument("--tabs", nargs="+", choices=list(TABS), default=list(TABS))
    crawl.add_argument("--limit", type=int, default=0, help="最多下载多少个页面")
    crawl.add_argument("--refresh-lists", action="store_true",
                       help="重新下载赛事的比赛列表")
    crawl.set_defaults(run=command_crawl)

    build = commands.add_parser("build", help="把缓存解析成 CSV")
    build.set_defaults(run=command_build)

    check = commands.add_parser("check", help="检查 CSV 的完整程度")
    check.set_defaults(run=command_check)

    args = parser.parse_args(argv)
    if args.cache:
        global CACHE_DIR
        CACHE_DIR = args.cache.resolve()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        return args.run(args)
    except (StatsError, uc.CalendarUpdateError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
