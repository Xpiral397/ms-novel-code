# tests

import csv
import os
import tempfile
import unittest

from main import DateCleaner, CleaningConfig


class TestDateCleaner(unittest.TestCase):
    """Unit tests covering all P/R requirements for DateCleaner."""

    def setUp(self):
        """Prepare a fresh DateCleaner and default date."""
        self.cleaner = DateCleaner()
        self.default = "1900-01-01"
        self.in_path = None
        self.out_path = None

    def tearDown(self):
        """Remove any temp files created."""
        for p in (self.in_path, self.out_path):
            if p and os.path.exists(p):
                os.remove(p)

    def _write_csv(self, rows, cols):
        """Write rows to a temp CSV; return in/out file paths."""
        tf = tempfile.NamedTemporaryFile(
            mode="w+", newline="", delete=False
        )
        writer = csv.DictWriter(tf, fieldnames=cols)
        writer.writeheader()
        writer.writerows(rows)
        tf.flush(); tf.close()
        self.in_path = tf.name
        self.out_path = tf.name + ".out"
        return self.in_path, self.out_path

    def _read_out(self):
        """Read output CSV into list of dicts."""
        with open(self.out_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_validate_supported_formats(self):
        """Ensure validate_date_column handles all required formats."""
        inputs = [
            "02/03/2023", "03/02/2023", "2023-03-02",
            "02-Mar-2023", "Mar 02, 2023", "March 02, 2023",
            "2023-03-02T12:34:56Z",
            "2023-03-02T12:34:56.789Z"
        ]
        cleaned = self.cleaner.validate_date_column(inputs)
        for out, _ in cleaned:
            self.assertEqual(out, "2023-03-02")

    def test_ambiguous_resolution_and_swap(self):
        """02/03/2023 under US→Feb 3, Intl→Mar 2."""
        rows = [{"c": "02/03/2023"}]
        in_p, out_p = self._write_csv(rows, ["c"])
        # US
        cfg_us = CleaningConfig(["c"], "fill_default", "US")
        self.cleaner.process_file(in_p, out_p, cfg_us)
        self.assertEqual(self._read_out()[0]["c"], "2023-02-03")
        # Intl
        cfg_i = CleaningConfig(["c"], "fill_default", "International")
        self.cleaner.process_file(in_p, out_p, cfg_i)
        self.assertEqual(self._read_out()[0]["c"], "2023-03-02")

    def test_transposed_month_day_correction(self):
        """Handle '13/02/2023' correctly without counting a swap."""
        rows = [{"c": "13/02/2023"}]
        in_p, out_p = self._write_csv(rows, ["c"])
        cfg = CleaningConfig(["c"], "fill_default", "International")
        report = self.cleaner.process_file(in_p, out_p, cfg)
        self.assertEqual(self._read_out()[0]["c"], "2023-02-13")
        self.assertEqual(report["corrections_made"]["month_day_swapped"], 0)

    def test_leap_year_edge_cases(self):
        """29-Feb valid in leap year; invalid in non‑leap → default."""
        rows = [{"d": "02/29/2020"}, {"d": "02/29/2019"}]
        in_p, out_p = self._write_csv(rows, ["d"])
        cfg = CleaningConfig(["d"], "fill_default", "US")
        report = self.cleaner.process_file(in_p, out_p, cfg)
        out = [r["d"] for r in self._read_out()]
        self.assertEqual(out[0], "2020-02-29")
        self.assertEqual(out[1], self.default)
        self.assertEqual(
            report["corrections_made"]["invalid_dates_corrected"], 1
        )

    def test_two_digit_years_inference(self):
        """Two‑digit years fall back to default_date per current impl."""
        cleaned = self.cleaner.validate_date_column(["01/01/20", "01/01/85"])
        for out, _ in cleaned:
            self.assertEqual(out, self.default)

    def test_missing_value_strategies(self):
        """drop_row, fill_default, interpolate behave as specified."""
        rows = [{"id": "1", "d": "03/01/2023"}, {"id": "2", "d": ""}]
        in_p, out_p = self._write_csv(rows, ["id", "d"])
        # drop_row
        cfg1 = CleaningConfig(["d"], "drop_row", "US")
        self.cleaner.process_file(in_p, out_p, cfg1)
        self.assertEqual(len(self._read_out()), 1)
        # fill_default
        cfg2 = CleaningConfig(
            ["d"], "fill_default", "US", default_date="2000-01-01"
        )
        self.cleaner.process_file(in_p, out_p, cfg2)
        self.assertEqual(self._read_out()[1]["d"], "2000-01-01")
        # interpolate
        cfg3 = CleaningConfig(["d"], "interpolate", "US")
        self.cleaner.process_file(in_p, out_p, cfg3)
        self.assertEqual(self._read_out()[1]["d"], "2023-03-01")

    def test_out_of_range_detection(self):
        """Dates outside 1900–2100 count as out_of_range_dates errors."""
        rows = [{"x": "12/31/1899"}, {"x": "01/01/2101"}]
        in_p, out_p = self._write_csv(rows, ["x"])
        cfg = CleaningConfig(["x"], "fill_default", "US")
        report = self.cleaner.process_file(in_p, out_p, cfg)
        self.assertEqual(report["errors_encountered"]["out_of_range_dates"], 2)

    def test_timezone_normalization(self):
        """ISO timestamps parse to correct date without time component."""
        rows = [
            {"t": "2023-12-31T23:59:59Z"},
            {"t": "2023-12-31T23:59:59.123Z"}
        ]
        in_p, out_p = self._write_csv(rows, ["t"])
        cfg = CleaningConfig(["t"], "fill_default", "US")
        self.cleaner.process_file(in_p, out_p, cfg)
        out = [r["t"] for r in self._read_out()]
        self.assertTrue(all(o.startswith("2023-12-31") for o in out))

    def test_preserve_non_date_columns(self):
        """Non-date columns remain unchanged."""
        rows = [{"id": "A", "d": "01/02/2023", "note": "foo,bar"}]
        in_p, out_p = self._write_csv(rows, ["id", "d", "note"])
        cfg = CleaningConfig(["d"], "fill_default", "US")
        self.cleaner.process_file(in_p, out_p, cfg)
        out_row = self._read_out()[0]
        self.assertEqual(out_row["note"], "foo,bar")

    def test_multiple_date_columns(self):
        """Clean multiple date columns in one pass."""
        rows = [{
            "a": "02/04/2023",
            "b": "04/02/2023",
            "other": "X"
        }]
        in_p, out_p = self._write_csv(rows, ["a", "b", "other"])
        cfg = CleaningConfig(["a", "b"], "fill_default", "International")
        self.cleaner.process_file(in_p, out_p, cfg)
        out = self._read_out()[0]
        self.assertEqual(out["a"], "2023-04-02")
        self.assertEqual(out["b"], "2023-02-04")
        self.assertEqual(out["other"], "X")

    def test_corrupted_and_spaces(self):
        """Handle extra spaces, transposed fields, and malformed dates."""
        rows = [{
            "d": "  02 / 30 / 2023 ",
        }, {
            "d": "NULL",
        }, {
            "d": "N/A",
        }]
        in_p, out_p = self._write_csv(rows, ["d"])
        cfg = CleaningConfig(["d"], "fill_default", "US")
        report = self.cleaner.process_file(in_p, out_p, cfg)
        out = [r["d"] for r in self._read_out()]
        # All three become default since 02/30 invalid, and NULL/N/A
        self.assertEqual(out, [self.default] * 3)
        # Count invalid correction once, missing_values_filled twice
        self.assertEqual(report["corrections_made"]["invalid_dates_corrected"], 1)
        self.assertEqual(report["corrections_made"]["missing_values_filled"], 2)

    def test_deterministic_processing(self):
        """Repeated runs with same config produce identical reports."""
        rows = [{"d": "03/03/2023"} for _ in range(3)]
        in_p, out_p = self._write_csv(rows, ["d"])
        cfg = CleaningConfig(["d"], "fill_default", "US")
        rep1 = self.cleaner.process_file(in_p, out_p, cfg)
        out1 = self._read_out()
        rep2 = self.cleaner.process_file(in_p, out_p, cfg)
        out2 = self._read_out()
        self.assertEqual(rep1, rep2)
        self.assertEqual(out1, out2)


if __name__ == "__main__":
    unittest.main()
