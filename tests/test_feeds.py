import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from icalendar import Calendar

import update_calendar
from calendar_library import load_matches
from live_check import active_matches
from update_calendar import (
    CalendarConfig,
    CalendarUpdateError,
    EventConfig,
    build_calendar,
    build_feeds,
    describe_archive,
    list_archives,
    merge_teams,
    parse_config,
    summary_text,
    team_slug,
    validate_feeds,
    write_feeds,
)


PAC = EventConfig("PAC", 3181, "vct-2027-pacific-kickoff", "VCT 2027: Pacific Kickoff")
SEOUL = EventConfig("INTL", 3161, "valorant-masters-seoul-2027", "Valorant Masters Seoul 2027")
CONFIG = CalendarConfig(name="VCT Matches", display_timezone=ZoneInfo("Australia/Sydney"))
TRACKED = {PAC.event_id: PAC, SEOUL.event_id: SEOUL}


def record(match_id, event, team1, team2, start, status="Upcoming", score=(None, None), best_of=3):
    return {
        "match_id": match_id,
        "event_id": event.event_id,
        "event_name": event.name,
        "region": event.region,
        "url": f"https://www.vlr.gg/{match_id}/x",
        "team1": team1,
        "team2": team2,
        "score1": score[0],
        "score2": score[1],
        "status": status,
        "phase": "Group Stage",
        "best_of": best_of,
        "start_utc": start,
        "end_utc": start,
        "sequence": 0,
        "updated_at": "2027-01-01T00:00:00Z",
    }


EVENTS = {
    "1": record("1", PAC, "Paper Rex", "T1", "2027-01-11T08:00:00Z", "Completed", (2, 1)),
    "2": record("2", PAC, "DRX", "TBD", "2027-01-12T08:00:00Z"),
    "3": record("3", SEOUL, "Paper Rex", "LEVIATÁN", "2027-02-20T08:00:00Z", best_of=5),
}


def events_in(ical_bytes):
    return [str(e.get("SUMMARY")) for e in Calendar.from_ical(ical_bytes).walk("VEVENT")]


class TitleTests(unittest.TestCase):
    def test_score_replaces_vs_once_a_match_has_one(self):
        self.assertEqual(summary_text(EVENTS["1"], True), "[PAC] Paper Rex 2:1 T1")

    def test_series_format_is_shown_before_the_match(self):
        self.assertEqual(summary_text(EVENTS["3"], True), "[INTL] Paper Rex vs LEVIATÁN (Bo5)")
        unknown = dict(EVENTS["2"], best_of=None)
        self.assertEqual(summary_text(unknown, True), "[PAC] DRX vs TBD")

    def test_scores_can_be_kept_out_of_titles(self):
        self.assertEqual(summary_text(EVENTS["1"], False), "[PAC] Paper Rex vs T1 (Bo3)")
        config = parse_config({"calendar": {"name": "x", "score_in_title": False}})
        self.assertFalse(config.score_in_title)
        self.assertEqual(
            events_in(build_calendar({"1": EVENTS["1"]}, config)),
            ["[PAC] Paper Rex vs T1 (Bo3)"],
        )

    def test_gui_reader_understands_the_new_titles(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live.ics"
            path.write_bytes(build_calendar(EVENTS, CONFIG))
            matches = load_matches(path)
        self.assertEqual(
            [(m.region, m.team1, m.team2, m.score) for m in matches],
            [
                ("PAC", "Paper Rex", "T1", "2:1"),
                ("PAC", "DRX", "TBD", "-"),
                ("INTL", "Paper Rex", "LEVIATÁN", "-"),
            ],
        )


class TeamTests(unittest.TestCase):
    def test_slugs_are_file_name_safe(self):
        self.assertEqual(team_slug("LEVIATÁN"), "leviatan")
        self.assertEqual(team_slug("KRÜ Esports"), "kru-esports")
        self.assertEqual(team_slug("100 Thieves"), "100-thieves")
        self.assertTrue(team_slug("夜莲").startswith("team-"))
        self.assertEqual(team_slug("夜莲"), team_slug("夜莲"))

    def test_home_region_comes_from_a_regional_league(self):
        teams = merge_teams({}, EVENTS)
        self.assertEqual(set(teams), {"paper-rex", "t1", "drx", "leviatan"})  # no TBD
        self.assertEqual(teams["paper-rex"]["region"], "PAC")
        self.assertEqual(teams["leviatan"]["region"], "INTL")

        later = {"9": record("9", EventConfig("AMER", 1, "s", "n"), "LEVIATÁN", "LOUD", "2027-03-01T00:00:00Z")}
        self.assertEqual(merge_teams(teams, later)["leviatan"]["region"], "AMER")
        # An international event never overwrites a known home region.
        self.assertEqual(merge_teams(teams, {"3": EVENTS["3"]})["paper-rex"]["region"], "PAC")


class FeedTests(unittest.TestCase):
    def setUp(self):
        self.files = build_feeds(EVENTS, TRACKED, CONFIG, {})
        self.index = json.loads(self.files["index.json"])

    def test_every_default_region_gets_a_feed_even_when_empty(self):
        self.assertEqual(
            [(r["code"], r["matches"]) for r in self.index["regions"]],
            [("AMER", 0), ("PAC", 2), ("EMEA", 0), ("CN", 0), ("INTL", 1)],
        )
        self.assertEqual(
            events_in(self.files["region/PAC.ics"]),
            ["[PAC] Paper Rex 2:1 T1", "[PAC] DRX vs TBD (Bo3)"],
        )
        self.assertEqual(events_in(self.files["region/AMER.ics"]), [])

    def test_team_feed_holds_that_teams_matches_across_events(self):
        self.assertEqual(
            events_in(self.files["team/paper-rex.ics"]),
            ["[PAC] Paper Rex 2:1 T1", "[INTL] Paper Rex vs LEVIATÁN (Bo5)"],
        )
        calendar = Calendar.from_ical(self.files["team/paper-rex.ics"])
        self.assertEqual(str(calendar.get("X-WR-CALNAME")), "VCT Paper Rex")
        self.assertNotIn("team/tbd.ics", self.files)

    def test_known_team_keeps_an_empty_feed_after_its_event_ends(self):
        known = {"sentinels": {"name": "Sentinels", "region": "AMER"}}
        files = build_feeds(EVENTS, TRACKED, CONFIG, known)
        self.assertEqual(events_in(files["team/sentinels.ics"]), [])
        entry = next(t for t in json.loads(files["index.json"])["teams"] if t["slug"] == "sentinels")
        self.assertEqual((entry["name"], entry["region"], entry["matches"]), ("Sentinels", "AMER", 0))

    def test_index_lists_what_is_next_and_is_reproducible(self):
        self.assertEqual(
            [(m["team1"], m["team2"], m["best_of"]) for m in self.index["upcoming"]],
            [("DRX", "TBD", 3), ("Paper Rex", "LEVIATÁN", 5)],
        )
        self.assertEqual(self.index["calendar"]["matches"], 3)
        self.assertEqual(self.files, build_feeds(EVENTS, TRACKED, CONFIG, {}))

    def test_written_feeds_validate_and_a_stale_index_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.multiple(update_calendar, ROOT=root, FEEDS_DIR=root / "feeds"):
                write_feeds(self.files)
                self.assertEqual(validate_feeds(), 5 + 4)
                (root / "feeds" / "team" / "t1.ics").write_bytes(build_calendar({}, CONFIG))
                with self.assertRaises(CalendarUpdateError):
                    validate_feeds()


class ArchiveIndexTests(unittest.TestCase):
    """What the web page's season review reads."""

    def test_archive_names_give_year_label_and_region(self):
        self.assertEqual(describe_archive("2026_Stage_2_CN"), ("2026", "Stage 2", "CN"))
        self.assertEqual(describe_archive("2026_Masters_London_Global"), ("2026", "Masters London", "INTL"))
        self.assertEqual(describe_archive("2025_China_Evolution_Act1"), ("2025", "China Evolution Act1", "CN"))
        self.assertIsNone(describe_archive("vct_completed"))

    def test_each_archive_gets_a_results_file_and_the_newest_is_marked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_dir = root / "Calendar_Files"
            archive_dir.mkdir()
            pac = {"1": EVENTS["1"]}
            intl = {"3": {**EVENTS["3"], "score1": 3, "score2": 1, "status": "Completed"}}
            (archive_dir / "2026_Stage_2_PAC.ics").write_bytes(build_calendar(pac, CONFIG))
            (archive_dir / "2026_Champions_Global.ics").write_bytes(build_calendar(intl, CONFIG))
            (archive_dir / "vct_completed.ics").write_bytes(build_calendar({}, CONFIG))
            with mock.patch.multiple(
                update_calendar, ROOT=root, FEEDS_DIR=root / "feeds", ARCHIVE_ICS_DIR=archive_dir
            ):
                archives, files = list_archives()
                self.assertEqual(
                    [(a["label"], a["region"], a["matches"]) for a in archives],
                    [("Champions", "INTL", 1), ("Stage 2", "PAC", 1)],
                )
                results = json.loads(files["matches/2026_Stage_2_PAC.json"])
                self.assertEqual(results["title"], "2026 Stage 2")
                self.assertEqual(
                    results["matches"],
                    [{"start_utc": EVENTS["1"]["start_utc"], "team1": "Paper Rex", "team2": "T1", "score1": 2, "score2": 1}],
                )
                self.assertEqual(archives[1]["start"], EVENTS["1"]["start_utc"])

                built = build_feeds(EVENTS, TRACKED, CONFIG, {})
                index = json.loads(built["index.json"])
                self.assertEqual(index["latest"], "feeds/matches/2026_Champions_Global.json")
                write_feeds(built)
                validate_feeds()
                (root / "feeds" / "matches" / "2026_Stage_2_PAC.json").write_text(
                    '{"matches": []}', encoding="utf-8"
                )
                with self.assertRaises(CalendarUpdateError):
                    validate_feeds()


class LiveCheckTests(unittest.TestCase):
    def at(self, text):
        return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)

    def test_update_window_opens_before_the_match_and_covers_a_long_series(self):
        upcoming = {"2": EVENTS["2"]}  # starts 2027-01-12 08:00 UTC
        self.assertEqual(active_matches(upcoming, self.at("2027-01-12T06:00:00")), [])
        self.assertEqual(len(active_matches(upcoming, self.at("2027-01-12T06:45:00"))), 1)
        self.assertEqual(len(active_matches(upcoming, self.at("2027-01-12T13:00:00"))), 1)
        self.assertEqual(active_matches(upcoming, self.at("2027-01-12T21:00:00")), [])

    def test_finished_matches_never_trigger_updates(self):
        finished = {"1": EVENTS["1"]}
        self.assertEqual(active_matches(finished, self.at("2027-01-11T09:00:00")), [])
        self.assertEqual(active_matches({}, self.at("2027-01-11T09:00:00")), [])


if __name__ == "__main__":
    unittest.main()
