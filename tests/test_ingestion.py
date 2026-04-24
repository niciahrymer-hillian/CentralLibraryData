from pathlib import Path

import pytest

from export_java_class_data import assert_files_exist, resolve_input_path


def test_assert_files_exist_raises_for_missing_file(tmp_path: Path) -> None:
    existing = tmp_path / "exists.csv"
    existing.write_text("id\n1\n", encoding="utf-8")

    missing = tmp_path / "missing.csv"
    with pytest.raises(FileNotFoundError):
        assert_files_exist([existing, missing])


def test_resolve_input_path_prefers_cleaned_when_available(tmp_path: Path) -> None:
    data_root = tmp_path / "data"
    cleaned_root = tmp_path / "cleaned"
    data_root.mkdir()
    cleaned_root.mkdir()

    (data_root / "pg_catalog.csv").write_text("id\n1\n", encoding="utf-8")
    cleaned_file = cleaned_root / "pg_catalog.csv"
    cleaned_file.write_text("id\n2\n", encoding="utf-8")

    chosen = resolve_input_path(data_root, cleaned_root, "pg_catalog.csv", prefer_cleaned=True)
    assert chosen == cleaned_file
