import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from calendar_library import (
    ARCHIVE_SUBSCRIBE_BASE,
    LIVE_GROUP,
    LIVE_SUBSCRIBE_URL,
    OTHER_GROUP,
    MatchRow,
    describe_archive_name,
    group_names,
    list_calendars,
    load_matches,
    score_matrix,
)


# Written by update_calendar.py.
NEW_FORMAT = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//VCT Calendar//Adamchen566//EN
BEGIN:VEVENT
SUMMARY:[CN] Wolves Esports vs Titan Esports Club
DTSTART:20260709T080000Z
DTEND:20260709T110000Z
UID:vlr-701025@vct-calendar
DESCRIPTION:VCT 2026: China Stage 2\\n状态：Completed\\n比分：2:0\\nVLR：https://www.vlr.gg/701025/x
LOCATION:VCT CN
END:VEVENT
BEGIN:VEVENT
SUMMARY:[CN] TBD vs Nova Esports
DTSTART:20260708T080000Z
DTEND:20260708T110000Z
UID:vlr-701026@vct-calendar
DESCRIPTION:VCT 2026: China Stage 2\\n状态：Upcoming\\n比分：TBD\\nVLR：https://www.vlr.gg/701026/x
LOCATION:VCT CN
END:VEVENT
END:VCALENDAR
"""

# Written by the retired ics.py based scraper, including its doubled "\r".
OLD_FORMAT = (
    "BEGIN:VCALENDAR\r\r\n"
    "VERSION:2.0\r\r\n"
    "PRODID:ics.py - http://git.io/lLljaA\r\r\n"
    "BEGIN:VEVENT\r\r\n"
    "DESCRIPTION:Score: 1:2\\nVLR: https://www.vlr.gg/event/matches/466/x\r\r\n"
    "DTEND:20210911T160000Z\r\r\n"
    "LOCATION:Global Score: 1:2\r\r\n"
    "DTSTART:20210911T130000Z\r\r\n"
    "SUMMARY:Vision Strikers vs Paper Rex\r\r\n"
    "UID:2333196f@2333.org\r\r\n"
    "END:VEVENT\r\r\n"
    "BEGIN:VEVENT\r\r\n"
    "DESCRIPTION:Score: 0:0\r\r\n"
    "DTEND:20210912T160000Z\r\r\n"
    "LOCATION:Global Score: 0:0\r\r\n"
    "DTSTART:20210912T130000Z\r\r\n"
    "SUMMARY:[TBD] Acend vs Gambit\r\r\n"
    "UID:2333196g@2333.org\r\r\n"
    "END:VEVENT\r\r\n"
    "END:VCALENDAR\r\r\n"
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return path


class LoadMatchesTests(unittest.TestCase):
    def test_reads_calendars_written_by_the_updater(self):
        with tempfile.TemporaryDirectory() as tmp:
            matches = load_matches(write(Path(tmp) / "new.ics", NEW_FORMAT))

        upcoming, played = matches  # earliest first
        self.assertEqual(
            (played.region, played.team1, played.team2, played.score),
            ("CN", "Wolves Esports", "Titan Esports Club", "2:0"),
        )
        self.assertEqual(
            played.start, datetime(2026, 7, 9, 8, 0, tzinfo=timezone.utc)
        )
        self.assertEqual((upcoming.team1, upcoming.score), ("TBD", "-"))

    def test_reads_older_calendars_with_doubled_carriage_returns(self):
        with tempfile.TemporaryDirectory() as tmp:
            matches = load_matches(write(Path(tmp) / "old.ics", OLD_FORMAT))

        first, second = matches
        self.assertEqual(
            (first.region, first.team1, first.team2, first.score),
            ("Global", "Vision Strikers", "Paper Rex", "1:2"),
        )
        # The old "[TBD]" marker is not a region and not part of the team name.
        self.assertEqual((second.region, second.team1), ("Global", "Acend"))


class ListCalendarsTests(unittest.TestCase):
    def test_archive_names_split_into_year_and_title(self):
        self.assertEqual(describe_archive_name("2026_Stage_2_CN"), ("2026", "Stage 2 CN"))
        self.assertEqual(
            describe_archive_name("2025_China_Evolution_Act1"),
            ("2025", "China Evolution Act1"),
        )
        self.assertEqual(
            describe_archive_name("vct_completed"), (OTHER_GROUP, "vct completed")
        )

    def test_live_calendar_comes_first_then_newest_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "vct_OnGoing.ics", NEW_FORMAT)
            for name in ("2024_Kickoff_CN", "2026_Stage_2_CN", "2026_Kickoff_CN", "vct_completed"):
                write(root / "Calendar_Files" / f"{name}.ics", NEW_FORMAT)
            entries = list_calendars(root)

        self.assertEqual(
            [(entry.group, entry.title) for entry in entries],
            [
                (LIVE_GROUP, "当前赛事"),
                ("2026", "Kickoff CN"),
                ("2026", "Stage 2 CN"),
                ("2024", "Kickoff CN"),
                (OTHER_GROUP, "vct completed"),
            ],
        )
        self.assertEqual(group_names(entries), [LIVE_GROUP, "2026", "2024", OTHER_GROUP])

    def test_subscription_links_point_at_published_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "vct_OnGoing.ics", NEW_FORMAT)
            write(root / "Calendar_Files" / "2026_Stage_2_CN.ics", NEW_FORMAT)
            live, archived = list_calendars(root)

        self.assertEqual(live.subscribe_url, LIVE_SUBSCRIBE_URL)
        self.assertEqual(
            archived.subscribe_url, ARCHIVE_SUBSCRIBE_BASE + "2026_Stage_2_CN.ics"
        )


class ScoreMatrixTests(unittest.TestCase):
    def test_counts_maps_won_against_each_opponent(self):
        def match(team1, team2, score1, score2):
            return MatchRow(None, "CN", team1, team2, score1, score2)

        teams, matrix = score_matrix(
            [
                match("B", "A", 2, 1),
                match("A", "B", 2, 0),
                match("A", "C", None, None),  # not played
                match("A", "C", 0, 0),  # placeholder score in older files
            ]
        )
        self.assertEqual(teams, ["A", "B"])
        self.assertEqual(matrix, [[0, 3], [2, 0]])

    def test_no_scores_means_no_matrix(self):
        self.assertEqual(score_matrix([]), ([], []))


if __name__ == "__main__":
    unittest.main()
