#!/usr/bin/env python3
"""Clean CSV, JSON, and NDJSON files in a directory tree.

By default, cleaned files are written to ./cleaned_data to avoid modifying
original source files. Use --in-place to overwrite files.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

try:
    from validate_sample import validate as _validate_sample
except ImportError:  # validate_sample not on path; validation silently skipped
    _validate_sample = None  # type: ignore[assignment]


SUPPORTED_EXTENSIONS = {".csv", ".json", ".ndjson"}

# Directories to skip entirely during scanning
SKIP_DIRS = {".venv", "venv", ".git", "__pycache__", "node_modules", ".tox", "cleaned_data"}

NULL_TOKENS = {"", "null", "none", "na", "n/a", "nan"}
INT_COLUMN_HINTS = {"count", "pages", "year", "total", "quantity", "num", "number"}
FLOAT_COLUMN_HINTS = {"rating", "score", "amount", "price", "lat", "latitude", "lon", "longitude"}
BOOL_COLUMN_HINTS = {"is", "has", "active", "enabled", "flag"}
STRING_KEY_EXEMPT_FROM_TYPE_COERCION = {"id", "issn", "isbn", "zip", "postcode", "code"}
DATE_FIELD_HINTS = {"date", "day", "published", "created", "updated", "start", "end"}


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _is_null_like(value: str) -> bool:
    return value.strip().lower() in NULL_TOKENS


def _parse_iso_date(value: str) -> str | None:
    token = value.strip()
    if not token:
        return None

    # Fast path for values already in YYYY-MM-DD.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", token):
        return token

    # Try common date-only patterns first to avoid locale parsing ambiguity.
    date_patterns = (
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
    )
    for pattern in date_patterns:
        try:
            return datetime.strptime(token, pattern).date().isoformat()
        except ValueError:
            continue

    # Handle ISO datetimes and similar values with time components.
    try:
        normalized = token.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).date().isoformat()
    except ValueError:
        return None


def standardize_dates(value: str) -> str | None:
    """Normalize supported date formats to YYYY-MM-DD."""
    return _parse_iso_date(value)


def _field_name_tokens(field_name: str) -> set[str]:
    lowered = field_name.strip().lower()
    parts = set(filter(None, re.split(r"[^a-z0-9]+", lowered)))
    if lowered.startswith("is_"):
        parts.add("is")
    if lowered.startswith("has_"):
        parts.add("has")
    return parts


def _is_date_field_name(field_name: str) -> bool:
    tokens = _field_name_tokens(field_name)
    return bool(tokens.intersection(DATE_FIELD_HINTS))


def _should_skip_type_coercion(field_name: str) -> bool:
    tokens = _field_name_tokens(field_name)
    return bool(tokens.intersection(STRING_KEY_EXEMPT_FROM_TYPE_COERCION))


def _coerce_typed_value(value: str, field_name: str | None = None) -> object:
    normalized = _normalize_whitespace(value)
    lowered = normalized.lower()

    if lowered in {"true", "false"}:
        return lowered == "true"

    # Preserve IDs/codes and similarly structured string keys.
    if field_name and _should_skip_type_coercion(field_name):
        return normalized

    if re.fullmatch(r"[+-]?\d+", normalized):
        try:
            return int(normalized)
        except ValueError:
            pass

    if re.fullmatch(r"[+-]?\d*\.\d+", normalized):
        try:
            return float(normalized)
        except ValueError:
            pass

    return normalized


def _normalize_value(value: object, field_name: str | None = None) -> object:
    if isinstance(value, dict):
        return {k: _normalize_value(v, k) for k, v in value.items()}

    if isinstance(value, list):
        return [_normalize_value(item, field_name) for item in value]

    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()

    if isinstance(value, str):
        normalized = _normalize_whitespace(value)
        if _is_null_like(normalized):
            return None

        if field_name and _is_date_field_name(field_name):
            parsed = standardize_dates(normalized)
            if parsed is not None:
                return parsed

        return _coerce_typed_value(normalized, field_name)

    return value


def iter_data_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        # Skip files inside excluded directories
        if any(part in SKIP_DIRS or part.startswith(".") for part in path.parts[len(root.parts):-1]):
            continue
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path


def clean_csv_content(text: str, trim_fields: bool) -> tuple[str, int, int]:
    """Returns (cleaned_text, duplicates_removed, null_rows_removed)."""
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel

    rows = list(csv.reader(io.StringIO(text), dialect=dialect))

    header: list[str] | None = None
    cleaned_rows: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    duplicates_removed = 0
    null_rows_removed = 0

    for i, row in enumerate(rows):
        base_row = [cell.strip() for cell in row] if trim_fields else list(row)
        if not base_row:
            continue
        # Keep header row as-is
        if i == 0:
            header = [_normalize_whitespace(cell) for cell in base_row]
            cleaned_rows.append(header)
            continue

        normalized: list[str] = []
        for idx, cell in enumerate(base_row):
            col_name = header[idx] if header and idx < len(header) else ""
            value = _normalize_whitespace(cell)

            if _is_null_like(value):
                normalized.append("")
                continue

            if _is_date_field_name(col_name):
                iso_date = standardize_dates(value)
                if iso_date is not None:
                    normalized.append(iso_date)
                    continue

            if _should_skip_type_coercion(col_name):
                normalized.append(value)
                continue

            tokens = _field_name_tokens(col_name)
            if tokens.intersection(INT_COLUMN_HINTS) and re.fullmatch(r"[+-]?\d+", value):
                normalized.append(str(int(value)))
                continue
            if tokens.intersection(FLOAT_COLUMN_HINTS) and re.fullmatch(r"[+-]?\d*\.\d+", value):
                normalized.append(str(float(value)))
                continue
            if tokens.intersection(BOOL_COLUMN_HINTS) and value.lower() in {"true", "false"}:
                normalized.append(value.lower())
                continue

            normalized.append(value)

        # Drop rows where every field is empty/null
        if all(_is_null_like(cell) for cell in normalized):
            null_rows_removed += 1
            continue
        # Drop rows that are entirely blank
        if all(cell.strip() == "" for cell in normalized):
            null_rows_removed += 1
            continue
        # Drop duplicate rows (compare data rows only, not header)
        key = tuple(normalized)
        if key in seen:
            duplicates_removed += 1
            continue
        seen.add(key)
        cleaned_rows.append(normalized)

    out = io.StringIO()
    writer = csv.writer(
        out,
        delimiter=getattr(dialect, "delimiter", ","),
        quotechar=getattr(dialect, "quotechar", '"'),
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    writer.writerows(cleaned_rows)
    return out.getvalue(), duplicates_removed, null_rows_removed


def _drop_nulls(obj: object) -> object:
    """Recursively remove null values from dicts and lists."""
    if isinstance(obj, dict):
        out: dict[str, object] = {}
        for key, value in obj.items():
            if value is None:
                continue
            cleaned = _drop_nulls(value)
            if cleaned is None:
                continue
            out[key] = cleaned
        return out
    if isinstance(obj, list):
        out_list: list[object] = []
        for item in obj:
            if item is None:
                continue
            cleaned_item = _drop_nulls(item)
            if cleaned_item is None:
                continue
            out_list.append(cleaned_item)
        return out_list
    return obj


def clean_json_content(text: str) -> str:
    payload = json.loads(text)
    normalized = _normalize_value(payload)
    cleaned = _drop_nulls(normalized)
    return json.dumps(cleaned, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def clean_ndjson_content(text: str) -> tuple[str, int, int]:
    """Returns (cleaned_text, duplicates_removed, null_rows_removed)."""
    lines: list[str] = []
    seen: set[str] = set()
    duplicates_removed = 0
    null_rows_removed = 0

    for line in text.splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        # Drop null-only objects
        if obj is None or obj == {}:
            null_rows_removed += 1
            continue
        cleaned_obj = _drop_nulls(_normalize_value(obj))
        serialized = json.dumps(cleaned_obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        if serialized in seen:
            duplicates_removed += 1
            continue
        seen.add(serialized)
        lines.append(serialized)
    return "\n".join(lines) + ("\n" if lines else ""), duplicates_removed, null_rows_removed


def clean_file(path: Path, trim_fields: bool) -> tuple[str, int, int]:
    """Returns (cleaned_text, duplicates_removed, null_rows_removed)."""
    original = path.read_text(encoding="utf-8-sig")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return clean_csv_content(original, trim_fields=trim_fields)
    if suffix == ".json":
        # JSON is a single object; no row-level dedup/null concept
        return clean_json_content(original), 0, 0
    if suffix == ".ndjson":
        return clean_ndjson_content(original)
    raise ValueError(f"Unsupported file type: {path}")


def write_output(cleaned: str, source: Path, root: Path, output_dir: Path | None, in_place: bool) -> Path:
    if in_place:
        source.write_text(cleaned, encoding="utf-8", newline="")
        return source

    assert output_dir is not None
    target = output_dir / source.relative_to(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(cleaned, encoding="utf-8", newline="")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean CSV/JSON/NDJSON files by normalizing formatting and removing blank rows/lines."
    )
    parser.add_argument("--root", type=Path, default=Path("."), help="Root directory to scan (default: current dir).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("cleaned_data"),
        help="Destination root for cleaned files when not using --in-place (default: cleaned_data).",
    )
    parser.add_argument("--in-place", action="store_true", help="Overwrite original files.")
    parser.add_argument("--trim-fields", action="store_true", help="Trim leading/trailing spaces from CSV fields.")
    parser.add_argument("--dry-run", action="store_true", help="Report files that would change without writing output.")
    parser.add_argument(
        "--validate-sample",
        nargs=2,
        metavar=("TITLES_CSV", "ISSUES_CSV"),
        help="After cleaning, validate a golden sample pair against business rules.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    output_dir = None if args.in_place else args.output_dir.resolve()

    changed = 0
    unchanged = 0
    failures = 0
    total_duplicates = 0
    total_nulls = 0

    for path in sorted(iter_data_files(root)):
        try:
            cleaned, dupes, nulls = clean_file(path, trim_fields=args.trim_fields)
            original = path.read_text(encoding="utf-8-sig")
            if cleaned == original and dupes == 0 and nulls == 0:
                unchanged += 1
                continue
            changed += 1
            total_duplicates += dupes
            total_nulls += nulls
            if args.dry_run:
                print(f"WOULD CLEAN: {path} (dupes={dupes}, nulls={nulls})")
                continue
            target = write_output(cleaned, path, root, output_dir, args.in_place)
            print(f"CLEANED: {path} -> {target} (dupes={dupes}, nulls={nulls})")
        except Exception as exc:  # pragma: no cover - defensive path for malformed files
            failures += 1
            print(f"FAILED: {path} ({exc})")

    mode = "in-place" if args.in_place else f"output-dir={output_dir}"
    print("\nSummary")
    print(f"mode: {mode}")
    print(f"changed: {changed}")
    print(f"unchanged: {unchanged}")
    print(f"duplicates removed: {total_duplicates}")
    print(f"null rows removed: {total_nulls}")
    print(f"failed: {failures}")

    sample_failures = 0
    if args.validate_sample:
        titles_path, issues_path = (Path(p) for p in args.validate_sample)
        if _validate_sample is None:
            print("WARNING: validate_sample module not found; skipping business-rule validation.")
        else:
            violations = _validate_sample(titles_path, issues_path)
            if violations:
                sample_failures = len(violations)
                print(f"\nSample validation FAILED — {sample_failures} violation(s):")
                for v in violations:
                    print(f"  {v}")
            else:
                print("\nSample validation OK — all business rules satisfied.")

    return 1 if (failures or sample_failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())