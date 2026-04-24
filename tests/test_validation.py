import pandas as pd
import pytest

from export_java_class_data import enforce_unique_ids, require_columns, standardize_date


def test_require_columns_raises_when_missing() -> None:
    frame = pd.DataFrame({"a": [1], "b": [2]})
    with pytest.raises(ValueError):
        require_columns(frame, ["a", "c"], "demo.csv")


def test_enforce_unique_ids_raises_for_duplicates() -> None:
    frame = pd.DataFrame({"ID": ["1", "1", "2"]})
    with pytest.raises(ValueError):
        enforce_unique_ids(frame, "DVD", "ID")


def test_standardize_date_common_formats() -> None:
    assert standardize_date("2026/04/24") == "2026-04-24"
    assert standardize_date("Apr 24, 2026") == "2026-04-24"
    assert standardize_date("not-a-date") == ""
