import pandas as pd

from export_java_class_data import clean_frame, parse_volume_issue


def test_clean_frame_writes_empty_for_optional_blanks() -> None:
    frame = pd.DataFrame(
        {
            "ID": ["1", "2", ""],
            "Title": ["Alpha", "Beta", "Gamma"],
            "Genre": ["", "Sci-Fi", "Drama"],
        }
    )

    cleaned = clean_frame(frame, ["ID", "Title"])

    assert len(cleaned) == 2
    assert cleaned.loc[0, "Genre"] == "empty"
    assert cleaned.loc[1, "Genre"] == "Sci-Fi"


def test_parse_volume_issue_extracts_values() -> None:
    volume, issue = parse_volume_issue("Volume 12 Number 3")
    assert volume == "12"
    assert issue == "3"


def test_accuracy_spot_check_transform_example() -> None:
    frame = pd.DataFrame(
        {
            "ID": ["100"],
            "Title": ["  Example Title  "],
            "Location": [""],
        }
    )

    cleaned = clean_frame(frame, ["ID", "Title"])
    record = cleaned.iloc[0].to_dict()

    assert record == {
        "ID": "100",
        "Title": "Example Title",
        "Location": "empty",
    }
