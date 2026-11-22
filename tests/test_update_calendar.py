import unittest
from zoneinfo import ZoneInfo

from icalendar import Calendar

from update_calendar import (
    CONFIG_PATH,
    CalendarConfig,
    CalendarUpdateError,
    EventConfig,
    build_calendar,
    build_text,
    check_match_count,
    load_config,
    match_id_from_url,
    parse_config,
    parse_event_html,
    parse_vlr_detail_timestamp,
    validate_calendar,
    validate_records,
)


AMER = EventConfig(
    region="AMER",
    event_id=2977,
    slug="vct-2026-americas-stage-2",
    name="VCT 2026: Americas Stage 2",
)

CONFIG = CalendarConfig(
    name="VCT Test Calendar",
    display_timezone=ZoneInfo("Australia/Sydney"),
    events=(AMER,),
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

EVENT_PAGE_HTML = """
<div class="wf-card">
  <a href="/706361/envy-vs-leviatan-vct-2026-americas-stage-2-w2"
     class="wf-module-item match-item mod-color mod-bg-after-striped_purple mod-first">
    <div class="match-item-time">7:00 AM</div>
    <div class="match-item-vs">
      <div class="match-item-vs-team">
        <div class="match-item-vs-team-name"><div class="text-of">ENVY</div></div>
        <div class="match-item-vs-team-score">2</div>
      </div>
      <div class="match-item-vs-team">
        <div class="match-item-vs-team-name"><div class="text-of">LEVIATÁN</div></div>
        <div class="match-item-vs-team-score">1</div>
      </div>
    </div>
    <div class="match-item-eta"><div class="ml"><div class="ml-status">Completed</div></div></div>
    <div class="match-item-event text-of">
      <div class="match-item-event-series text-of">Week 2</div>
      Group Stage
    </div>
  </a>
  <a href="/706362/tbd-vs-tbd-vct-2026-americas-stage-2-gf"
     class="wf-module-item match-item mod-color mod-bg-after-striped_purple">
    <div class="match-item-vs">
      <div class="match-item-vs-team">
        <div class="match-item-vs-team-name"><div class="text-of"></div></div>
        <div class="match-item-vs-team-score">–</div>
      </div>
      <div class="match-item-vs-team">
        <div class="match-item-vs-team-name"><div class="text-of">NRG</div></div>
        <div class="match-item-vs-team-score">–</div>
      </div>
    </div>
    <div class="match-item-eta"><div class="ml"><div class="ml-status">Upcoming</div></div></div>
    <div class="match-item-event text-of">Grand Final</div>
  </a>
</div>
"""


class CalendarOutputTests(unittest.TestCase):
    def test_match_id_from_url(self):
        self.assertEqual(
            match_id_from_url(
                "https://www.vlr.gg/706361/envy-vs-leviatan"
            ),
            "706361",
        )

    def test_calendar_output_is_deterministic_and_has_stable_uid(self):
        first = build_calendar(SAMPLE_EVENTS, CONFIG)
        second = build_calendar(SAMPLE_EVENTS, CONFIG)
        self.assertEqual(first, second)

        calendar = Calendar.from_ical(first)
        events = list(calendar.walk("VEVENT"))
        self.assertEqual(len(events), 1)
        self.assertEqual(
            str(events[0].get("UID")),
            "vlr-706361@vct-calendar",
        )
        self.assertEqual(str(calendar.get("X-WR-CALNAME")), "VCT Test Calendar")

    def test_vlr_detail_timestamp_uses_havana_source_timezone(self):
        parsed = parse_vlr_detail_timestamp("2026-07-16 17:00:00")
        self.assertEqual(
            parsed.isoformat(),
            "2026-07-16T21:00:00+00:00",
        )

    def test_text_uses_configured_timezone(self):
        output = build_text(SAMPLE_EVENTS, CONFIG)
        self.assertIn("2026-07-27 07:00 AEST", output)
        self.assertIn("AMER", output)

        tokyo = CalendarConfig(
            name="VCT Test Calendar",
            display_timezone=ZoneInfo("Asia/Tokyo"),
            events=(AMER,),
        )
        self.assertIn("2026-07-27 06:00 JST", build_text(SAMPLE_EVENTS, tokyo))

    def test_event_without_published_schedule_gives_valid_empty_calendar(self):
        ical_bytes = build_calendar({}, CONFIG)
        validate_records({}, CONFIG)
        validate_calendar(ical_bytes, {})
        self.assertEqual(len(list(Calendar.from_ical(ical_bytes).walk("VEVENT"))), 0)
        self.assertIn("VCT Test Calendar", build_text({}, CONFIG))


class EventPageParsingTests(unittest.TestCase):
    def test_parses_teams_scores_status_and_phase(self):
        matches = parse_event_html(EVENT_PAGE_HTML, AMER)
        self.assertEqual([m["match_id"] for m in matches], ["706361", "706362"])

        done, upcoming = matches
        self.assertEqual((done["team1"], done["team2"]), ("ENVY", "LEVIATÁN"))
        self.assertEqual((done["score1"], done["score2"]), (2, 1))
        self.assertEqual(done["status"], "Completed")
        self.assertEqual(done["phase"], "Week 2 Group Stage")
        self.assertEqual(done["event_id"], 2977)
        self.assertEqual(done["region"], "AMER")

        self.assertEqual((upcoming["team1"], upcoming["team2"]), ("TBD", "NRG"))
        self.assertEqual((upcoming["score1"], upcoming["score2"]), (None, None))

    def test_page_without_matches_is_empty_not_an_error(self):
        self.assertEqual(parse_event_html("<div class='wf-card'></div>", AMER), [])


class MatchCountGuardTests(unittest.TestCase):
    def test_refuses_to_publish_fewer_matches_than_last_time(self):
        with self.assertRaises(CalendarUpdateError):
            check_match_count(AMER, scraped=0, cached=30)
        check_match_count(AMER, scraped=0, cached=30, allow_shrink=True)
        check_match_count(AMER, scraped=31, cached=30)

    def test_refuses_fewer_matches_than_configured_minimum(self):
        strict = EventConfig(
            region="AMER", event_id=2977, slug="s", name="n", min_matches=30
        )
        with self.assertRaises(CalendarUpdateError):
            check_match_count(strict, scraped=29, cached=0, allow_shrink=True)

    def test_records_from_an_unconfigured_event_are_rejected(self):
        stray = {"1": dict(SAMPLE_EVENTS["706361"], match_id="1", event_id=9999)}
        with self.assertRaises(CalendarUpdateError):
            validate_records(stray, CONFIG)


class ConfigTests(unittest.TestCase):
    def test_repository_config_loads(self):
        config = load_config(CONFIG_PATH)
        self.assertTrue(config.name)
        self.assertGreaterEqual(len(config.events), 1)
        for event in config.events:
            self.assertIn(str(event.event_id), event.matches_url)
            self.assertIn(event.slug, event.matches_url)

    def test_duplicate_event_ids_are_rejected(self):
        event = {"region": "AMER", "event_id": 1, "slug": "a", "name": "A"}
        with self.assertRaises(CalendarUpdateError):
            parse_config({"calendar": {"name": "x"}, "events": [event, dict(event)]})

    def test_missing_fields_and_bad_timezone_are_rejected(self):
        with self.assertRaises(CalendarUpdateError):
            parse_config({"calendar": {"name": "x"}, "events": [{"region": "AMER"}]})
        with self.assertRaises(CalendarUpdateError):
            parse_config(
                {
                    "calendar": {"name": "x", "display_timezone": "Mars/Olympus"},
                    "events": [
                        {"region": "AMER", "event_id": 1, "slug": "a", "name": "A"}
                    ],
                }
            )


if __name__ == "__main__":
    unittest.main()
