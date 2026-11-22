"""Checks on the calendar files committed to the repository."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def calendar_files() -> list[Path]:
    files = [ROOT / "vct_OnGoing.ics"]
    files += sorted((ROOT / "Calendar_Files").glob("*.ics"))
    files += sorted((ROOT / "feeds").rglob("*.ics"))
    return files


class LineEndingTests(unittest.TestCase):
    def test_every_calendar_uses_crlf_line_endings(self):
        """iCalendar requires CRLF, and git must not rewrite it.

        .gitattributes marks *.ics as -text for this. Without it git stores
        the files with bare LF, the updater sees a difference on every run,
        and older files end up with doubled carriage returns.
        """
        files = calendar_files()
        self.assertGreater(len(files), 100)
        for path in files:
            data = path.read_bytes()
            name = path.relative_to(ROOT).as_posix()
            self.assertNotIn(b"\r\r", data, f"{name} has doubled carriage returns")
            self.assertEqual(
                data.count(b"\n"),
                data.count(b"\r\n"),
                f"{name} has bare LF line endings",
            )
            self.assertTrue(data.endswith(b"END:VCALENDAR\r\n"), name)


if __name__ == "__main__":
    unittest.main()
