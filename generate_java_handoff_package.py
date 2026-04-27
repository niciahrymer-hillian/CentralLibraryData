from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import random
import re
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

SAFE_SONG_TITLES = [
    "Northern Lights", "Quiet Avenue", "Summer Lantern", "Paper Planes", "Horizon Bloom", "Silver Harbor",
    "Velvet Morning", "Clear Skies", "Open Window", "Golden Mile", "Moonlit Station", "Riverline",
]

SAFE_MUSIC_ARTISTS = [
    "Avery Lane", "Mila Hart", "Noah Finch", "Iris Monroe", "Leo Bennett", "Aria Stone",
    "Eden Park", "Rowan Hale", "Mason Vale", "Sofia Clark", "Elliot Brooks", "Nina West",
]

PROFANITY_PATTERNS = [
    re.compile(r"\bf+u+c*k+\b", flags=re.IGNORECASE),
    re.compile(r"\bs+h+i+t+\b", flags=re.IGNORECASE),
    re.compile(r"\bb+i+t+c+h+\b", flags=re.IGNORECASE),
    re.compile(r"\ba+s+s+h+o+l+e+\b", flags=re.IGNORECASE),
    re.compile(r"\bb+a+s+t+a+r+d+\b", flags=re.IGNORECASE),
]

HATE_PATTERNS = [
    re.compile(r"\bwhite\s+power\b", flags=re.IGNORECASE),
    re.compile(r"\bkill\s+all\b", flags=re.IGNORECASE),
    re.compile(r"\bexterminate\b", flags=re.IGNORECASE),
    re.compile(r"\bhate\s+all\b", flags=re.IGNORECASE),
]

HARMFUL_MUSIC_PATTERNS = [*PROFANITY_PATTERNS, *HATE_PATTERNS]

PERIODICAL_TITLE_REPLACEMENTS = [
    (re.compile(r"\blesbians?\s+on\s+the\s+loose\b", flags=re.IGNORECASE), "Community Life Review"),
]

TITLE_QUALIFIER_FIRST = [
    "North", "South", "East", "West", "Harbor", "River", "Civic", "Metro", "Central", "Summit",
    "Coastal", "Valley", "Forest", "Lake", "Prairie", "Granite", "Crown", "Elm", "Pine", "Maple",
]

TITLE_QUALIFIER_SECOND = [
    "Metro", "Weekly", "Regional", "National", "Global", "Urban", "Coastal", "Valley", "Central", "Evening",
    "Morning", "Civic", "Public", "Herald", "Outlook", "Digest", "Review", "Monthly", "Quarterly", "International",
]

PERIODICAL_VARIANT_PATTERNS = [
    "{title}: {first} {second}",
    "{title} ({first} {second} Edition)",
    "{title} - {first} {second} Review",
    "{title}: {first} {second} Bulletin",
    "{title} | {first} {second} Desk",
    "{title}: {first} {second} Journal",
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


def resolve_id_column(frame: pd.DataFrame) -> str:
    if "Id" in frame.columns:
        return "Id"
    if "ID" in frame.columns:
        return "ID"
    return frame.columns[0]


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
    return f"{descriptor} {fmt}"


def class_title(class_name: str, row_index: int, id_token: str) -> str:
    rng = stable_rng(class_name, "title", row_index, id_token)
    adj = rng.choice(MOVIE_ADJECTIVES)

    if class_name == "Book":
        noun = rng.choice(BOOK_NOUNS)
        base = rng.choice(BOOK_PATTERNS).format(adj=adj, noun=noun)
        return base

    if class_name == "DVD":
        noun = rng.choice(MOVIE_NOUNS)
        base = rng.choice(DVD_PATTERNS).format(adj=adj, noun=noun)
        return base

    if class_name == "Music":
        noun = rng.choice(MOVIE_NOUNS)
        base = rng.choice(MUSIC_PATTERNS).format(adj=adj, noun=noun)
        return base

    return periodical_title(row_index, id_token)


def normalize_existing_title(value: object) -> str:
    text = str(value).strip()
    if text and text.lower().startswith("generated "):
        return ""
    return text


def strip_author_years(value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""

    # Remove year metadata like ", 1743-1826", "(1901-1987)", "b. 1940", "d. 2005", "5 BCE-65".
    text = re.sub(r"\(\s*(?:b\.?|d\.?)?\s*\d{1,4}\??\s*(?:bce|bc|ce|ad)?\s*(?:[-/]|to)?\s*\d{0,4}\??\s*(?:bce|bc|ce|ad)?\s*\)", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:b\.?|d\.?|born|died)\s*\d{1,4}\??\s*(?:bce|bc|ce|ad)?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{1,4}\??\s*(?:bce|bc|ce|ad)?\s*[-/]\s*\d{1,4}\??\s*(?:bce|bc|ce|ad)?\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{3,4}\??\s*(?:bce|bc|ce|ad)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r",\s*\d{3,4}\s*[-/]\s*\d{2,4}\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\s*;\s*", "; ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"(?:;\s*){2,}", "; ", text)
    text = re.sub(r"\s+,", ",", text)
    return text.strip(" ,;")


def qualifier_from_rank(rank: int) -> str:
    first_len = len(TITLE_QUALIFIER_FIRST)
    second_len = len(TITLE_QUALIFIER_SECOND)
    space = first_len * second_len

    first = TITLE_QUALIFIER_FIRST[(rank // second_len) % first_len]
    second = TITLE_QUALIFIER_SECOND[rank % second_len]
    cycle = rank // space
    if cycle == 0:
        return f"{first} {second}"
    return f"{first} {second} {TITLE_QUALIFIER_FIRST[cycle % first_len]}"


def variant_periodical_title(base_title: str, rank: int, row_index: int) -> str:
    qualifier = qualifier_from_rank(rank)
    first, _, second_part = qualifier.partition(" ")
    second = second_part or "Review"

    chooser = stable_rng("Periodical", "variant", row_index, f"{base_title}|{rank}")
    pattern = chooser.choice(PERIODICAL_VARIANT_PATTERNS)
    return pattern.format(title=base_title, first=first, second=second)


def enforce_periodical_title_uniqueness(frame: pd.DataFrame) -> pd.DataFrame:
    if "Title" not in frame.columns:
        return frame

    result = frame.copy()
    result["Title"] = result["Title"].fillna("").map(lambda value: str(value).strip())

    used_titles = set(result["Title"].tolist())
    grouped = result.groupby("Title", dropna=False).indices

    for base_title, raw_indexes in grouped.items():
        title_text = str(base_title).strip()
        if title_text == "":
            continue
        if len(raw_indexes) <= 1:
            continue

        indexes = sorted(int(idx) for idx in raw_indexes)
        for rank, row_index in enumerate(indexes):
            qualifier_rank = rank
            while True:
                candidate = variant_periodical_title(title_text, qualifier_rank, row_index)
                current_title = str(result.at[row_index, "Title"]).strip()
                if candidate == current_title:
                    break
                if candidate not in used_titles:
                    used_titles.discard(current_title)
                    result.at[row_index, "Title"] = candidate
                    used_titles.add(candidate)
                    break
                qualifier_rank += 1

    return result


def sanitize_periodical_titles(frame: pd.DataFrame) -> pd.DataFrame:
    if "Title" not in frame.columns:
        return frame

    result = frame.copy()
    id_column = resolve_id_column(result)

    for idx in result.index:
        current_title = str(result.at[idx, "Title"]).strip()
        if not current_title:
            continue

        replacement = None
        for pattern, replacement_base in PERIODICAL_TITLE_REPLACEMENTS:
            if pattern.search(current_title):
                replacement = replacement_base
                break

        if replacement is not None:
            id_token = normalize_id_token(result.at[idx, id_column], int(idx) + 1)
            chooser = stable_rng("Periodical", "replacement-title", int(idx), id_token)
            variant = chooser.choice(["Digest", "Review", "Journal", "Chronicle"])
            result.at[idx, "Title"] = f"{replacement} {variant}"

    return result


def contains_harmful_music_text(text: str) -> bool:
    lowered = text.lower()
    for pattern in HARMFUL_MUSIC_PATTERNS:
        if pattern.search(lowered):
            return True
    return False


def replacement_music_row(row_index: int, id_token: str) -> dict[str, str]:
    rng = stable_rng("Music", "replacement", row_index, id_token)
    base = date(2018, 1, 1)
    lyric_lines = [rng.choice(LYRICS_LINES) for _ in range(rng.randint(2, 4))]
    return {
        "Title": rng.choice(SAFE_SONG_TITLES),
        "Location": rng.choice(LOCATIONS),
        "Artist": rng.choice(SAFE_MUSIC_ARTISTS),
        "Date": (base + timedelta(days=rng.randint(0, 2800))).isoformat(),
        "Genre": rng.choice(MUSIC_GENRES),
        "Lyrics": "; ".join(lyric_lines),
        "Length": str(rng.randint(140, 360)),
    }


def sanitize_music_content(frame: pd.DataFrame) -> pd.DataFrame:
    id_column = resolve_id_column(frame)

    result = frame.copy()
    scanned_columns = [col for col in ["Title", "Artist", "Genre", "Lyrics"] if col in result.columns]

    for idx in result.index:
        text_blob = " ".join(str(result.at[idx, col]) for col in scanned_columns)
        if not contains_harmful_music_text(text_blob):
            continue

        id_token = normalize_id_token(result.at[idx, id_column], int(idx) + 1)
        replacement = replacement_music_row(int(idx), id_token)
        for col, value in replacement.items():
            if col in result.columns:
                result.at[idx, col] = value

    return result


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
    id_column = resolve_id_column(filled)

    for idx in filled.index:
        id_token = normalize_id_token(filled.at[idx, id_column], int(idx) + 1)
        for column in filled.columns:
            lower_col = column.lower()

            if lower_col == "title":
                current_title = normalize_existing_title(filled.at[idx, column])
                if not is_missing(current_title):
                    filled.at[idx, column] = current_title
                else:
                    filled.at[idx, column] = class_title(class_name, int(idx), id_token)
                continue

            if class_name == "Book" and lower_col == "author":
                cleaned_author = strip_author_years(filled.at[idx, column])
                if not is_missing(cleaned_author):
                    filled.at[idx, column] = cleaned_author
                else:
                    filled.at[idx, column] = generated_value(class_name, column, int(idx), id_token)
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
        if class_name == "Periodical":
            output = sanitize_periodical_titles(output)
            output = enforce_periodical_title_uniqueness(output)
        if class_name == "Music":
            output = sanitize_music_content(output)
        output.to_csv(TARGET_DIR / source_path.name, index=False)

    if ZIP_BASE.with_suffix(".zip").exists():
        ZIP_BASE.with_suffix(".zip").unlink()

    shutil.make_archive(str(ZIP_BASE), "zip", root_dir=TARGET_DIR)
    print(f"Created folder: {TARGET_DIR}")
    print(f"Created zip: {ZIP_BASE.with_suffix('.zip')}")


if __name__ == "__main__":
    main()