import unittest
from icalendar import Calendar

from update_stage2_calendar import (
    build_calendar,
    build_text,
    match_id_from_url,
    parse_vlr_detail_timestamp,
)


SAMPLE_EVENTS = {
    "706361": {
        "match_id": "706361",
        "event_id": 2977,
        "event_name": "VCT 2026: Americas Stage 2",
        "region": "AMER",
        "url": "https://www.vlr.gg/706361/envy-vs-leviatan",
        "team1": "ENVY",
        "team2": "LEVIATÁN",
        "score1": None,
        "score2": None,
        "status": "Upcoming",
        "phase": "Week 2 Group Stage",
        "best_of": 3,
        "start_utc": "2026-07-26T21:00:00Z",
        "end_utc": "2026-07-27T00:00:00Z",
        "sequence": 0,
        "updated_at": "2026-07-26T05:00:00Z",
    }
}


class Stage2CalendarTests(unittest.TestCase):
    def test_match_id_from_url(self):
        self.assertEqual(
            match_id_from_url(
                "https://www.vlr.gg/706361/envy-vs-leviatan"
            ),
            "706361",
        )

    def test_calendar_output_is_deterministic_and_has_stable_uid(self):
        first = build_calendar(SAMPLE_EVENTS)
        second = build_calendar(SAMPLE_EVENTS)
        self.assertEqual(first, second)

        calendar = Calendar.from_ical(first)
        events = list(calendar.walk("VEVENT"))
        self.assertEqual(len(events), 1)
        self.assertEqual(
            str(events[0].get("UID")),
            "vlr-706361@vct-calendar",
        )

    def test_vlr_detail_timestamp_uses_havana_source_timezone(self):
        parsed = parse_vlr_detail_timestamp("2026-07-16 17:00:00")
        self.assertEqual(
            parsed.isoformat(),
            "2026-07-16T21:00:00+00:00",
        )

    def test_text_uses_sydney_timezone(self):
        output = build_text(SAMPLE_EVENTS)
        self.assertIn("2026-07-27 07:00 AEST", output)
        self.assertIn("AMER", output)


if __name__ == "__main__":
    unittest.main()
