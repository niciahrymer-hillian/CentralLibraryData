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
from typing import Iterable, TextIO

import pandas as pd


SUPPORTED_EXTENSIONS = {".csv", ".json", ".ndjson"}

# Directories to skip entirely during scanning
SKIP_DIRS = {".venv", "venv", ".git", "__pycache__", "node_modules", ".tox", "cleaned_data", "sample_data_java"}

# Optional size guard for very large files. Disabled by default.
DEFAULT_MAX_FILE_MB: int | None = None

NULL_TOKENS = {"", "null", "none", "na", "n/a", "nan"}
INT_COLUMN_HINTS = {"count", "pages", "year", "total", "quantity", "num", "number"}
FLOAT_COLUMN_HINTS = {"rating", "score", "amount", "price", "lat", "latitude", "lon", "longitude"}
BOOL_COLUMN_HINTS = {"is", "has", "active", "enabled", "flag"}
STRING_KEY_EXEMPT_FROM_TYPE_COERCION = {"id", "issn", "isbn", "zip", "postcode", "code"}
DATE_FIELD_HINTS = {"date", "day", "published", "created", "updated", "start", "end"}
NUMERIC_COLUMN_HINTS = INT_COLUMN_HINTS.union(FLOAT_COLUMN_HINTS).union({"pages", "timestamp", "index", "text"})
MAX_DUPLICATE_INDEX_PRINT = 200


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


def _emit(line: str, report_stream: TextIO | None = None) -> None:
    print(line)
    if report_stream is not None:
        report_stream.write(line + "\n")


def _should_write_sidecar_report(path: Path) -> bool:
    return not path.name.endswith("-schema.json")


def _report_path_for(path: Path, root: Path, report_dir: Path | None) -> Path:
    if report_dir is not None:
        report_path = report_dir.resolve() / path.relative_to(root)
        return report_path.with_suffix(report_path.suffix + ".report.txt")
    return path.with_suffix(path.suffix + ".report.txt")


def _print_non_csv_report(path: Path, target: Path, changed: bool, dupes: int, nulls: int, report_stream: TextIO | None = None) -> None:
    _emit(f"\n=== REPORT: {path} ===", report_stream)
    _emit(f"file type: {path.suffix.lower()}", report_stream)
    _emit(f"status: {'changed' if changed else 'unchanged'}", report_stream)
    _emit(f"output: {target}", report_stream)
    _emit(f"duplicates removed: {dupes}", report_stream)
    _emit(f"null rows removed: {nulls}", report_stream)


def _print_inventory(root: Path, report_stream: TextIO | None = None) -> None:
    files = sorted(iter_data_files(root))
    _emit("\nData inventory", report_stream)
    _emit("file,type,size_bytes", report_stream)
    for path in files:
        size = path.stat().st_size
        _emit(f"{path},{path.suffix.lower()},{size}", report_stream)


def _column_tokens(name: str) -> set[str]:
    return _field_name_tokens(name)


def _is_numeric_like_column(name: str) -> bool:
    tokens = _column_tokens(name)
    return bool(tokens.intersection(NUMERIC_COLUMN_HINTS))


def _is_date_like_column(name: str) -> bool:
    tokens = _column_tokens(name)
    return bool(tokens.intersection(DATE_FIELD_HINTS))


def _id_like_columns(df: pd.DataFrame) -> list[str]:
    preferred = {
        "id",
        "title_id",
        "userId",
        "movieId",
        "Text#",
        "index",
        "index number",
    }
    result: list[str] = []
    for col in df.columns:
        lowered = str(col).strip().lower()
        if col in preferred or lowered in preferred or lowered.endswith("_id"):
            result.append(str(col))
    return result


def _print_csv_profile(path: Path, df: pd.DataFrame, report_stream: TextIO | None = None) -> None:
    _emit(f"\n=== PROFILE: {path} ===", report_stream)
    _emit(f"rows: {df.shape[0]}", report_stream)
    _emit(f"columns: {df.shape[1]}", report_stream)
    _emit("column names and dtypes:", report_stream)
    _emit(df.dtypes.to_string(), report_stream)

    _emit("\nfirst 5 rows:", report_stream)
    _emit(df.head(5).to_string(index=False), report_stream)

    null_count = df.isna().sum()
    null_pct = (null_count / len(df) * 100) if len(df) else null_count.astype(float)
    null_report = pd.DataFrame({"null_count": null_count, "null_pct": null_pct}).sort_values(
        by=["null_count", "null_pct"], ascending=False
    )
    _emit("\nnull report (sorted):", report_stream)
    _emit(null_report.to_string(), report_stream)

    exact_dupes = int(df.duplicated().sum())
    _emit(f"\nexact duplicate rows: {exact_dupes}", report_stream)
    if exact_dupes:
        dup_index = df[df.duplicated()].index.tolist()
        preview = dup_index[:MAX_DUPLICATE_INDEX_PRINT]
        _emit(
            f"duplicate index numbers (showing up to {MAX_DUPLICATE_INDEX_PRINT}): {preview}",
            report_stream,
        )
        _emit(df[df.duplicated()].head(MAX_DUPLICATE_INDEX_PRINT).to_string(index=True), report_stream)

    for col in _id_like_columns(df):
        dup_mask = df[col].duplicated(keep=False) & df[col].notna()
        dup_count = int(dup_mask.sum())
        if dup_count:
            _emit(f"\nid duplicate rows for {col}: {dup_count}", report_stream)
            dup_indices = df[dup_mask].index.tolist()
            preview = dup_indices[:MAX_DUPLICATE_INDEX_PRINT]
            _emit(
                f"duplicate index numbers ({col}, showing up to {MAX_DUPLICATE_INDEX_PRINT}): {preview}",
                report_stream,
            )
            _emit(
                df.loc[dup_mask, [col]].sort_values(by=col).head(MAX_DUPLICATE_INDEX_PRINT).to_string(index=True),
                report_stream,
            )

    numeric_candidates = [c for c in df.columns if _is_numeric_like_column(str(c))]
    if numeric_candidates:
        _emit("\nnumeric column stats:", report_stream)
        for col in numeric_candidates:
            coerced = pd.to_numeric(df[col], errors="coerce")
            non_numeric_mask = df[col].notna() & coerced.isna()
            if non_numeric_mask.any():
                _emit(f"non-numeric values in {col}: {int(non_numeric_mask.sum())}", report_stream)
                _emit(df.loc[non_numeric_mask, [col]].head(20).to_string(index=True), report_stream)
            valid = coerced.dropna()
            if len(valid):
                _emit(f"{col}: min={valid.min()} max={valid.max()} mean={valid.mean()}", report_stream)

    date_candidates = [c for c in df.columns if _is_date_like_column(str(c))]
    if date_candidates:
        _emit("\ndate parsing checks:", report_stream)
        for col in date_candidates:
            parsed = pd.to_datetime(df[col], errors="coerce")
            failed = int((df[col].notna() & parsed.isna()).sum())
            _emit(f"unparseable dates in {col}: {failed}", report_stream)


def _normalize_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = [col for col in df.columns if pd.api.types.is_object_dtype(df[col])]
    for col in text_cols:
        df[col] = (
            df[col]
            .astype("string")
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )
        df[col] = df[col].replace("", pd.NA)
    return df


def _clean_csv_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned = _normalize_text_columns(cleaned)
    cleaned = cleaned.drop_duplicates()

    required_cols = _id_like_columns(cleaned)
    if required_cols:
        for col in required_cols:
            cleaned = cleaned[cleaned[col].notna()]

    for col in cleaned.columns:
        if _is_numeric_like_column(str(col)):
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    for col in cleaned.columns:
        if _is_date_like_column(str(col)):
            parsed = pd.to_datetime(cleaned[col], errors="coerce")
            cleaned[col] = parsed.dt.strftime("%Y-%m-%d")

    for col in required_cols:
        cleaned = cleaned[cleaned[col].notna()]

    cleaned = cleaned.drop_duplicates()

    return cleaned.reset_index(drop=True)


def _validation_unique_key_columns(df: pd.DataFrame, name: str) -> list[str]:
    dataset_name = Path(name).name
    overrides = {
        "credits.csv": ["id"],
        "keywords.csv": ["id"],
        "links.csv": ["movieId"],
        "links_small.csv": ["movieId"],
        "periodical-issues.csv": [],
        "periodical-titles.csv": [],
        "pg_catalog.csv": [],
        "ratings_small.csv": [],
        "tcc_ceds_music.csv": [],
    }
    if dataset_name in overrides:
        return [col for col in overrides[dataset_name] if col in df.columns]

    return [col for col in _id_like_columns(df) if str(col) == "id"]


def _validate_cleaned_csv(df: pd.DataFrame, name: str, report_stream: TextIO | None = None) -> None:
    if int(df.duplicated().sum()) != 0:
        raise AssertionError(f"{name}: exact duplicates remain after cleaning")

    for col in _validation_unique_key_columns(df, name):
        if int(df[col].duplicated().sum()) != 0:
            raise AssertionError(f"{name}: duplicate id values remain in {col}")

    if "rating" in df.columns:
        rating = pd.to_numeric(df["rating"], errors="coerce").dropna()
        if not rating.empty and ((rating < 0).any() or (rating > 5).any()):
            raise AssertionError(f"{name}: rating outside expected range [0, 5]")

    if "pages" in df.columns:
        pages = pd.to_numeric(df["pages"], errors="coerce").dropna()
        if not pages.empty and (pages < 0).any():
            raise AssertionError(f"{name}: pages contains negative values")

    _emit(f"validation passed: {name}", report_stream)


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
        with source.open("w", encoding="utf-8", newline="") as f:
            f.write(cleaned)
        return source

    assert output_dir is not None
    target = output_dir / source.relative_to(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as f:
        f.write(cleaned)
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
    parser.add_argument("--inventory", action="store_true", help="Print file name, type, and size inventory.")
    parser.add_argument("--profile-csv", action="store_true", help="Print CSV shape, dtypes, null, duplicate, and type checks.")
    parser.add_argument("--validate-csv", action="store_true", help="Run post-clean CSV validation checks.")
    parser.add_argument(
        "--max-file-mb",
        type=int,
        default=DEFAULT_MAX_FILE_MB,
        help="Skip files larger than this size in MB. Default: no size-based skipping.",
    )
    parser.add_argument(
        "--write-reports",
        action="store_true",
        help="Write inventory/profile/validation output to sidecar report files next to each source file.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=None,
        help="Directory for report files when using --write-reports (default: next to each source file).",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    output_dir = None if args.in_place else args.output_dir.resolve()

    inventory_stream: TextIO | None = None
    if args.inventory and args.write_reports:
        if args.report_dir is not None:
            inventory_path = args.report_dir.resolve() / "inventory_report.txt"
        else:
            inventory_path = root / "inventory_report.txt"
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        inventory_stream = inventory_path.open("w", encoding="utf-8")

    try:
        if args.inventory:
            _print_inventory(root, report_stream=inventory_stream)
    finally:
        if inventory_stream is not None:
            inventory_stream.close()

    changed = 0
    unchanged = 0
    failures = 0
    total_duplicates = 0
    total_nulls = 0
    max_file_bytes = None if args.max_file_mb is None else args.max_file_mb * 1024 * 1024

    for path in sorted(iter_data_files(root)):
        report_path: Path | None = None
        report_stream: TextIO | None = None
        if max_file_bytes is not None and path.stat().st_size > max_file_bytes:
            if args.write_reports and _should_write_sidecar_report(path):
                report_path = _report_path_for(path, root, args.report_dir)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_stream = report_path.open("w", encoding="utf-8")
                _emit(
                    f"SKIPPED (too large, >{args.max_file_mb}MB): {path}",
                    report_stream,
                )
                report_stream.close()
            else:
                print(f"SKIPPED (too large, >{args.max_file_mb}MB): {path}")
            continue
        try:
            if args.write_reports and _should_write_sidecar_report(path):
                report_path = _report_path_for(path, root, args.report_dir)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_stream = report_path.open("w", encoding="utf-8")

            if path.suffix.lower() == ".csv" and (args.profile_csv or args.validate_csv):
                df_before = pd.read_csv(path, low_memory=False, on_bad_lines='warn')
                if args.profile_csv:
                    _print_csv_profile(path, df_before, report_stream=report_stream)

            cleaned, dupes, nulls = clean_file(path, trim_fields=args.trim_fields)
            original = path.read_text(encoding="utf-8-sig")
            if cleaned == original and dupes == 0 and nulls == 0:
                unchanged += 1
                if report_stream is not None:
                    _emit(f"UNCHANGED: {path}", report_stream)
                continue
            changed += 1
            total_duplicates += dupes
            total_nulls += nulls
            if args.dry_run:
                _emit(f"WOULD CLEAN: {path} (dupes={dupes}, nulls={nulls})", report_stream)
                if path.suffix.lower() == ".csv" and args.validate_csv:
                    validated_df = _clean_csv_dataframe(df_before)
                    _validate_cleaned_csv(validated_df, path.name, report_stream=report_stream)
                continue
            target = write_output(cleaned, path, root, output_dir, args.in_place)
            _emit(f"CLEANED: {path} -> {target} (dupes={dupes}, nulls={nulls})", report_stream)
            if path.suffix.lower() == ".csv" and args.validate_csv:
                validated_df = _clean_csv_dataframe(pd.read_csv(target, low_memory=False, on_bad_lines='warn'))
                _validate_cleaned_csv(validated_df, target.name, report_stream=report_stream)
            elif report_stream is not None:
                _print_non_csv_report(path, target, changed=True, dupes=dupes, nulls=nulls, report_stream=report_stream)
        except Exception as exc:  # pragma: no cover - defensive path for malformed files
            failures += 1
            _emit(f"FAILED: {path} ({exc})", report_stream)
        finally:
            if report_stream is not None:
                report_stream.close()

    mode = "in-place" if args.in_place else f"output-dir={output_dir}"
    print("\nSummary")
    print(f"mode: {mode}")
    print(f"changed: {changed}")
    print(f"unchanged: {unchanged}")
    print(f"duplicates removed: {total_duplicates}")
    print(f"null rows removed: {total_nulls}")
    print(f"failed: {failures}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
