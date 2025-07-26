import calendar
import csv
import json
import re
import sys
import time
from collections import Counter, deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Optional, Tuple

__all__ = ["CleaningConfig", "DateCleaner"]


@dataclass(slots=True, frozen=True)
class CleaningConfig:
    date_columns: List[str]
    missing_strategy: str
    ambiguous_format_preference: str
    output_format: str = "ISO"
    default_date: str = "1900-01-01"
    interpolation_window: int = 5
    sample_rows: int = 200

    def __post_init__(self) -> None:
        if self.missing_strategy not in {
            "drop_row",
            "fill_default",
            "interpolate",
        }:
            raise ValueError(
                "missing_strategy must be drop_row | fill_default | interpolate",
            )

        if self.ambiguous_format_preference not in {"US", "International", "AUTO"}:
            raise ValueError(
                "ambiguous_format_preference must be US | International | AUTO",
            )

        try:
            date.fromisoformat(self.default_date)
        except ValueError as exc:
            raise ValueError(
                "default_date must be ISO-8601 YYYY-MM-DD") from exc

        if self.interpolation_window < 1:
            raise ValueError("interpolation_window must be ≥ 1")
        if self.sample_rows < 1:
            raise ValueError("sample_rows must be ≥ 1")

    @property
    def strftime(self) -> str:  # noqa: D401
        return "%Y-%m-%d" if self.output_format == "ISO" else self.output_format


class DateCleaner:
    def process_file(
        self,
        input_path: str | Path,
        output_path: str | Path,
        config: CleaningConfig,
    ) -> Dict[str, object]:
        t0 = time.perf_counter()

        in_path = Path(input_path)
        out_path = Path(output_path)
        audit_path = out_path.with_suffix(f"{out_path.suffix}.audit.jsonl")

        encoding = self._detect_encoding(in_path)
        reader = csv.reader(in_path.open("r", encoding=encoding, newline=""))
        writer = csv.writer(out_path.open("w", encoding="utf-8", newline=""))
        audit_fh = audit_path.open("w", encoding="utf-8")

        try:
            header = next(reader)
        except StopIteration:
            return self._fresh_stats(config, 0, time.perf_counter() - t0)

        writer.writerow(header)
        col_indices = {h: i for i, h in enumerate(
            header) if h in config.date_columns}

        if not col_indices:
            writer.writerows(reader)
            audit_fh.close()
            return self._fresh_stats(config, 0, time.perf_counter() - t0)

        col_modes = self._sample_modes(reader, col_indices, config, encoding)
        reader = csv.reader(in_path.open("r", encoding=encoding, newline=""))
        next(reader)

        stats = self._fresh_stats(config, len(col_indices), 0.0)
        window: Deque[Tuple[int, List[str]]] = deque(
            maxlen=config.interpolation_window * 2 + 1,
        )

        for row_idx, raw_row in enumerate(reader, start=1):
            stats["total_rows"] += 1
            row = self._normalise_row_len(raw_row, len(header))
            drop_row = False
            per_row_audit: List[dict] = []

            for col_name, col_idx in col_indices.items():
                pref = (
                    config.ambiguous_format_preference
                    if config.ambiguous_format_preference != "AUTO"
                    else col_modes[col_name]
                )
                cleaned, audit_entry = self._clean_cell(
                    row[col_idx],
                    config,
                    pref,
                    row_idx,
                    header[col_idx],
                )

                if cleaned is None:
                    if audit_entry["error"] == "unparseable":
                        stats["errors_encountered"]["unparseable_dates"] += 1
                    elif audit_entry["error"] == "out_of_range":
                        stats["errors_encountered"]["out_of_range_dates"] += 1

                    if config.missing_strategy == "drop_row":
                        drop_row = True
                        break

                    row[col_idx] = ""
                else:
                    row[col_idx] = cleaned
                    self._tally(stats, audit_entry)

                if audit_entry["action"] != "none":
                    per_row_audit.append(audit_entry)

            if drop_row:
                continue

            if config.missing_strategy == "interpolate":
                window.append((row_idx, row))
                if len(window) == window.maxlen:
                    self._write_centre(
                        window,
                        writer,
                        col_indices.values(),
                        config,
                        stats,
                        audit_fh,
                    )
            else:
                if config.missing_strategy == "fill_default":
                    self._apply_fill_default(
                        row, col_indices.values(), config, stats)
                writer.writerow(row)

            for entry in per_row_audit:
                audit_fh.write(json.dumps(entry, separators=(",", ":")) + "\n")

            if stats["total_rows"] % 10_000 == 0:
                print(
                    f"[{time.strftime('%H:%M:%S')}] "
                    f"{stats['total_rows']:,} rows processed…",
                    file=sys.stderr,
                )

        if config.missing_strategy == "interpolate":
            while window:
                self._write_centre(
                    window,
                    writer,
                    col_indices.values(),
                    config,
                    stats,
                    audit_fh,
                )

        audit_fh.close()
        stats["processing_time_seconds"] = round(time.perf_counter() - t0, 3)
        return stats

    def validate_date_column(
        self,
        column_data: Iterable[str],
        preference: str = "US",
        config: Optional[CleaningConfig] = None,
    ) -> List[Tuple[str, bool]]:
        cfg = config or CleaningConfig(
            date_columns=[],
            missing_strategy="fill_default",
            ambiguous_format_preference=preference,
        )
        out: List[Tuple[str, bool]] = []
        for idx, raw in enumerate(column_data, start=1):
            cleaned, audit = self._clean_cell(raw, cfg, preference, idx, "col")
            if cleaned is None:
                cleaned = cfg.default_date
                corrected = True
            else:
                corrected = audit["action"] != "none"
            out.append((cleaned, corrected))
        return out

    _MONTHS: Dict[str, int] = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
        "mär": 3,
        "maerz": 3,
        "märz": 3,
        "mai": 5,
        "okt": 10,
        "dez": 12,
        "janv": 1,
        "févr": 2,
        "fevr": 2,
        "avr": 4,
        "juin": 6,
        "juil": 7,
        "août": 8,
        "aout": 8,
        "déc": 12,
        "decembre": 12,
    }

    _MISSING = {"", "NULL", "N/A", "NONE", "NAN"}

    _PATTERNS: List[Tuple[re.Pattern, str]] = [
        (
            re.compile(
                r"^(\d{4}-\d{2}-\d{2})[T\s]"
                r"(\d{2}:\d{2}:\d{2}(?:\.\d+)?)?"
                r"(Z|[+-]\d{2}:?\d{2})$",
                re.I,
            ),
            "ISO_TZ",
        ),
        (re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$"), "YMD_HYPH"),
        (re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$"), "YMD_SLSH"),
        (
            re.compile(r"^(\d{1,2})-([A-Za-zÀ-ÿ]{3,9})-(\d{2,4})$", re.I),
            "DMY_MON_DASH",
        ),
        (
            re.compile(
                r"^([A-Za-zÀ-ÿ]{3,9})\s+(\d{1,2}),?\s+(\d{2,4})$",
                re.I,
            ),
            "MON_DD_COMMA",
        ),
        (re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$"), "NUM_GEN"),
        (re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$"), "NUM_DOT"),
    ]

    @staticmethod
    def _detect_encoding(path: Path) -> str:
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                with path.open("r", encoding=enc) as fh:
                    fh.read(1024)
                return enc
            except UnicodeDecodeError:
                continue
        return "utf-8"

    @staticmethod
    def _fresh_stats(
        cfg: CleaningConfig,
        n_cols: int,
        duration: float,
    ) -> Dict[str, object]:
        return {
            "total_rows": 0,
            "date_columns_processed": cfg.date_columns,
            "corrections_made": {
                "format_standardized": 0,
                "month_day_swapped": 0,
                "invalid_dates_corrected": 0,
                "missing_values_filled": 0,
            },
            "errors_encountered": {
                "unparseable_dates": 0,
                "out_of_range_dates": 0,
            },
            "processing_time_seconds": round(duration, 3),
        }

    @staticmethod
    def _tally(stats: Dict[str, object], audit_entry: Dict[str, object]) -> None:
        action = audit_entry["action"]
        if action == "standardized":
            stats["corrections_made"]["format_standardized"] += 1
        elif action == "swapped":
            stats["corrections_made"]["month_day_swapped"] += 1
        elif action == "invalid_fixed":
            stats["corrections_made"]["invalid_dates_corrected"] += 1

    def _sample_modes(
        self,
        reader: Iterable[List[str]],
        col_indices: Dict[str, int],
        cfg: CleaningConfig,
        encoding: str,
    ) -> Dict[str, str]:
        counters: Dict[str, Counter[str]] = {c: Counter() for c in col_indices}

        for _ in range(cfg.sample_rows):
            try:
                row = next(reader)
            except StopIteration:
                break
            for col, idx in col_indices.items():
                cleaned, _ = self._clean_cell(
                    row[idx],
                    cfg,
                    "US",
                    0,
                    col,
                    audit=False,
                )
                if cleaned:
                    _, mm, dd = cleaned.split("-")
                    mode = (
                        "US"
                        if int(mm) <= 12 and int(dd) <= 31 and int(mm) != 0
                        else "International"
                    )
                    counters[col][mode] += 1

        out: Dict[str, str] = {}
        for col, counter in counters.items():
            out[col] = (
                "US"
                if counter.get("US", 0) >= counter.get("International", 0)
                else "International"
            )
        return out

    def _clean_cell(
        self,
        raw_value: str,
        cfg: CleaningConfig,
        preference: str,
        row_idx: int,
        col_name: str,
        audit: bool = True,
    ) -> Tuple[Optional[str], Dict[str, object]]:
        original = (raw_value or "").strip()

        if original.upper() in self._MISSING:
            if audit:
                return None, {
                    "row": row_idx,
                    "column": col_name,
                    "original": original,
                    "cleaned": (
                        cfg.default_date
                        if cfg.missing_strategy == "fill_default"
                        else None
                    ),
                    "action": "missing",
                    "error": None,
                }
            return None, {}

        for pat, tag in self._PATTERNS:
            match = pat.match(original)
            if not match:
                continue

            if tag == "ISO_TZ":
                iso_part, _, tz = match.groups()
                try:
                    base_dt = datetime.fromisoformat(iso_part)
                except ValueError:
                    break

                if tz == "Z":
                    base_dt = base_dt.replace(tzinfo=timezone.utc)
                else:
                    sign = 1 if tz[0] == "+" else -1
                    tz_hour = int(tz[1:3])
                    tz_min = int(tz[-2:])
                    base_dt = base_dt.replace(
                        tzinfo=timezone(
                            sign * timedelta(hours=tz_hour, minutes=tz_min),
                        ),
                    )

                cleaned = base_dt.astimezone(timezone.utc).date().strftime(
                    cfg.strftime,
                )
                return cleaned, self._audit(
                    row_idx,
                    col_name,
                    original,
                    cleaned,
                    "standardized",
                )

            if tag in {"YMD_HYPH", "YMD_SLSH"}:
                y, mo, da = map(int, match.groups())
                if not self._in_range(y):
                    return None, self._err(row_idx, col_name, original, "out_of_range")

                if self._valid(y, mo, da):
                    cleaned = f"{y:04d}-{mo:02d}-{da:02d}"
                    action = "standardized" if tag == "YMD_SLSH" else "none"
                    return cleaned, self._audit(row_idx, col_name, original, cleaned, action)

                max_d = calendar.monthrange(y, mo)[1]
                cleaned = f"{y:04d}-{mo:02d}-{max_d:02d}"
                return cleaned, self._audit(row_idx, col_name, original, cleaned, "invalid_fixed")

            if tag in {"DMY_MON_DASH", "MON_DD_COMMA"}:
                if tag == "DMY_MON_DASH":
                    da_s, mon_s, y_s = match.groups()
                else:
                    mon_s, da_s, y_s = match.groups()

                mo = self._MONTHS.get(mon_s.lower())
                if mo is None:
                    break

                da = int(da_s)
                y = self._century(int(y_s))
                if not self._in_range(y):
                    return None, self._err(row_idx, col_name, original, "out_of_range")

                if self._valid(y, mo, da):
                    cleaned = f"{y:04d}-{mo:02d}-{da:02d}"
                    return cleaned, self._audit(row_idx, col_name, original, cleaned, "standardized")

                max_d = calendar.monthrange(y, mo)[1]
                cleaned = f"{y:04d}-{mo:02d}-{max_d:02d}"
                return cleaned, self._audit(row_idx, col_name, original, cleaned, "invalid_fixed")

            if tag in {"NUM_GEN", "NUM_DOT"}:
                a, b, c = map(int, match.groups())
                y = self._century(c)
                if not self._in_range(y):
                    return None, self._err(row_idx, col_name, original, "out_of_range")

                if a > 31:
                    mo, da = b, c
                    y = self._century(a)
                    if self._valid(y, mo, da):
                        cleaned = f"{y:04d}-{mo:02d}-{da:02d}"
                        return cleaned, self._audit(row_idx, col_name, original, cleaned, "standardized")

                if a > 12 or b > 12:
                    mo, da = (a, b) if a <= 12 else (b, a)
                    swapped = False
                else:
                    if preference == "US":
                        mo, da = a, b
                        alt_mo, alt_da = b, a
                    else:
                        mo, da = b, a
                        alt_mo, alt_da = a, b

                    swapped = False
                    if not self._valid(y, mo, da) and self._valid(y, alt_mo, alt_da):
                        mo, da = alt_mo, alt_da
                        swapped = True

                if not self._valid(y, mo, da):
                    max_d = calendar.monthrange(y, mo)[1]
                    da = max_d
                    action = "invalid_fixed"
                elif swapped:
                    action = "swapped"
                else:
                    action = "standardized"

                cleaned = f"{y:04d}-{mo:02d}-{da:02d}"
                return cleaned, self._audit(row_idx, col_name, original, cleaned, action)

            break

        return None, self._err(row_idx, col_name, original, "unparseable")

    @staticmethod
    def _audit(
        row: int,
        col: str,
        original: str,
        cleaned: str,
        action: str,
    ) -> Dict[str, object]:
        return {
            "row": row,
            "column": col,
            "original": original,
            "cleaned": cleaned,
            "action": action,
            "error": None,
        }

    @staticmethod
    def _err(
        row: int,
        col: str,
        original: str,
        err_type: str,
    ) -> Dict[str, object]:
        return {
            "row": row,
            "column": col,
            "original": original,
            "cleaned": None,
            "action": "none",
            "error": err_type,
        }

    @staticmethod
    def _valid(y: int, mo: int, da: int) -> bool:
        try:
            date(y, mo, da)
            return True
        except ValueError:
            return False

    @staticmethod
    def _in_range(y: int) -> bool:
        return 1900 <= y <= 2100

    @staticmethod
    def _century(y: int) -> int:
        if y < 100:
            return 2000 + y if y <= 30 else 1900 + y
        return y

    @staticmethod
    def _apply_fill_default(
        row: List[str],
        idxs: Iterable[int],
        cfg: CleaningConfig,
        stats: Dict[str, object],
    ) -> None:
        for idx in idxs:
            if row[idx] == "":
                row[idx] = cfg.default_date
                stats["corrections_made"]["missing_values_filled"] += 1

    def _write_centre(
        self,
        window: Deque[Tuple[int, List[str]]],
        writer: csv.writer,
        idxs: Iterable[int],
        cfg: CleaningConfig,
        stats: Dict[str, object],
        audit_fh,
    ) -> None:
        centre_pos = len(window) // 2
        row_idx, row = window[centre_pos]

        for col_idx in idxs:
            if row[col_idx]:
                continue

            prev_dt = next_dt = None
            for off in range(1, len(window)):
                if centre_pos - off >= 0 and not prev_dt:
                    prev_val = window[centre_pos - off][1][col_idx]
                    if prev_val:
                        prev_dt = datetime.strptime(prev_val, "%Y-%m-%d")
                if centre_pos + off < len(window) and not next_dt:
                    next_val = window[centre_pos + off][1][col_idx]
                    if next_val:
                        next_dt = datetime.strptime(next_val, "%Y-%m-%d")
                if prev_dt and next_dt:
                    break

            if prev_dt and next_dt:
                span = (next_dt - prev_dt).days
                offset = off if centre_pos - off >= 0 else 0
                interp = prev_dt + \
                    timedelta(days=round(span * offset / (2 * off)))
                row[col_idx] = interp.strftime("%Y-%m-%d")
                action = "interpolated"
            else:
                row[col_idx] = cfg.default_date
                action = "default_filled"

            stats["corrections_made"]["missing_values_filled"] += 1
            audit_fh.write(
                json.dumps(
                    {
                        "row": row_idx,
                        "column_index": col_idx,
                        "original": None,
                        "cleaned": row[col_idx],
                        "action": action,
                        "error": None,
                    },
                    separators=(",", ":"),
                )
                + "\n",
            )

        writer.writerow(row)
        window.remove(window[centre_pos])

    @staticmethod
    def _normalise_row_len(row: List[str], target: int) -> List[str]:
        if len(row) < target:
            row.extend([""] * (target - len(row)))
            return row
        if len(row) > target:
            return row[:target]
        return row

