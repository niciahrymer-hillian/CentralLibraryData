from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random
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


FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Elijah", "Sophia", "Lucas", "Isabella", "Mason",
    "Mia", "Ethan", "Charlotte", "James", "Amelia", "Benjamin", "Harper", "Logan", "Evelyn", "Alexander",
    "Abigail", "Henry", "Ella", "Michael", "Scarlett", "Daniel", "Grace", "Jackson", "Chloe", "Sebastian",
]

LAST_NAMES = [
    "Anderson", "Bennett", "Carter", "Donovan", "Ellis", "Fletcher", "Garcia", "Hughes", "Iverson", "Jensen",
    "Kensington", "Lawson", "Montgomery", "Nolan", "Owens", "Prescott", "Quincy", "Ramirez", "Sinclair", "Turner",
    "Underwood", "Vasquez", "Whitaker", "Xu", "Young", "Zimmerman", "Hawthorne", "Blackwell", "Dawson", "Marlowe",
]

MOVIE_ADJECTIVES = [
    "Silent", "Hidden", "Golden", "Broken", "Midnight", "Crimson", "Fading", "Last", "Rising", "Forgotten",
    "Electric", "Velvet", "Iron", "Wandering", "Burning", "Shattered", "Secret", "Lonely", "Radiant", "Final",
]

MOVIE_NOUNS = [
    "Harbor", "Empire", "Echo", "Promise", "Horizon", "Garden", "Signal", "River", "City", "Letter",
    "Voyage", "Kingdom", "Trial", "Shadow", "Paradox", "Summit", "Mirage", "Chronicle", "Frontier", "Lantern",
]

PERIODICAL_DESCRIPTORS = [
    "Business", "Policy", "Science", "Health", "Technology", "Arts", "Culture", "Global", "Economic", "Legal",
    "Education", "Literary", "Environmental", "Medical", "Industry", "Public Affairs", "Research", "Finance", "Innovation", "Civic",
]

PERIODICAL_FORMATS = ["Review", "Journal", "Quarterly", "Digest", "Chronicle", "Bulletin", "Observer", "Forum", "Report", "Times"]

BOOK_PATTERNS = [
    "The {adj} {noun}",
    "{noun} of the {adj} Era",
    "A {adj} {noun}",
]

DVD_PATTERNS = [
    "The {adj} {noun}",
    "{adj} {noun}",
    "{noun} at Midnight",
]

MUSIC_PATTERNS = [
    "{adj} {noun}",
    "{noun} in the {adj} Light",
    "{adj} Hearts, {noun} Nights",
]

BOOK_NOUNS = [
    "Atlas", "Chronicles", "Memoir", "Ledger", "Notebook", "Companion", "Guide", "Archive", "Record", "Anthology",
]

PUBLISHER_PREFIXES = [
    "Northbridge", "Redwood", "Harbor", "Summit", "Stonefield", "Bluebird", "Maple", "Riverside", "Crescent", "Elmwood",
    "Granite", "Pinecrest", "Westgate", "Hillside", "Broadview", "Lakeshore", "Brighton", "Ironwood", "Fairmont", "Crown",
]

PUBLISHER_SUFFIXES = ["Press", "Publishing", "Media Group", "House", "Journals", "Publications", "Review", "Books", "Editions", "Works"]

LOCATIONS = [
    "Main Library - Floor 1", "Main Library - Floor 2", "Downtown Branch", "Riverside Branch", "North Campus Library",
    "South Campus Library", "Reference Wing", "Archives Room", "Media Center", "Periodicals Desk", "Stacks A", "Stacks B",
]

MUSIC_GENRES = ["Pop", "Rock", "Jazz", "Hip-Hop", "Folk", "Classical", "R&B", "Soul", "Electronic", "Blues"]
BOOK_GENRES = ["History", "Biography", "Politics", "Science", "Literature", "Philosophy", "Travel", "Poetry", "Law", "Art"]
DVD_GENRES = ["Drama", "Comedy", "Thriller", "Action", "Documentary", "Adventure", "Sci-Fi", "Mystery", "Romance", "Animation"]

LYRICS_LINES = [
    "Streetlights glow while the city hums below",
    "Every promise finds a place to rest",
    "A borrowed summer in a paper sky",
    "Hold the moment like a photograph",
    "Morning breaks and everything feels new",
    "We were echoes learning how to sing",
    "The night was wide and full of quiet fire",
    "Turn the page and let the chorus rise",
]


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


def stable_rng(class_name: str, column: str, row_index: int, id_token: str) -> random.Random:
    seed = f"{class_name}|{column}|{row_index}|{id_token}"
    return random.Random(seed)


def pick_full_name(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def movie_title(rng: random.Random) -> str:
    if rng.random() < 0.35:
        return f"The {rng.choice(MOVIE_ADJECTIVES)} {rng.choice(MOVIE_NOUNS)}"
    return f"{rng.choice(MOVIE_ADJECTIVES)} {rng.choice(MOVIE_NOUNS)}"


def book_title(rng: random.Random) -> str:
    return f"{rng.choice(MOVIE_ADJECTIVES)} {rng.choice(BOOK_NOUNS)}"


def publisher_name(rng: random.Random) -> str:
    return f"{rng.choice(PUBLISHER_PREFIXES)} {rng.choice(PUBLISHER_SUFFIXES)}"


def periodical_title(row_index: int, id_token: str) -> str:
    rng = stable_rng("Periodical", "title", row_index, id_token)
    descriptor = rng.choice(PERIODICAL_DESCRIPTORS)
    fmt = rng.choice(PERIODICAL_FORMATS)
    return f"{descriptor} {fmt} {id_token}"


def class_title(class_name: str, row_index: int, id_token: str) -> str:
    rng = stable_rng(class_name, "title", row_index, id_token)
    adj = rng.choice(MOVIE_ADJECTIVES)

    if class_name == "Book":
        noun = rng.choice(BOOK_NOUNS)
        base = rng.choice(BOOK_PATTERNS).format(adj=adj, noun=noun)
        return f"{base} {id_token}"

    if class_name == "DVD":
        noun = rng.choice(MOVIE_NOUNS)
        base = rng.choice(DVD_PATTERNS).format(adj=adj, noun=noun)
        return f"{base} {id_token}"

    if class_name == "Music":
        noun = rng.choice(MOVIE_NOUNS)
        base = rng.choice(MUSIC_PATTERNS).format(adj=adj, noun=noun)
        return f"{base} {id_token}"

    return periodical_title(row_index, id_token)


def normalize_existing_title(value: object) -> str:
    text = str(value).strip()
    if text and text.lower().startswith("generated "):
        return ""
    return text


def generated_value(class_name: str, column: str, row_index: int, id_token: str) -> str:
    lower_col = column.lower()
    rng = stable_rng(class_name, column, row_index, id_token)

    if lower_col in {"id", "id#"}:
        return id_token

    if lower_col == "title":
        if class_name == "DVD":
            return movie_title(rng)
        if class_name == "Book":
            return book_title(rng)
        if class_name == "Music":
            return f"{rng.choice(MOVIE_ADJECTIVES)} {rng.choice(MOVIE_NOUNS)}"
        return f"{rng.choice(MOVIE_ADJECTIVES)} {rng.choice(MOVIE_NOUNS)} Review"

    if lower_col == "location":
        return rng.choice(LOCATIONS)

    if lower_col in {"author", "artist", "director"}:
        return pick_full_name(rng)

    if lower_col == "publisher":
        return publisher_name(rng)

    if lower_col == "isbn":
        seed = int(id_token[-6:]) if id_token[-6:].isdigit() else row_index + 1
        return f"978{seed:010d}"[:13]

    if lower_col == "pages":
        return str(rng.randint(120, 920))

    if lower_col == "genre":
        if class_name == "Book":
            return rng.choice(BOOK_GENRES)
        if class_name == "DVD":
            return rng.choice(DVD_GENRES)
        return rng.choice(MUSIC_GENRES)

    if lower_col == "rating":
        return f"{rng.uniform(2.8, 4.9):.1f}"

    if lower_col == "issn":
        left = (1000 + (row_index % 9000))
        right = (1000 + ((row_index * 7) % 9000))
        return f"{left:04d}-{right:04d}"

    if lower_col == "volume":
        return str(rng.randint(1, 48))

    if lower_col in {"issue #", "issue number"}:
        return str(rng.randint(1, 24))

    if lower_col in {"publication date", "date"}:
        base = date(2020, 1, 1)
        return (base + timedelta(days=row_index % 2000)).isoformat()

    if lower_col == "lyrics":
        line_count = rng.randint(2, 4)
        return "; ".join(rng.choice(LYRICS_LINES) for _ in range(line_count))

    if lower_col == "length":
        return str(rng.randint(120, 420))

    return f"{column} {id_token}"


def fill_missing_values(class_name: str, frame: pd.DataFrame) -> pd.DataFrame:
    filled = frame.copy()
    id_column = "Id" if "Id" in filled.columns else "ID" if "ID" in filled.columns else filled.columns[0]

    for idx in filled.index:
        id_token = normalize_id_token(filled.at[idx, id_column], int(idx) + 1)
        for column in filled.columns:
            if column.lower() == "title":
                filled.at[idx, column] = class_title(class_name, int(idx), id_token)
                continue

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