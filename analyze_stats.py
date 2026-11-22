"""Summarise the match statistics in data/stats into small analysis tables.

    python analyze_stats.py            # -> data/stats/summary/*.csv

Every table has one block of rows per year plus a block with year "all".
Rates are 0-1. Player averages are weighted by the rounds of each map, the
same way an event page on VLR weights them.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import vlr_stats
from vlr_stats import read_csv, write_csv

ALL = "all"
MIN_COMP_MAPS = 3       # compositions seen less often than this are left out
MIN_AGENT_MAP_PICKS = 5  # same for an agent on one map
PISTOL_ROUNDS = {"1", "13"}

MAP_FIELDS = (
    "year", "map", "played", "pick_rate", "ban_rate", "decider_rate",
    "atk_round_share", "picker_win_rate", "overtime_rate", "avg_rounds",
)
AGENT_FIELDS = ("year", "agent", "picks", "pick_rate", "win_rate", "rating", "acs", "maps_used_on")
AGENT_MAP_FIELDS = ("year", "map", "agent", "picks", "pick_rate", "win_rate")
AGENT_REGION_FIELDS = ("year", "region", "agent", "picks", "pick_rate", "win_rate")
COMP_FIELDS = ("year", "map", "comp", "played", "pick_rate", "wins", "win_rate", "teams")
PLAYER_FIELDS = (
    "year", "player_id", "player", "team", "maps", "rounds", "rating", "rating_atk",
    "rating_def", "acs", "kd", "kills", "deaths", "assists", "kast", "adr", "hs",
    "fk", "fd", "fk_per_map", "multikills", "clutches", "agents",
)
TEAM_FIELDS = (
    "year", "team_id", "team", "matches", "match_wins", "maps", "map_wins", "map_win_rate",
    "round_win_rate", "atk_round_win_rate", "def_round_win_rate", "pistol_win_rate",
    "own_pick_win_rate", "most_played_map", "comps_used",
)
TEAM_MAP_FIELDS = ("year", "team_id", "team", "map", "played", "wins", "win_rate", "picked", "banned")
ECONOMY_FIELDS = ("year", "buy", "against", "rounds", "wins", "win_rate")


def rate(part: float, whole: float) -> str:
    return f"{part / whole:.3f}" if whole else ""


def number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Average:
    """A weighted mean that ignores missing values."""

    def __init__(self) -> None:
        self.total = 0.0
        self.weight = 0.0

    def add(self, value: str, weight: float) -> None:
        parsed = number(value)
        if parsed is not None and weight:
            self.total += parsed * weight
            self.weight += weight

    def text(self, digits: int = 2) -> str:
        return f"{self.total / self.weight:.{digits}f}" if self.weight else ""


def load_years(stats_dir: Path) -> dict[str, dict[str, list[dict[str, str]]]]:
    years = {}
    for folder in sorted(path for path in stats_dir.iterdir() if path.is_dir() and path.name.isdigit()):
        years[folder.name] = {
            name: read_csv(folder / f"{name}.csv")
            for name in ("matches", "maps", "rounds", "vetoes", "player_stats")
        }
    return years


def scopes(years: dict[str, Any]) -> Iterable[tuple[str, list[dict[str, list[dict[str, str]]]]]]:
    """Each year on its own, then every year together."""
    for year, tables in years.items():
        yield year, [tables]
    if len(years) > 1:
        yield ALL, list(years.values())


def merged(parts: list[dict[str, list[dict[str, str]]]], name: str) -> list[dict[str, str]]:
    return [row for tables in parts for row in tables[name]]


def summarise(years: dict[str, Any], events: list[dict[str, str]],
              team_names: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    event_region = {event["event_id"]: event["region"] for event in events}
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for year, parts in scopes(years):
        matches = merged(parts, "matches")
        maps = merged(parts, "maps")
        rounds = merged(parts, "rounds")
        vetoes = merged(parts, "vetoes")
        players = merged(parts, "player_stats")
        match_by_id = {match["match_id"]: match for match in matches}
        game_by_id = {game["game_id"]: game for game in maps}
        rounds_in_game = {
            game["game_id"]: int(game["score1"]) + int(game["score2"]) for game in maps
        }

        def team_id(game: dict[str, str], number_: str) -> str:
            return match_by_id[game["match_id"]][f"team{number_}_id"]

        # ---------------------------------------------------------------- maps
        veto_matches = {veto["match_id"] for veto in vetoes}
        picks = Counter(v["map"] for v in vetoes if v["action"] == "pick")
        bans = Counter(v["map"] for v in vetoes if v["action"] == "ban")
        played = Counter(game["map"] for game in maps)
        decider_pool = Counter(v["map"] for v in vetoes if v["action"] == "remains")
        attack: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for row in rounds:
            game = game_by_id.get(row["game_id"])
            if game is None or not row["winner_side"]:
                continue
            attack[game["map"]][0] += row["winner_side"] == "atk"
            attack[game["map"]][1] += 1
        for name in sorted(played, key=lambda item: -played[item]):
            games = [game for game in maps if game["map"] == name]
            picked = [game for game in games if game["picked_by"]]
            out["maps"].append({
                "year": year, "map": name, "played": played[name],
                "pick_rate": rate(picks[name], len(veto_matches)),
                "ban_rate": rate(bans[name], len(veto_matches)),
                "decider_rate": rate(decider_pool[name], len(veto_matches)),
                "atk_round_share": rate(*attack[name]),
                "picker_win_rate": rate(
                    sum(game["winner"] == game["picked_by"] for game in picked), len(picked)
                ),
                "overtime_rate": rate(
                    sum(rounds_in_game[game["game_id"]] > 24 for game in games), len(games)
                ),
                "avg_rounds": f"{sum(rounds_in_game[g['game_id']] for g in games) / len(games):.1f}",
            })

        # -------------------------------------------------------------- agents
        agent_rows: dict[str, dict[str, Any]] = {}
        by_map: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        by_region: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        region_team_maps: Counter = Counter()
        for game in maps:
            region = event_region.get(match_by_id[game["match_id"]]["event_id"], "")
            region_team_maps[region] += 2
        for row in players:
            game = game_by_id.get(row["game_id"])
            if game is None or not row["agent"] or "|" in row["agent"]:
                continue
            won = game["winner"] == row["team"]
            weight = rounds_in_game[row["game_id"]]
            info = agent_rows.setdefault(row["agent"], {
                "picks": 0, "wins": 0, "rating": Average(), "acs": Average(), "maps": set(),
            })
            info["picks"] += 1
            info["wins"] += won
            info["rating"].add(row["rating"], weight)
            info["acs"].add(row["acs"], weight)
            info["maps"].add(game["map"])
            by_map[(game["map"], row["agent"])][0] += 1
            by_map[(game["map"], row["agent"])][1] += won
            region = event_region.get(match_by_id[game["match_id"]]["event_id"], "")
            by_region[(region, row["agent"])][0] += 1
            by_region[(region, row["agent"])][1] += won
        team_maps = 2 * len(maps)
        for agent, info in sorted(agent_rows.items(), key=lambda item: -item[1]["picks"]):
            out["agents"].append({
                "year": year, "agent": agent, "picks": info["picks"],
                "pick_rate": rate(info["picks"], team_maps),
                "win_rate": rate(info["wins"], info["picks"]),
                "rating": info["rating"].text(), "acs": info["acs"].text(0),
                "maps_used_on": len(info["maps"]),
            })
        for (name, agent), (count, wins) in sorted(by_map.items(), key=lambda i: (i[0][0], -i[1][0])):
            if count >= MIN_AGENT_MAP_PICKS:
                out["agents_by_map"].append({
                    "year": year, "map": name, "agent": agent, "picks": count,
                    "pick_rate": rate(count, 2 * played[name]), "win_rate": rate(wins, count),
                })
        for (region, agent), (count, wins) in sorted(by_region.items(), key=lambda i: (i[0][0], -i[1][0])):
            if region and count >= MIN_AGENT_MAP_PICKS:
                out["agents_by_region"].append({
                    "year": year, "region": region, "agent": agent, "picks": count,
                    "pick_rate": rate(count, region_team_maps[region]), "win_rate": rate(wins, count),
                })

        # --------------------------------------------------------------- comps
        comps: dict[tuple[str, str], dict[str, Any]] = {}
        for game in maps:
            for number_ in ("1", "2"):
                comp = game[f"team{number_}_comp"]
                if not comp:
                    continue
                info = comps.setdefault((game["map"], comp), {"played": 0, "wins": 0, "teams": set()})
                info["played"] += 1
                info["wins"] += game["winner"] == number_
                info["teams"].add(team_id(game, number_))
        for (name, comp), info in sorted(comps.items(), key=lambda i: (i[0][0], -i[1]["played"])):
            if info["played"] >= MIN_COMP_MAPS:
                out["comps"].append({
                    "year": year, "map": name, "comp": comp, "played": info["played"],
                    "pick_rate": rate(info["played"], 2 * played[name]),
                    "wins": info["wins"], "win_rate": rate(info["wins"], info["played"]),
                    "teams": len(info["teams"]),
                })

        # ------------------------------------------------------------- players
        people: dict[str, dict[str, Any]] = {}
        starts = {match["match_id"]: match["start_utc"] for match in matches}
        for row in sorted(players, key=lambda r: starts.get(r["match_id"], "")):
            if not row["player_id"] or row["game_id"] not in game_by_id:
                continue
            weight = rounds_in_game[row["game_id"]]
            info = people.setdefault(row["player_id"], {
                "maps": 0, "rounds": 0, "sums": Counter(), "agents": Counter(),
                **{key: Average() for key in ("rating", "rating_atk", "rating_def", "acs", "kast", "adr", "hs")},
            })
            info["player"] = row["player"]
            info["team"] = row["team_tag"]
            info["maps"] += 1
            info["rounds"] += weight
            for key in ("rating", "rating_atk", "rating_def", "acs", "kast", "adr", "hs"):
                info[key].add(row[key], weight)
            for key in ("kills", "deaths", "assists", "fk", "fd"):
                info["sums"][key] += int(number(row[key]) or 0)
            info["sums"]["multikills"] += sum(int(number(row[key]) or 0) for key in ("k3", "k4", "k5"))
            info["sums"]["clutches"] += sum(
                int(number(row[key]) or 0)
                for key in ("clutch_1v1", "clutch_1v2", "clutch_1v3", "clutch_1v4", "clutch_1v5")
            )
            for agent in filter(None, row["agent"].split("|")):
                info["agents"][agent] += 1
        for player_id, info in sorted(people.items(), key=lambda item: -item[1]["maps"]):
            sums = info["sums"]
            out["players"].append({
                "year": year, "player_id": player_id, "player": info["player"], "team": info["team"],
                "maps": info["maps"], "rounds": info["rounds"],
                "rating": info["rating"].text(), "rating_atk": info["rating_atk"].text(),
                "rating_def": info["rating_def"].text(), "acs": info["acs"].text(0),
                "kd": f"{sums['kills'] / sums['deaths']:.2f}" if sums["deaths"] else "",
                "kills": sums["kills"], "deaths": sums["deaths"], "assists": sums["assists"],
                "kast": info["kast"].text(1), "adr": info["adr"].text(0), "hs": info["hs"].text(1),
                "fk": sums["fk"], "fd": sums["fd"], "fk_per_map": f"{sums['fk'] / info['maps']:.2f}",
                "multikills": sums["multikills"], "clutches": sums["clutches"],
                "agents": "|".join(f"{agent}:{count}" for agent, count in info["agents"].most_common(4)),
            })

        # --------------------------------------------------------------- teams
        squads: dict[str, dict[str, Any]] = {}

        def squad(identifier: str) -> dict[str, Any]:
            return squads.setdefault(identifier, {"count": Counter(), "maps": Counter(), "comps": set(),
                                                  "map_wins": Counter(), "picked": Counter(), "banned": Counter()})

        for match in matches:
            for number_ in ("1", "2"):
                if not match[f"team{number_}_id"]:
                    continue
                info = squad(match[f"team{number_}_id"])
                info["count"]["matches"] += 1
                info["count"]["match_wins"] += match["winner"] == number_
        for veto in vetoes:
            match = match_by_id.get(veto["match_id"])
            if match is None or veto["team"] not in ("1", "2"):
                continue
            key = "picked" if veto["action"] == "pick" else "banned"
            squad(match[f"team{veto['team']}_id"])[key][veto["map"]] += 1
        for game in maps:
            for number_ in ("1", "2"):
                identifier = team_id(game, number_)
                if not identifier:
                    continue
                info = squad(identifier)
                info["maps"][game["map"]] += 1
                info["map_wins"][game["map"]] += game["winner"] == number_
                if game[f"team{number_}_comp"]:
                    info["comps"].add((game["map"], game[f"team{number_}_comp"]))
                if game["picked_by"] == number_:
                    info["count"]["own_picks"] += 1
                    info["count"]["own_pick_wins"] += game["winner"] == number_
        for row in rounds:
            game = game_by_id.get(row["game_id"])
            if game is None or row["winner"] not in ("1", "2"):
                continue
            for number_ in ("1", "2"):
                identifier = team_id(game, number_)
                if not identifier:
                    continue
                count = squad(identifier)["count"]
                won = row["winner"] == number_
                count["rounds"] += 1
                count["round_wins"] += won
                if row["winner_side"]:
                    side = row["winner_side"] if won else ("def" if row["winner_side"] == "atk" else "atk")
                    count[f"{side}_rounds"] += 1
                    count[f"{side}_wins"] += won
                if row["round"] in PISTOL_ROUNDS:
                    count["pistols"] += 1
                    count["pistol_wins"] += won
        for identifier, info in sorted(squads.items(), key=lambda item: -sum(item[1]["maps"].values())):
            count = info["count"]
            total_maps = sum(info["maps"].values())
            name = team_names.get(identifier, identifier)
            out["teams"].append({
                "year": year, "team_id": identifier, "team": name,
                "matches": count["matches"], "match_wins": count["match_wins"],
                "maps": total_maps, "map_wins": sum(info["map_wins"].values()),
                "map_win_rate": rate(sum(info["map_wins"].values()), total_maps),
                "round_win_rate": rate(count["round_wins"], count["rounds"]),
                "atk_round_win_rate": rate(count["atk_wins"], count["atk_rounds"]),
                "def_round_win_rate": rate(count["def_wins"], count["def_rounds"]),
                "pistol_win_rate": rate(count["pistol_wins"], count["pistols"]),
                "own_pick_win_rate": rate(count["own_pick_wins"], count["own_picks"]),
                "most_played_map": info["maps"].most_common(1)[0][0] if info["maps"] else "",
                "comps_used": len(info["comps"]),
            })
            for map_name in sorted(set(info["maps"]) | set(info["picked"]) | set(info["banned"])):
                out["team_maps"].append({
                    "year": year, "team_id": identifier, "team": name, "map": map_name,
                    "played": info["maps"][map_name], "wins": info["map_wins"][map_name],
                    "win_rate": rate(info["map_wins"][map_name], info["maps"][map_name]),
                    "picked": info["picked"][map_name], "banned": info["banned"][map_name],
                })

        # ------------------------------------------------------------- economy
        money: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        for row in rounds:
            if not row["team1_buy"] or not row["team2_buy"]:
                continue
            money[(row["team1_buy"], row["team2_buy"])][0] += 1
            money[(row["team1_buy"], row["team2_buy"])][1] += row["winner"] == "1"
            money[(row["team2_buy"], row["team1_buy"])][0] += 1
            money[(row["team2_buy"], row["team1_buy"])][1] += row["winner"] == "2"
        for (buy, against), (count, wins) in sorted(money.items()):
            out["economy"].append({
                "year": year, "buy": buy, "against": against, "rounds": count,
                "wins": wins, "win_rate": rate(wins, count),
            })
    return out


OUTPUTS = (
    ("maps", MAP_FIELDS), ("agents", AGENT_FIELDS), ("agents_by_map", AGENT_MAP_FIELDS),
    ("agents_by_region", AGENT_REGION_FIELDS), ("comps", COMP_FIELDS), ("players", PLAYER_FIELDS),
    ("teams", TEAM_FIELDS), ("team_maps", TEAM_MAP_FIELDS), ("economy", ECONOMY_FIELDS),
)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    stats_dir = vlr_stats.STATS_DIR
    years = load_years(stats_dir)
    if not years:
        print("data/stats 里还没有数据，先运行 vlr_stats.py build", file=sys.stderr)
        return 1
    team_names = {row["team_id"]: row["name"] for row in read_csv(stats_dir / "teams.csv")}
    tables = summarise(years, read_csv(stats_dir / "events.csv"), team_names)
    for name, fields in OUTPUTS:
        count = write_csv(stats_dir / "summary" / f"{name}.csv", fields, tables[name])
        print(f"summary/{name}.csv: {count} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
