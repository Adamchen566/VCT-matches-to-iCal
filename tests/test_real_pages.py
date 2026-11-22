"""Parser tests against markup saved from real vlr.gg pages.

The fixtures in tests/fixtures/ are trimmed copies of real pages, so these
tests break when the parsers stop matching the markup VLR actually serves.
"""

import unittest
from dataclasses import replace
from pathlib import Path

from update_calendar import (
    DEFAULT_CANARY,
    CalendarUpdateError,
    check_canary_html,
    discover_events,
    event_title_from_html,
    parse_config,
    parse_event_html,
    parse_events_list,
    parse_match_detail_html,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class EventMatchesPageTests(unittest.TestCase):
    def setUp(self):
        self.html = fixture("event_matches.html")
        self.matches = parse_event_html(self.html, DEFAULT_CANARY)

    def test_every_match_row_is_found(self):
        self.assertEqual(
            [match["match_id"] for match in self.matches],
            ["753455", "753454", "754737"],
        )

    def test_teams_scores_status_and_phase(self):
        opener, _, final = self.matches
        self.assertEqual(
            (opener["team1"], opener["score1"], opener["score2"], opener["team2"]),
            ("Team Liquid", 1, 2, "Paper Rex"),
        )
        self.assertEqual(opener["status"], "Completed")
        self.assertEqual(opener["phase"], "Opening (C) Group Stage")
        self.assertEqual(
            (final["team1"], final["score1"], final["score2"], final["team2"]),
            ("LOUD", 3, 1, "Team Vitality"),
        )
        self.assertEqual(
            final["url"],
            "https://www.vlr.gg/754737/"
            "loud-vs-team-vitality-valorant-champions-2026-gf",
        )

    def test_event_title(self):
        self.assertEqual(event_title_from_html(self.html), "Valorant Champions 2026")


class MatchDetailPageTests(unittest.TestCase):
    def test_start_time_and_series_format(self):
        timing = parse_match_detail_html(fixture("match_detail.html"), "url")
        # The page shows this final at 5:00 PM AEDT on 18 October 2026.
        self.assertEqual(timing["start_utc"], "2026-10-18T06:00:00Z")
        # "Bo5" sits in the second note node, after the "final" state.
        self.assertEqual(timing["best_of"], 5)
        self.assertEqual(timing["end_utc"], "2026-10-18T11:00:00Z")

    def test_page_without_timestamp_is_an_error(self):
        with self.assertRaises(CalendarUpdateError):
            parse_match_detail_html("<div class='match-header'></div>", "url")


class EventsListPageTests(unittest.TestCase):
    def setUp(self):
        self.statuses = parse_events_list(fixture("events_list.html"))

    def test_events_and_statuses_are_read(self):
        self.assertEqual(
            {event_id: info["status"] for event_id, info in self.statuses.items()},
            {
                3177: "ongoing",
                3239: "ongoing",
                3178: "upcoming",
                3161: "upcoming",
                3163: "upcoming",
                2766: "completed",
            },
        )
        self.assertEqual(self.statuses[3178]["name"], "VCT 2027: Americas Kickoff")

    def test_only_live_tier_one_events_are_followed(self):
        # The Türkiye qualifier and Predator League are ongoing but not tier 1;
        # Champions 2026 is tier 1 but already completed.
        self.assertEqual(
            [event.event_id for event in discover_events(self.statuses)],
            [3161, 3163, 3178],
        )


class CanaryTests(unittest.TestCase):
    def test_passes_while_the_page_still_parses(self):
        canary = replace(DEFAULT_CANARY, min_matches=3)
        self.assertEqual(check_canary_html(fixture("event_matches.html"), canary), 3)

    def test_fails_when_the_page_no_longer_parses(self):
        redesigned = fixture("event_matches.html").replace("match-item", "match-row")
        with self.assertRaises(CalendarUpdateError):
            check_canary_html(redesigned, replace(DEFAULT_CANARY, min_matches=3))

    def test_canary_is_on_by_default_and_can_be_changed_or_disabled(self):
        self.assertEqual(parse_config({"calendar": {"name": "x"}}).canary, DEFAULT_CANARY)
        off = parse_config({"calendar": {"name": "x"}, "canary": {"enabled": False}})
        self.assertIsNone(off.canary)
        custom = parse_config(
            {
                "calendar": {"name": "x"},
                "canary": {"event_id": 2765, "slug": "valorant-masters-london-2026", "min_matches": 24},
            }
        )
        self.assertEqual((custom.canary.event_id, custom.canary.min_matches), (2765, 24))
        with self.assertRaises(CalendarUpdateError):
            parse_config({"calendar": {"name": "x"}, "canary": {"event_id": 2765}})


if __name__ == "__main__":
    unittest.main()
