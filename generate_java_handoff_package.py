from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import shutil

import pandas as pd


ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "java_exports"
TARGET_DIR = ROOT / "Generated java handoff package"
ZIP_BASE = ROOT / "Generated java handoff package"


SOURCE_FILES = {
    "Book": SOURCE_DIR / "Book.csv",
    "DVD": SOURCE_DIR / "DVD.csv",
    "Periodical": SOURCE_DIR / "Periodical.csv",
    "Music": SOURCE_DIR / "Music.csv",
}


def is_missing(value: object) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() == "empty"


def normalize_id_token(value: object, fallback_index: int) -> str:
    if not is_missing(value):
        raw = str(value).strip()
        digits = "".join(ch for ch in raw if ch.isdigit())
        if digits:
            return digits
        return raw.replace(" ", "")
    return str(100000 + fallback_index)


def generated_value(class_name: str, column: str, row_index: int, id_token: str) -> str:
    lower_col = column.lower()

    if lower_col in {"id", "id#"}:
        return id_token

    if lower_col == "title":
        return f"Generated {class_name} Title {id_token}"

    if lower_col == "location":
        aisle = (row_index % 12) + 1
        shelf = (row_index % 40) + 1
        return f"Aisle {aisle}, Shelf {shelf}"

    if lower_col in {"author", "artist", "director", "publisher"}:
        return f"Generated {column} {id_token}"

    if lower_col == "isbn":
        seed = int(id_token[-6:]) if id_token[-6:].isdigit() else row_index + 1
        return f"978{seed:010d}"[:13]

    if lower_col == "pages":
        return str(120 + (row_index % 380))

    if lower_col == "genre":
        genres = ["Fiction", "Drama", "History", "Science", "Biography", "Classical", "Documentary"]
        return genres[row_index % len(genres)]

    if lower_col == "rating":
        return f"{2.5 + ((row_index % 6) * 0.5):.1f}"

    if lower_col == "issn":
        left = (1000 + (row_index % 9000))
        right = (1000 + ((row_index * 7) % 9000))
        return f"{left:04d}-{right:04d}"

    if lower_col == "volume":
        return str((row_index % 30) + 1)

    if lower_col in {"issue #", "issue number"}:
        return str((row_index % 12) + 1)

    if lower_col in {"publication date", "date"}:
        base = date(2020, 1, 1)
        return (base + timedelta(days=row_index % 2000)).isoformat()

    if lower_col == "lyrics":
        return f"Generated lyrics for track {id_token}."

    if lower_col == "length":
        return str(150 + (row_index % 220))

    return f"Generated {column} {id_token}"


def fill_missing_values(class_name: str, frame: pd.DataFrame) -> pd.DataFrame:
    filled = frame.copy()
    id_column = "Id" if "Id" in filled.columns else "ID" if "ID" in filled.columns else filled.columns[0]

    for idx in filled.index:
        id_token = normalize_id_token(filled.at[idx, id_column], int(idx) + 1)
        for column in filled.columns:
            if is_missing(filled.at[idx, column]):
                filled.at[idx, column] = generated_value(class_name, column, int(idx), id_token)

    return filled


def main() -> None:
    missing_sources = [path for path in SOURCE_FILES.values() if not path.exists()]
    if missing_sources:
        names = ", ".join(str(path) for path in missing_sources)
        raise FileNotFoundError(f"Missing source export files: {names}")

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    for class_name, source_path in SOURCE_FILES.items():
        frame = pd.read_csv(source_path, dtype="string")
        output = fill_missing_values(class_name, frame)
        output.to_csv(TARGET_DIR / source_path.name, index=False)

    if ZIP_BASE.with_suffix(".zip").exists():
        ZIP_BASE.with_suffix(".zip").unlink()

    shutil.make_archive(str(ZIP_BASE), "zip", root_dir=TARGET_DIR)
    print(f"Created folder: {TARGET_DIR}")
    print(f"Created zip: {ZIP_BASE.with_suffix('.zip')}")


if __name__ == "__main__":
    main()