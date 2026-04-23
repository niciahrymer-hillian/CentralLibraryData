from __future__ import annotations

import ast
import csv
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "java_exports"

NULL_TOKENS = {"", "null", "none", "na", "n/a", "nan", "<na>"}


def normalize_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    if text.lower() in NULL_TOKENS:
        return ""
    return text


def clean_frame(df: pd.DataFrame, required_columns: list[str]) -> pd.DataFrame:
    cleaned = df.copy()

    for column in cleaned.columns:
        cleaned[column] = cleaned[column].map(normalize_text)

    for column in required_columns:
        cleaned = cleaned[cleaned[column] != ""]

    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    return cleaned


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


def build_books() -> pd.DataFrame:
    books = read_csv_as_strings(ROOT / "cleaned_data" / "pg_catalog.csv", skip_bad_lines=True)
    output = pd.DataFrame(
        {
            "ID": books["Text#"],
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
    output = clean_frame(output, ["ID", "Title"])
    output = output[output["ID"].str.fullmatch(r"\d+") == True]
    return dedupe_by_id(output, "ID")


def parse_volume_issue(description: object) -> tuple[str, str]:
    text = normalize_text(description)
    if not text:
        return "", ""

    volume_match = re.search(r"volume\s*([0-9A-Za-z.-]+)", text, flags=re.IGNORECASE)
    issue_match = re.search(r"(?:number|no\.?|issue)\s*([0-9A-Za-z.-]+)", text, flags=re.IGNORECASE)

    volume = volume_match.group(1) if volume_match else ""
    issue_number = issue_match.group(1) if issue_match else ""
    return normalize_text(volume), normalize_text(issue_number)


def build_periodicals() -> pd.DataFrame:
    titles = read_csv_as_strings(ROOT / "periodical-titles.csv", skip_bad_lines=True).rename(
        columns={"id": "title_id_ref", "title": "periodical_title"}
    )
    issues = read_periodical_issues(ROOT / "periodical-issues.csv").rename(
        columns={"id": "issue_id", "title": "issue_title", "description": "issue_description", "date": "issue_date"}
    )

    merged = issues.merge(
        titles[["title_id_ref", "periodical_title", "publisher", "place", "issn"]],
        left_on="title_id",
        right_on="title_id_ref",
        how="left",
    )

    volume_issue = merged["issue_description"].map(parse_volume_issue)
    output = pd.DataFrame(
        {
            "ID": merged["issue_id"],
            "Title": merged["periodical_title"].fillna(merged["issue_title"]),
            "Location": merged["place"],
            "Publisher": merged["publisher"],
            "ISSN": merged["issn"],
            "Volume": [item[0] for item in volume_issue],
            "Issue Number": [item[1] for item in volume_issue],
            "Publication Date": merged["issue_date"],
        }
    )
    return clean_frame(output, ["ID", "Title"])


def build_music() -> pd.DataFrame:
    music = read_csv_as_strings(ROOT / "cleaned_data" / "tcc_ceds_music.csv")
    id_column = music.columns[0]
    output = pd.DataFrame(
        {
            "ID": music[id_column],
            "Artist Name": music["artist_name"],
            "Track Name": music["track_name"],
            "Release Date": music["release_date"],
            "Genre": music["genre"],
            "Lyrics": music["lyrics"],
            "Length": music["len"],
            "Keywords": "",
        }
    )
    return clean_frame(output, ["ID", "Artist Name", "Track Name"])


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


def build_dvds() -> pd.DataFrame:
    links = read_csv_as_strings(ROOT / "links.csv")
    ratings = pd.read_csv(ROOT / "ratings.csv", usecols=["movieId", "rating"])
    avg_rating = (
        ratings.groupby("movieId", dropna=False)["rating"]
        .mean()
        .round(2)
        .astype(str)
        .to_dict()
    )
    directors = parse_director_by_tmdb_id(ROOT / "credits.csv")

    output = pd.DataFrame(
        {
            "ID": links["movieId"],
            "Title": "",
            "Location": "",
            "Director": links["tmdbId"].map(lambda value: directors.get(normalize_text(value), "")),
            "Duration": "",
            "Rating": links["movieId"].map(lambda value: avg_rating.get(pd.to_numeric(value, errors="coerce"), "")),
            "Genre": "",
        }
    )
    return clean_frame(output, ["ID"])


def write_output(filename: str, df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    target = OUTPUT_DIR / filename
    df.to_csv(target, index=False)
    print(f"wrote {len(df)} rows to {target}")


def main() -> int:
    write_output("Book.csv", build_books())
    write_output("DVD.csv", build_dvds())
    write_output("Periodical.csv", build_periodicals())
    write_output("Music.csv", build_music())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())