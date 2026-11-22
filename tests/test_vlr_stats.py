"""Match statistics parsed from VLR pages.

The fixtures are the three tabs of one real match (the Champions 2026 grand
final), trimmed to its first map plus the fifth map that was never played.
"""

import argparse
import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analyze_stats
import vlr_stats
from vlr_stats import (
    classify_event,
    event_region,
    parse_event_listing,
    parse_match,
    parse_year_page,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


OVERVIEW = fixture("stats_overview.html")
PERFORMANCE = fixture("stats_performance.html")
ECONOMY = fixture("stats_economy.html")


class EventCatalogueTests(unittest.TestCase):
    def test_events_are_sorted_into_tiers(self):
        cases = {
            "valorant-champions-2026": ("international", "INTL"),
            "valorant-masters-london-2026": ("international", "INTL"),
            "champions-tour-2023-lock-in-s-o-paulo": ("international", "INTL"),
            "valorant-champions-tour-stage-2-masters-reykjav-k": ("international", "INTL"),
            "vct-2026-china-stage-2": ("league", "CN"),
            "champions-tour-2023-americas-league": ("league", "AMER"),
            "champions-tour-2023-pacific-last-chance-qualifier": ("qualifier", "PAC"),
            # 2021's regional "Masters" were regional finals, not world events.
            "champions-tour-north-america-stage-1-masters": ("challengers", "AMER"),
            "champions-tour-turkey-stage-3-challengers-1": ("challengers", "EMEA"),
        }
        for slug, expected in cases.items():
            tier = classify_event(slug)
            self.assertEqual((tier, event_region(slug, tier)), expected, slug)

    def test_year_page_lists_events_with_their_tier(self):
        events = parse_year_page(fixture("events_list.html"), 2026)
        self.assertTrue(events)
        self.assertTrue(all(event["year"] == 2026 for event in events))
        self.assertTrue({"event_id", "tier", "region", "slug", "status"} <= set(events[0]))

    def test_event_listing_gives_match_paths(self):
        matches = parse_event_listing(fixture("event_matches.html"))
        self.assertTrue(matches)
        for match in matches:
            self.assertTrue(match["path"].startswith(f"/{match['match_id']}/"))
            self.assertTrue(match["status"])


class MatchParsingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = parse_match("754737", OVERVIEW, PERFORMANCE, ECONOMY, url="u")

    def test_match_header(self):
        match = self.data["match"]
        self.assertEqual(
            (match["team1"], match["team2"], match["score1"], match["score2"], match["winner"]),
            ("LOUD", "Team Vitality", "3", "1", "1"),
        )
        self.assertEqual((match["team1_id"], match["team2_id"]), ("6961", "2059"))
        self.assertEqual((match["team1_tag"], match["team2_tag"]), ("LOUD", "VIT"))
        self.assertEqual((match["event_id"], match["best_of"], match["patch"]), ("2766", "5", "13.05"))
        self.assertEqual(match["series"], "Playoffs: Grand Final")
        # The page gives Havana local time; 02:00 there is 06:00 UTC.
        self.assertEqual(match["start_utc"], "2026-10-18T06:00:00Z")

    def test_veto_names_the_team_behind_each_step(self):
        steps = [(v["team"], v["action"], v["map"]) for v in self.data["vetoes"]]
        self.assertEqual(steps[:4], [
            ("1", "ban", "Ascent"), ("1", "ban", "Split"),
            ("1", "pick", "Summit"), ("2", "pick", "Lotus"),
        ])
        self.assertEqual(steps[-1], ("", "remains", "Abyss"))

    def test_only_played_maps_are_kept(self):
        self.assertEqual(len(self.data["maps"]), 1)
        game = self.data["maps"][0]
        self.assertEqual((game["map"], game["map_no"], game["picked_by"]), ("Summit", "1", "1"))
        self.assertEqual((game["score1"], game["score2"], game["winner"]), ("13", "11", "1"))
        self.assertEqual((game["team1_atk"], game["team1_def"]), ("3", "10"))
        self.assertEqual(game["team1_comp"], "Chamber|Fade|Neon|Omen|Sage")
        self.assertEqual(game["team2_comp"], "Chamber|Fade|Harbor|Neon|Phoenix")

    def test_rounds_carry_winner_side_and_economy(self):
        rounds = self.data["rounds"]
        self.assertEqual(len(rounds), 24)
        first = rounds[0]
        self.assertEqual(
            (first["round"], first["winner"], first["winner_side"], first["win_type"]),
            ("1", "2", "def", "defuse"),
        )
        self.assertEqual((first["team1_buy"], first["team2_buy"]), ("pistol", "pistol"))
        self.assertEqual((first["team1_loadout"], first["team1_bank"]), ("3900", "100"))
        self.assertEqual(sum(row["winner"] == "1" for row in rounds), 13)
        self.assertTrue(all(row["team1_buy"] for row in rounds))

    def test_player_rows_have_side_splits_and_advanced_stats(self):
        players = self.data["players"]
        self.assertEqual(len(players), 10)
        self.assertEqual([p["team"] for p in players], ["1"] * 5 + ["2"] * 5)
        erde = players[0]
        self.assertEqual(
            (erde["player"], erde["player_id"], erde["country"], erde["agent"], erde["team_id"]),
            ("erde", "29242", "Chile", "Sage", "6961"),
        )
        self.assertEqual((erde["rating"], erde["rating_atk"], erde["rating_def"]), ("1.31", "0.54", "2.09"))
        self.assertEqual((erde["kills"], erde["deaths"], erde["assists"]), ("19", "16", "13"))
        self.assertEqual((erde["kast"], erde["hs"], erde["fk"], erde["fd"]), ("71", "31", "3", "4"))
        self.assertEqual((erde["k2"], erde["k3"], erde["plants"], erde["defuses"]), ("4", "2", "1", "1"))

    def test_overview_alone_still_parses(self):
        data = parse_match("754737", OVERVIEW, None, None)
        self.assertEqual(len(data["players"]), 10)
        self.assertEqual(data["players"][0]["k2"], "")
        self.assertEqual(data["rounds"][0]["team1_buy"], "")

    def test_overtime_rounds_keep_regulation_economy(self):
        """The economy tab stops at round 24; overtime rounds stay blank."""
        real = vlr_stats.parse_overview

        def with_overtime(*args, **kwargs):
            data = real(*args, **kwargs)
            extra = [dict(data["rounds"][-1], round=str(n), winner=w) for n, w in ((25, "2"), (26, "1"))]
            data["rounds"].extend(extra)
            return data

        with mock.patch.object(vlr_stats, "parse_overview", with_overtime):
            data = parse_match("754737", OVERVIEW, PERFORMANCE, ECONOMY)
        by_round = {row["round"]: row for row in data["rounds"]}
        self.assertEqual(by_round["24"]["team1_buy"] != "", True)
        self.assertEqual((by_round["25"]["team1_buy"], by_round["26"]["team2_bank"]), ("", ""))

    def test_economy_that_disagrees_with_the_rounds_is_dropped(self):
        swapped = (
            ECONOMY.replace("mod-t1", "mod-tX").replace("mod-t2", "mod-t1").replace("mod-tX", "mod-t2")
        )
        data = parse_match("754737", OVERVIEW, PERFORMANCE, swapped)
        self.assertTrue(all(row["team1_buy"] == "" for row in data["rounds"]))
        self.assertEqual(data["rounds"][0]["winner"], "2")


class BuildTests(unittest.TestCase):
    def test_cache_is_turned_into_tables(self):
        listing = (
            '<a class="wf-module-item match-item" href="/754737/loud-vs-team-vitality">'
            '<div class="ml-status">Completed</div></a>'
        )
        event = {
            "event_id": "2766", "year": "2026", "tier": "international", "region": "INTL",
            "name": "Valorant Champions 2026", "slug": "valorant-champions-2026", "status": "completed",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.multiple(vlr_stats, CACHE_DIR=root / "cache", STATS_DIR=root / "stats"):
                vlr_stats.write_csv(root / "stats" / "events.csv", vlr_stats.EVENT_FIELDS, [event])
                vlr_stats.write_cache(vlr_stats.cache_path("events", "2766"), listing)
                for tab, html in (("overview", OVERVIEW), ("performance", PERFORMANCE), ("economy", ECONOMY)):
                    vlr_stats.write_cache(vlr_stats.cache_path("matches", f"754737.{tab}"), html)
                with mock.patch("builtins.print"):
                    self.assertEqual(vlr_stats.command_build(argparse.Namespace()), 0)

                def table(name):
                    with (root / "stats" / name).open(encoding="utf-8", newline="") as handle:
                        return list(csv.DictReader(handle))

                self.assertEqual(len(table("2026/matches.csv")), 1)
                self.assertEqual(len(table("2026/maps.csv")), 1)
                self.assertEqual(len(table("2026/rounds.csv")), 24)
                self.assertEqual(len(table("2026/vetoes.csv")), 7)
                self.assertEqual(len(table("2026/player_stats.csv")), 10)
                teams = {row["team_id"]: row for row in table("teams.csv")}
                self.assertEqual((teams["6961"]["name"], teams["6961"]["maps"], teams["6961"]["map_wins"]), ("LOUD", "1", "1"))
                players = {row["name"]: row for row in table("players.csv")}
                self.assertEqual((players["erde"]["teams"], players["erde"]["top_agents"]), ("LOUD", "Sage"))
                raw = (root / "stats" / "2026" / "matches.csv").read_bytes()
                self.assertNotIn(b"\r", raw)

                summary = analyze_stats.summarise(
                    analyze_stats.load_years(root / "stats"),
                    table("events.csv"),
                    {row["team_id"]: row["name"] for row in table("teams.csv")},
                )
                summit = summary["maps"][0]
                self.assertEqual((summit["map"], summit["played"], summit["pick_rate"]), ("Summit", 1, "1.000"))
                # LOUD picked Summit and won it; attackers took 5 of the 24 rounds.
                self.assertEqual((summit["picker_win_rate"], summit["atk_round_share"]), ("1.000", "0.208"))
                agents = {row["agent"]: row for row in summary["agents"]}
                self.assertEqual((agents["Neon"]["picks"], agents["Neon"]["pick_rate"]), (2, "1.000"))
                self.assertEqual((agents["Sage"]["pick_rate"], agents["Sage"]["win_rate"]), ("0.500", "1.000"))
                erde = next(row for row in summary["players"] if row["player"] == "erde")
                self.assertEqual((erde["maps"], erde["rounds"], erde["rating"], erde["kd"]), (1, 24, "1.31", "1.19"))
                self.assertEqual((erde["multikills"], erde["agents"]), (2, "Sage:1"))
                loud = next(row for row in summary["teams"] if row["team"] == "LOUD")
                self.assertEqual((loud["map_win_rate"], loud["round_win_rate"]), ("1.000", "0.542"))
                self.assertEqual((loud["atk_round_win_rate"], loud["def_round_win_rate"]), ("0.250", "0.833"))
                self.assertEqual(loud["pistol_win_rate"], "0.500")  # lost round 1, won round 13
                pistol = next(r for r in summary["economy"] if (r["buy"], r["against"]) == ("pistol", "pistol"))
                self.assertEqual((pistol["rounds"], pistol["wins"]), (4, 2))
                # One year only, so there is no separate "all" block.
                self.assertEqual({row["year"] for row in summary["maps"]}, {"2026"})

                # The check still runs once the summary folder exists. It
                # reports a problem here because the fixture keeps one map
                # of a 3:1 series, so map wins (1:0) differ from the score.
                with mock.patch("builtins.print"):
                    self.assertEqual(analyze_stats.main(), 0)
                with mock.patch("builtins.print") as printed:
                    self.assertEqual(vlr_stats.command_check(argparse.Namespace()), 1)
                report = " ".join(str(call.args[0]) for call in printed.call_args_list)
                self.assertIn("地图胜场对不上大比分的比赛 1", report)
                self.assertTrue(report.startswith("2026:"), report)


if __name__ == "__main__":
    unittest.main()
