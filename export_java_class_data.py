from __future__ import annotations

import argparse
import ast
import csv
import logging
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "java_exports"

NULL_TOKENS = {"", "null", "none", "na", "n/a", "nan", "<na>"}

LOGGER = logging.getLogger("export_java")

DATE_PATTERNS = (
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


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    if text.lower() in NULL_TOKENS:
        return ""
    return text


def configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def standardize_date(value: object) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    try:
        normalized = text.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized).date().isoformat()
    except ValueError:
        return ""


def assert_numeric_column(df: pd.DataFrame, column: str, dataset_name: str) -> None:
    if column not in df.columns:
        raise ValueError(f"{dataset_name} missing expected numeric column: {column}")
    non_empty = df[column].map(normalize_text)
    non_empty = non_empty[non_empty != ""]
    if int(pd.to_numeric(non_empty, errors="coerce").isna().sum()) > 0:
        raise ValueError(f"{dataset_name} contains non-numeric values in {column}")


def verify_row_count(dataset_name: str, input_rows: int, output_rows: int) -> None:
    if output_rows <= 0:
        LOGGER.warning("%s output has no rows after filtering", dataset_name)
    elif output_rows > input_rows:
        raise ValueError(f"{dataset_name} output rows exceed input rows ({output_rows} > {input_rows})")
    else:
        LOGGER.info("%s row count check input=%s output=%s", dataset_name, input_rows, output_rows)


def clean_frame(df: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    cleaned = df.copy()

    for column in cleaned.columns:
        cleaned[column] = cleaned[column].map(normalize_text)

    for column in required_columns:
        cleaned = cleaned[cleaned[column] != ""]

    cleaned = cleaned.drop_duplicates().reset_index(drop=True)

    # Write a literal placeholder for optional blanks in exported CSVs.
    cleaned = cleaned.replace("", "empty")

    return cleaned


def require_columns(df: pd.DataFrame, required_columns: list[str], dataset_name: str) -> None:
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(f"{dataset_name} missing required columns: {missing}")


def enforce_unique_ids(df: pd.DataFrame, dataset_name: str, id_column: str = "ID") -> pd.DataFrame:
    if id_column not in df.columns:
        raise ValueError(f"{dataset_name} missing required id column: {id_column}")
    duplicate_count = int(df[id_column].duplicated().sum())
    if duplicate_count:
        raise ValueError(f"{dataset_name} has duplicate IDs in {id_column}: {duplicate_count}")
    return df


def assert_files_exist(paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required input files: {missing}")


def resolve_input_path(data_root: Path, cleaned_root: Path, filename: str, prefer_cleaned: bool = False) -> Path:
    candidates = (
        [cleaned_root / filename, data_root / filename]
        if prefer_cleaned
        else [data_root / filename, cleaned_root / filename]
    )
    return next((p for p in candidates if p.exists()), candidates[0])


def resolve_first_existing(candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def read_csv_as_strings(path: Path, skip_bad_lines: bool = False) -> pd.DataFrame:
    read_kwargs: dict[str, object] = {
        "dtype": "string",
        "keep_default_na": False,
    }
    if skip_bad_lines:
        read_kwargs.update({"engine": "python", "on_bad_lines": "skip"})
    return pd.read_csv(path, **read_kwargs)


def dedupe_by_id(df: pd.DataFrame, id_column: str) -> pd.DataFrame:
    ranked = df.copy()
    non_id_columns = [column for column in ranked.columns if column != id_column]
    ranked["_completeness"] = ranked[non_id_columns].apply(
        lambda row: sum(1 for value in row if normalize_text(value)),
        axis=1,
    )
    ranked = ranked.sort_values(by=[id_column, "_completeness"], ascending=[True, False], kind="mergesort")
    ranked = ranked.drop_duplicates(subset=[id_column], keep="first")
    return ranked.drop(columns=["_completeness"]).reset_index(drop=True)


def read_periodical_issues(path: Path) -> pd.DataFrame:
    rows: list[dict[str, str]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)

        for row in reader:
            if not row:
                continue
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            elif len(row) > len(header):
                row = row[:2] + [",".join(row[2:-5]), *row[-5:]]
            rows.append(dict(zip(header, row, strict=False)))

    return pd.DataFrame(rows, columns=header, dtype="string")


def extract_first_present(*values: object) -> str:
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return ""


def build_books(data_root: Path, cleaned_root: Path) -> pd.DataFrame:
    books_path = resolve_input_path(data_root, cleaned_root, "pg_catalog.csv", prefer_cleaned=True)
    books = read_csv_as_strings(books_path, skip_bad_lines=True)
    require_columns(books, ["Text#", "Title", "Authors"], "pg_catalog.csv")
    text_number = pd.to_numeric(books["Text#"], errors="coerce")
    invalid_id_count = int(text_number.isna().sum())
    if invalid_id_count:
        LOGGER.warning("pg_catalog.csv has %s rows with non-numeric Text#; they will be dropped", invalid_id_count)
    LOGGER.info("books input rows=%s source=%s", len(books), books_path)
    input_rows = len(books)
    output = pd.DataFrame(
        {
            "Id": books["Text#"],
            "Title": books["Title"],
            "Location": "",
            "Author": books["Authors"],
            "ISBN": "",
            "Pages": "",
            "Genre": books.apply(
                lambda row: extract_first_present(row.get("Bookshelves"), row.get("Subjects")),
                axis=1,
            ),
        }
    )
    output = clean_frame(output, ["Id", "Title"])
    output = output[output["Id"].str.fullmatch(r"\d+") == True]
    output = dedupe_by_id(output, "Id")
    output = enforce_unique_ids(output, "Book", "Id")
    verify_row_count("Book", input_rows, len(output))
    LOGGER.info("books output rows=%s", len(output))
    return output


def parse_volume_issue(description: object) -> tuple[str, str]:
    text = normalize_text(description)
    if not text:
        return "", ""

    volume_match = re.search(r"volume\s*([0-9A-Za-z.-]+)", text, flags=re.IGNORECASE)
    issue_match = re.search(r"(?:number|no\.?|issue)\s*([0-9A-Za-z.-]+)", text, flags=re.IGNORECASE)

    volume = volume_match.group(1) if volume_match else ""
    issue_number = issue_match.group(1) if issue_match else ""
    return normalize_text(volume), normalize_text(issue_number)


def build_periodicals(data_root: Path, cleaned_root: Path) -> pd.DataFrame:
    titles_path = resolve_input_path(data_root, cleaned_root, "periodical-titles.csv", prefer_cleaned=True)
    issues_path = resolve_input_path(data_root, cleaned_root, "periodical-issues.csv", prefer_cleaned=True)
    titles = read_csv_as_strings(titles_path, skip_bad_lines=True).rename(
        columns={"id": "title_id_ref", "title": "periodical_title"}
    )
    issues = read_periodical_issues(issues_path).rename(
        columns={"id": "issue_id", "title": "issue_title", "description": "issue_description", "date": "issue_date"}
    )
    require_columns(titles, ["title_id_ref", "periodical_title", "publisher", "place", "issn"], "periodical-titles.csv")
    require_columns(issues, ["issue_id", "issue_title", "issue_description", "issue_date", "title_id"], "periodical-issues.csv")
    LOGGER.info("periodicals input rows titles=%s issues=%s", len(titles), len(issues))
    input_rows = len(issues)

    orphan_mask = ~issues["title_id"].isin(titles["title_id_ref"])
    orphan_count = int(orphan_mask.sum())
    if orphan_count:
        LOGGER.warning("periodicals: %s issues have unmatched title_id (orphan FK)", orphan_count)

    merged = issues.merge(
        titles[["title_id_ref", "periodical_title", "publisher", "place", "issn"]],
        left_on="title_id",
        right_on="title_id_ref",
        how="left",
    )

    volume_issue = merged["issue_description"].map(parse_volume_issue)
    output = pd.DataFrame(
        {
            "Id": merged["issue_id"],
            "Title": merged["periodical_title"].fillna(merged["issue_title"]),
            "Location": merged["place"],
            "Publisher": merged["publisher"],
            "ISSN": merged["issn"],
            "Volume": [item[0] for item in volume_issue],
            "Issue #": [item[1] for item in volume_issue],
            "Publication date": merged["issue_date"].map(standardize_date),
        }
    )
    output = clean_frame(output, ["Id", "Title"])
    output = dedupe_by_id(output, "Id")
    output = enforce_unique_ids(output, "Periodical", "Id")
    verify_row_count("Periodical", input_rows, len(output))
    LOGGER.info("periodicals stage rows output=%s", len(output))
    return output


def build_music(data_root: Path, cleaned_root: Path) -> pd.DataFrame:
    music_path = resolve_input_path(data_root, cleaned_root, "tcc_ceds_music.csv", prefer_cleaned=True)
    music = read_csv_as_strings(music_path)
    require_columns(music, ["artist_name", "track_name", "release_date", "genre", "lyrics", "len"], "tcc_ceds_music.csv")
    assert_numeric_column(music, music.columns[0], "tcc_ceds_music.csv")
    LOGGER.info("music input rows=%s source=%s", len(music), music_path)
    input_rows = len(music)
    id_column = music.columns[0]
    output = pd.DataFrame(
        {
            "ID": music[id_column],
            "Title": music["track_name"],
            "Location": "",
            "Artist": music["artist_name"],
            "Date": music["release_date"].map(standardize_date),
            "Genre": music["genre"],
            "Lyrics": music["lyrics"],
            "Length": music["len"],
        }
    )
    output = clean_frame(output, ["ID", "Title", "Artist"])
    output = dedupe_by_id(output, "ID")
    output = enforce_unique_ids(output, "Music", "ID")
    verify_row_count("Music", input_rows, len(output))
    LOGGER.info("music stage rows output=%s", len(output))
    return output


def parse_director_by_tmdb_id(path: Path) -> dict[str, str]:
    directors: dict[str, str] = {}

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            tmdb_id = normalize_text(row.get("id"))
            crew_text = normalize_text(row.get("crew"))
            if not tmdb_id or not crew_text:
                continue

            try:
                crew_items = ast.literal_eval(crew_text)
            except (SyntaxError, ValueError):
                continue

            if not isinstance(crew_items, list):
                continue

            director_name = ""
            for item in crew_items:
                if not isinstance(item, dict):
                    continue
                job = normalize_text(item.get("job"))
                department = normalize_text(item.get("department"))
                if job.lower() == "director" or department.lower() == "directing":
                    director_name = normalize_text(item.get("name"))
                    if director_name:
                        break

            directors[tmdb_id] = director_name

    return directors


def build_dvds(data_root: Path, cleaned_root: Path) -> pd.DataFrame:
    links_path = resolve_input_path(data_root, cleaned_root, "links.csv", prefer_cleaned=True)
    ratings_path = resolve_first_existing(
        [
            resolve_input_path(data_root, cleaned_root, "ratings.csv", prefer_cleaned=True),
            resolve_input_path(data_root, cleaned_root, "ratings_small.csv", prefer_cleaned=True),
        ]
    )
    credits_path = resolve_input_path(data_root, cleaned_root, "credits.csv", prefer_cleaned=True)
    links = read_csv_as_strings(links_path)
    require_columns(links, ["movieId", "tmdbId"], "links.csv")
    assert_numeric_column(links, "movieId", "links.csv")
    ratings = pd.read_csv(ratings_path, usecols=["movieId", "rating"])
    if pd.to_numeric(ratings["rating"], errors="coerce").isna().any():
        raise ValueError("ratings.csv contains non-numeric values in rating")
    LOGGER.info("dvd input rows links=%s ratings=%s", len(links), len(ratings))
    input_rows = len(links)
    avg_rating = (
        ratings.groupby("movieId", dropna=False)["rating"]
        .mean()
        .round(2)
        .astype(str)
        .to_dict()
    )
    directors = parse_director_by_tmdb_id(credits_path)

    output = pd.DataFrame(
        {
            "Id": links["movieId"],
            "Title": "",
            "Location": "",
            "Director": links["tmdbId"].map(lambda value: directors.get(normalize_text(value), "")),
            "Rating": links["movieId"].map(lambda value: avg_rating.get(pd.to_numeric(value, errors="coerce"), "")),
            "Genre": "",
        }
    )
    output = clean_frame(output, ["Id"])
    output = dedupe_by_id(output, "Id")
    output = enforce_unique_ids(output, "DVD", "Id")
    verify_row_count("DVD", input_rows, len(output))
    LOGGER.info("dvd stage rows output=%s", len(output))
    return output


def write_output(filename: str, df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / filename
    if len(df) == 0:
        LOGGER.warning("skipping %s — no rows to write", filename)
        return
    df.to_csv(target, index=False)
    LOGGER.info("wrote rows=%s target=%s", len(df), target)


def get_required_input_paths(data_root: Path, cleaned_root: Path) -> list[Path]:
    ratings_path = resolve_first_existing(
        [
            resolve_input_path(data_root, cleaned_root, "ratings.csv", prefer_cleaned=True),
            resolve_input_path(data_root, cleaned_root, "ratings_small.csv", prefer_cleaned=True),
        ]
    )
    return [
        resolve_input_path(data_root, cleaned_root, "pg_catalog.csv", prefer_cleaned=True),
        resolve_input_path(data_root, cleaned_root, "periodical-titles.csv", prefer_cleaned=True),
        resolve_input_path(data_root, cleaned_root, "periodical-issues.csv", prefer_cleaned=True),
        resolve_input_path(data_root, cleaned_root, "tcc_ceds_music.csv", prefer_cleaned=True),
        resolve_input_path(data_root, cleaned_root, "links.csv", prefer_cleaned=True),
        ratings_path,
        resolve_input_path(data_root, cleaned_root, "credits.csv", prefer_cleaned=True),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export class-specific CSV files for Java integration.")
    parser.add_argument("--sample", action="store_true", help="Run using sample data in sample_data_java.")
    parser.add_argument(
        "--sample-group",
        choices=["valid_records", "invalid_records", "edge_case_records"],
        default="valid_records",
        help="Sample dataset group to use with --sample.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    if args.sample:
        data_root = ROOT / "sample_data_java" / args.sample_group
        cleaned_root = data_root
    else:
        data_root = ROOT
        cleaned_root = ROOT / "cleaned_data"

    try:
        required_paths = get_required_input_paths(data_root, cleaned_root)
        assert_files_exist(required_paths)

        write_output("Book.csv", build_books(data_root, cleaned_root))
        write_output("DVD.csv", build_dvds(data_root, cleaned_root))
        write_output("Periodical.csv", build_periodicals(data_root, cleaned_root))
        write_output("Music.csv", build_music(data_root, cleaned_root))
        return 0
    except Exception:
        LOGGER.exception("export pipeline failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())