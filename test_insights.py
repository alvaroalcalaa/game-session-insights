import csv
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from insights import analyze, read_sessions, render_html

ROOT = Path(__file__).parent


class InsightsTests(unittest.TestCase):
    def setUp(self):
        self.sessions = read_sessions(ROOT / "data/demo.csv")

    def test_demo_totals(self):
        r = analyze(self.sessions, date(2026, 10, 8))
        self.assertEqual((r["players"], r["sessions"], r["total_minutes"]), (5, 9, 225))
        self.assertEqual(r["median_session_minutes"], 25)
        self.assertEqual(r["retention"]["d1"], {"eligible": 4, "retained": 3, "rate": .75})
        self.assertEqual(r["retention"]["d7"], {"eligible": 2, "retained": 1, "rate": .5})

    def test_immature_cohort_not_zero(self):
        r = analyze(self.sessions, date(2026, 10, 8))
        self.assertIsNone(r["cohorts"][-1]["d1"]["rate"])
        self.assertEqual(r["cohorts"][-1]["d1"]["eligible"], 0)

    def test_exact_day_not_rolling_retention(self):
        r = analyze(self.sessions, date(2026, 10, 9))
        # player_c came back on D1, but did not return on D7.
        self.assertEqual(r["retention"]["d7"], {"eligible": 3, "retained": 1, "rate": .3333})

    def test_zero_activity_days_present(self):
        r = analyze(self.sessions, date(2026, 10, 8))
        self.assertEqual(len(r["daily"]), 8)
        self.assertEqual(r["daily"][3]["active_players"], 0)

    def test_future_sessions_excluded(self):
        r = analyze(self.sessions, date(2026, 10, 1))
        self.assertEqual(r["excluded_sessions"], 7)
        self.assertIsNone(r["retention"]["d1"]["rate"])

    def test_empty_dataset(self):
        r = analyze([], date(2026, 10, 8))
        self.assertEqual(r["players"], 0)
        self.assertIsNone(r["median_session_minutes"])
        self.assertIsNone(r["retention"]["d7"]["rate"])

    def read_row(self, start, end, sid="s1", player="p"):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "x.csv"
            with path.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["session_id", "player_id", "start_at", "end_at"])
                writer.writerow([sid, player, start, end])
            return read_sessions(path)

    def test_offset_normalized_to_utc(self):
        s = self.read_row("2026-10-02T00:30:00+02:00", "2026-10-02T01:00:00+02:00")
        r = analyze(s, date(2026, 10, 1))
        self.assertEqual(r["daily"][0]["date"], "2026-10-01")
        self.assertEqual(r["total_minutes"], 30)

    def test_rejects_naive_timestamps_and_negative_duration(self):
        for start, end in [
            ("2026-10-01T10:00:00", "2026-10-01T11:00:00"),
            ("2026-10-01T12:00:00Z", "2026-10-01T11:00:00Z"),
        ]:
            with self.assertRaisesRegex(ValueError, "fila 2"):
                self.read_row(start, end)

    def test_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.csv"
            text = (ROOT / "data/demo.csv").read_text()
            path.write_text(text + text.splitlines()[1] + "\n")
            with self.assertRaisesRegex(ValueError, "duplicado"):
                read_sessions(path)

    def test_midnight_end_requires_next_observed_day(self):
        s = self.read_row("2026-10-01T23:30:00Z", "2026-10-02T00:00:00Z")
        self.assertEqual(analyze(s, date(2026, 10, 1))["sessions"], 0)
        self.assertEqual(analyze(s, date(2026, 10, 2))["sessions"], 1)

    def test_html_escapes_title(self):
        result = render_html(analyze([], date(2026, 10, 8)), "<script>alert(1)</script>")
        self.assertNotIn("<script>", result)
        self.assertIn("&lt;script&gt;", result)

    def test_cli_exports_and_protects_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sessions.csv"
            source.write_bytes((ROOT / "data/demo.csv").read_bytes())
            output = Path(directory) / "report.html"
            command = [sys.executable, str(ROOT / "insights.py"), str(source),
                       "--as-of", "2026-10-08", "--html", str(output)]
            good = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertIn("Retención D7", output.read_text())
            bad = subprocess.run(command[:-1] + [str(source)], capture_output=True, text=True)
            self.assertEqual(bad.returncode, 2)
            self.assertTrue(source.read_text().startswith("session_id,"))


if __name__ == "__main__":
    unittest.main()
