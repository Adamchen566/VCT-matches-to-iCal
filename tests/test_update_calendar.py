import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from icalendar import Calendar

import update_calendar
from update_calendar import (
    CONFIG_PATH,
    CacheState,
    CalendarConfig,
    CalendarUpdateError,
    EventConfig,
    build_cache_json,
    build_calendar,
    build_text,
    check_match_count,
    describe_slug,
    discover_events,
    event_from_reference,
    event_title_from_html,
    is_archived,
    load_cache,
    load_config,
    match_id_from_url,
    parse_config,
    parse_event_html,
    parse_events_list,
    parse_vlr_detail_timestamp,
    ready_to_archive,
    select_events,
    validate_calendar,
    validate_records,
    write_archive,
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
TRACKED = {AMER.event_id: AMER}

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
        validate_records({}, TRACKED)
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

    def test_records_from_an_untracked_event_are_rejected(self):
        stray = {"1": dict(SAMPLE_EVENTS["706361"], match_id="1", event_id=9999)}
        with self.assertRaises(CalendarUpdateError):
            validate_records(stray, TRACKED)


class ConfigTests(unittest.TestCase):
    def test_repository_config_loads(self):
        config = load_config(CONFIG_PATH)
        self.assertTrue(config.name)
        self.assertTrue(config.discover or config.events)
        for event in config.events:
            self.assertIn(str(event.event_id), event.matches_url)
            self.assertIn(event.slug, event.matches_url)

    def test_events_are_optional_only_while_discovery_is_on(self):
        config = parse_config({"calendar": {"name": "x"}})
        self.assertTrue(config.discover)
        self.assertEqual(config.events, ())
        self.assertEqual(config.keep_finished_days, 7)
        with self.assertRaises(CalendarUpdateError):
            parse_config({"calendar": {"name": "x"}, "discovery": {"enabled": False}})

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


EVENTS_LIST_HTML = """
<a class="wf-card mod-flex event-item" href="/event/3178/vct-2027-americas-kickoff">
  <div class="event-item-title"> VCT 2027: Americas Kickoff </div>
  <span class="event-item-desc-item-status mod-upcoming">upcoming</span>
</a>
<a class="wf-card mod-flex event-item" href="/event/3161/valorant-masters-seoul-2027">
  <div class="event-item-title">Valorant Masters Seoul 2027</div>
  <span class="event-item-desc-item-status mod-ongoing">ongoing</span>
</a>
<a class="wf-card mod-flex event-item" href="/event/3179/vct-2027-america-kickoff-north-america-qualifier-playoffs">
  <div class="event-item-title">VCT 2027: America Kickoff - North America Qualifier Playoffs</div>
  <span class="event-item-desc-item-status mod-ongoing">ongoing</span>
</a>
<a class="wf-card mod-flex event-item" href="/event/2766/valorant-champions-2026">
  <div class="event-item-title">Valorant Champions 2026</div>
  <span class="event-item-desc-item-status mod-completed">completed</span>
</a>
"""

SEOUL = EventConfig(
    region="INTL",
    event_id=3161,
    slug="valorant-masters-seoul-2027",
    name="Valorant Masters Seoul 2027",
    source="discovered",
)


def completed_record(match_id, event, end_utc):
    return dict(
        SAMPLE_EVENTS["706361"],
        match_id=match_id,
        event_id=event.event_id,
        event_name=event.name,
        region=event.region,
        status="Completed",
        score1=2,
        score2=0,
        end_utc=end_utc,
    )


class SlugTests(unittest.TestCase):
    def test_tier_one_slugs_map_to_region_and_archive_name(self):
        cases = {
            "vct-2027-americas-kickoff": ("AMER", "2027_Kickoff_AMER"),
            "vct-2026-china-stage-2": ("CN", "2026_Stage_2_CN"),
            "champions-tour-2025-emea-stage-1": ("EMEA", "2025_Stage_1_EMEA"),
            "valorant-masters-santiago-2026": ("INTL", "2026_Masters_Santiago_Global"),
            "valorant-champions-2026": ("INTL", "2026_Champions_Global"),
        }
        for slug, expected in cases.items():
            self.assertEqual(describe_slug(slug), expected, slug)

    def test_qualifiers_and_other_events_are_not_tier_one(self):
        for slug in (
            "vct-2027-pacific-kickoff-last-chance",
            "vct-2027-emea-kickoff-mena-qualifier",
            "predator-league-2027-india",
            "game-changers-2024-championship-berlin",
        ):
            self.assertIsNone(describe_slug(slug), slug)

    def test_archive_name_can_be_set_or_falls_back_to_event_name(self):
        other = EventConfig(
            "CN",
            2894,
            "china-evolution-series-2026-act-1",
            "China Evolution Series 2026: Act 1",
        )
        self.assertEqual(other.archive_stem, "China_Evolution_Series_2026_Act_1")
        named = EventConfig("CN", 2894, "x", "y", archive="2026_Evolution_Act1_China")
        self.assertEqual(named.archive_stem, "2026_Evolution_Act1_China")

    def test_archive_command_accepts_id_slug_or_url(self):
        for reference in (
            "2766/valorant-champions-2026",
            "https://www.vlr.gg/event/matches/2766/valorant-champions-2026/?series_id=all",
        ):
            event = event_from_reference(reference)
            self.assertEqual((event.event_id, event.region), (2766, "INTL"))
        with self.assertRaises(CalendarUpdateError):
            event_from_reference("3236/vct-2027-pacific-kickoff-last-chance")


class EventTitleTests(unittest.TestCase):
    def test_title_comes_from_the_page_heading(self):
        html = (
            "<title>Other</title>"
            '<h1 class="event-header-main-title"> Valorant Champions 2026 </h1>'
        )
        self.assertEqual(event_title_from_html(html), "Valorant Champions 2026")

    def test_title_falls_back_to_the_title_tag(self):
        html = (
            "<title>VCT 2027: Americas Kickoff: Schedule and Results"
            " | Valorant Event | VLR.gg</title>"
        )
        self.assertEqual(event_title_from_html(html), "VCT 2027: Americas Kickoff")
        self.assertIsNone(event_title_from_html("<p>nothing</p>"))


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.statuses = parse_events_list(EVENTS_LIST_HTML)

    def test_events_list_is_parsed(self):
        self.assertEqual(set(self.statuses), {3178, 3161, 3179, 2766})
        self.assertEqual(
            self.statuses[3178],
            {
                "slug": "vct-2027-americas-kickoff",
                "name": "VCT 2027: Americas Kickoff",
                "status": "upcoming",
            },
        )

    def test_only_live_tier_one_events_are_discovered(self):
        found = discover_events(self.statuses)
        self.assertEqual([event.event_id for event in found], [3161, 3178])
        self.assertEqual([event.region for event in found], ["INTL", "AMER"])
        self.assertTrue(all(event.source == "discovered" for event in found))

    def test_configured_events_win_over_discovered_ones(self):
        mine = EventConfig(
            "AMER", 3178, "vct-2027-americas-kickoff", "My name", min_matches=5
        )
        config = CalendarConfig("x", ZoneInfo("UTC"), events=(mine,))
        selected = select_events(config, CacheState(), self.statuses)
        self.assertEqual([event.event_id for event in selected], [3161, 3178])
        self.assertEqual(selected[1].name, "My name")

    def test_ended_discovered_event_is_still_scraped_until_archived(self):
        # Seoul has finished. VLR no longer lists it as ongoing, but we still
        # hold its matches and need the final results.
        statuses = dict(self.statuses)
        statuses[3161] = dict(statuses[3161], status="completed")
        state = CacheState(
            tracked={3161: SEOUL},
            events={"1": completed_record("1", SEOUL, "2027-03-08T12:00:00Z")},
        )
        config = CalendarConfig("x", ZoneInfo("UTC"))
        selected = select_events(config, state, statuses)
        self.assertIn(3161, [event.event_id for event in selected])

    def test_vanished_upcoming_event_without_matches_is_dropped(self):
        statuses = {k: v for k, v in self.statuses.items() if k != 3161}
        state = CacheState(tracked={3161: SEOUL})
        selected = select_events(CalendarConfig("x", ZoneInfo("UTC")), state, statuses)
        self.assertNotIn(3161, [event.event_id for event in selected])

    def test_discovery_failure_keeps_following_known_events(self):
        state = CacheState(tracked={3161: SEOUL})
        selected = select_events(CalendarConfig("x", ZoneInfo("UTC")), state, None)
        self.assertEqual([event.event_id for event in selected], [3161])


class ArchiveTests(unittest.TestCase):
    NOW = datetime(2027, 3, 20, tzinfo=timezone.utc)

    def test_finished_event_waits_for_the_grace_period(self):
        records = {"1": completed_record("1", SEOUL, "2027-03-08T12:00:00Z")}
        self.assertTrue(ready_to_archive(records, "completed", self.NOW, 7))
        self.assertTrue(ready_to_archive(records, None, self.NOW, 7))
        self.assertFalse(ready_to_archive(records, "completed", self.NOW, 30))

    def test_event_is_not_archived_while_it_can_still_change(self):
        done = completed_record("1", SEOUL, "2027-03-08T12:00:00Z")
        upcoming = dict(done, match_id="2", status="Upcoming")
        self.assertFalse(
            ready_to_archive({"1": done, "2": upcoming}, "completed", self.NOW, 7)
        )
        self.assertFalse(ready_to_archive({"1": done}, "ongoing", self.NOW, 7))
        self.assertFalse(ready_to_archive({}, "completed", self.NOW, 7))

    def test_archive_files_are_written_and_mark_the_event_archived(self):
        records = {"1": completed_record("1", SEOUL, "2027-03-08T12:00:00Z")}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.multiple(
                update_calendar,
                ARCHIVE_ICS_DIR=root / "Calendar_Files",
                ARCHIVE_TEXT_DIR=root / "TEXT_Files",
                ARCHIVE_DATA_DIR=root / "data" / "archive",
            ):
                self.assertFalse(is_archived(SEOUL))
                write_archive(SEOUL, records, ZoneInfo("Australia/Sydney"))
                self.assertTrue(is_archived(SEOUL))

            stem = "2027_Masters_Seoul_Global"
            ics = (root / "Calendar_Files" / f"{stem}.ics").read_bytes()
            calendar = Calendar.from_ical(ics)
            self.assertEqual(
                str(calendar.get("X-WR-CALNAME")), "Valorant Masters Seoul 2027"
            )
            self.assertEqual(len(list(calendar.walk("VEVENT"))), 1)
            self.assertTrue((root / "TEXT_Files" / f"{stem}.txt").exists())
            data = json.loads(
                (root / "data" / "archive" / f"{stem}.json").read_text(encoding="utf-8")
            )
            self.assertEqual(data["event"]["event_id"], 3161)
            self.assertEqual(list(data["events"]), ["1"])


class CacheTests(unittest.TestCase):
    def test_tracked_events_survive_a_cache_round_trip(self):
        tracked = {AMER.event_id: AMER, 3161: SEOUL}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "matches.json"
            path.write_text(
                build_cache_json(SAMPLE_EVENTS, CONFIG, tracked), encoding="utf-8"
            )
            state = load_cache(path)
        self.assertEqual(state.tracked, tracked)
        self.assertEqual(state.events, SAMPLE_EVENTS)

    def test_cache_from_an_older_schema_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "matches.json"
            path.write_text(
                json.dumps({"schema_version": 3, "events": {"1": {}}}),
                encoding="utf-8",
            )
            state = load_cache(path)
        self.assertEqual((state.tracked, state.events), ({}, {}))


if __name__ == "__main__":
    unittest.main()
