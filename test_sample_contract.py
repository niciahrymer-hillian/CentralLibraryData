"""Pytest contract tests for golden sample business rules.

Mirrors the Java GoldenSampleContractTest so both teams assert
the identical contract.  Covers:
  Rule 1 – referential integrity (issue.title_id in title.id)
  Rule 2 – issue_count matches linked rows
  Rule 3 – title start_date <= end_date
  Rule 4 – title start_year <= end_year
  Rule 5 – issue.date within title date range
  Rule 6 – issue.pages is a positive integer
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from validate_sample import validate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _csv(headers: list[str], rows: list[list[str]]) -> io.StringIO:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    buf.seek(0)
    return buf


def _write_csv(tmp_path: Path, name: str, headers: list[str], rows: list[list[str]]) -> Path:
    p = tmp_path / name
    p.write_text(_csv(headers, rows).getvalue(), encoding="utf-8")
    return p


TITLE_HEADERS = ["id", "title", "description", "publisher", "trove_url",
                 "download_text", "issue_count", "start_date", "end_date",
                 "start_year", "end_year", "extent", "place", "issn", "catalogue_url"]

ISSUE_HEADERS = ["id", "title_id", "title", "description", "date", "url",
                 "pages", "text_download_url"]

GOOD_TITLE = [
    "nla.obj-9000000001", "Sample Gazette", "Demo", "Publisher",
    "https://nla.gov.au/nla.obj-9000000001", "https://example.org/sample.zip",
    "1", "2020-01-15", "2020-01-15", "2020", "2020",
    "1 volume", "Australia", "1234-5678", "https://nla.gov.au/nla.cat-vn1",
]

GOOD_ISSUE = [
    "nla.obj-9000001001", "nla.obj-9000000001", "Sample Gazette",
    "Volume 1 Number 1", "2020-01-15",
    "https://nla.gov.au/nla.obj-9000001001", "24",
    "https://trove.nla.gov.au/nla.obj-9000001001/download",
]


# ---------------------------------------------------------------------------
# Canonical golden sample — must be violation-free
# ---------------------------------------------------------------------------

class TestGoldenSampleFiles:
    """Load the actual files shipped in both package variants."""

    PACKAGES = [
        Path(__file__).parent / "java_team_package_small",
        Path(__file__).parent / "java_team_package_small_cleaned",
    ]

    @pytest.mark.parametrize("pkg_dir", PACKAGES, ids=["small", "small_cleaned"])
    def test_no_violations(self, pkg_dir: Path) -> None:
        titles = pkg_dir / "valid-periodical-titles-sample.csv"
        issues = pkg_dir / "valid-periodical-issues-sample.csv"
        assert titles.exists(), f"Missing {titles}"
        assert issues.exists(), f"Missing {issues}"

        violations = validate(titles, issues)
        assert violations == [], "Violations found:\n" + "\n".join(str(v) for v in violations)


# ---------------------------------------------------------------------------
# Rule-specific unit tests using in-memory CSVs
# ---------------------------------------------------------------------------

class TestRule1ReferentialIntegrity:
    def test_matching_title_id_passes(self, tmp_path: Path) -> None:
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [GOOD_ISSUE])
        assert validate(titles, issues) == []

    def test_unknown_title_id_fails(self, tmp_path: Path) -> None:
        bad_issue = GOOD_ISSUE[:1] + ["nla.obj-UNKNOWN"] + GOOD_ISSUE[2:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [bad_issue])
        violations = validate(titles, issues)
        assert any("rule1" in v.rule for v in violations)


class TestRule2IssueCount:
    def test_matching_count_passes(self, tmp_path: Path) -> None:
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [GOOD_ISSUE])
        assert validate(titles, issues) == []

    def test_mismatched_count_fails(self, tmp_path: Path) -> None:
        # title says issue_count=2 but only 1 issue row
        bad_title = GOOD_TITLE[:6] + ["2"] + GOOD_TITLE[7:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [bad_title])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [GOOD_ISSUE])
        violations = validate(titles, issues)
        assert any("rule2" in v.rule for v in violations)

    def test_zero_count_with_no_issues_passes(self, tmp_path: Path) -> None:
        no_issues_title = GOOD_TITLE[:6] + ["0"] + GOOD_TITLE[7:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [no_issues_title])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [])
        assert validate(titles, issues) == []


class TestRule3DateOrder:
    def test_equal_dates_pass(self, tmp_path: Path) -> None:
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [GOOD_ISSUE])
        assert validate(titles, issues) == []

    def test_start_after_end_fails(self, tmp_path: Path) -> None:
        bad_title = GOOD_TITLE[:7] + ["2021-01-01", "2020-01-01"] + GOOD_TITLE[9:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [bad_title])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [])
        violations = validate(titles, issues)
        assert any("rule3" in v.rule for v in violations)

    def test_missing_end_date_passes(self, tmp_path: Path) -> None:
        open_ended_title = GOOD_TITLE[:8] + [""] + GOOD_TITLE[9:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [open_ended_title])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [])
        assert validate(titles, issues) == []


class TestRule4YearOrder:
    def test_equal_years_pass(self, tmp_path: Path) -> None:
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [GOOD_ISSUE])
        assert validate(titles, issues) == []

    def test_start_year_after_end_year_fails(self, tmp_path: Path) -> None:
        bad_title = GOOD_TITLE[:9] + ["2022", "2019"] + GOOD_TITLE[11:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [bad_title])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [])
        violations = validate(titles, issues)
        assert any("rule4" in v.rule for v in violations)


class TestRule5IssueDateInRange:
    def test_date_on_boundary_passes(self, tmp_path: Path) -> None:
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [GOOD_ISSUE])
        assert validate(titles, issues) == []

    def test_date_before_start_fails(self, tmp_path: Path) -> None:
        early_issue = GOOD_ISSUE[:4] + ["2019-12-31"] + GOOD_ISSUE[5:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [early_issue])
        violations = validate(titles, issues)
        assert any("rule5" in v.rule for v in violations)

    def test_date_after_end_fails(self, tmp_path: Path) -> None:
        late_issue = GOOD_ISSUE[:4] + ["2021-01-01"] + GOOD_ISSUE[5:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [late_issue])
        violations = validate(titles, issues)
        assert any("rule5" in v.rule for v in violations)

    def test_missing_issue_date_skipped(self, tmp_path: Path) -> None:
        no_date_issue = GOOD_ISSUE[:4] + [""] + GOOD_ISSUE[5:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [no_date_issue])
        assert validate(titles, issues) == []


class TestRule6PagesPositive:
    def test_positive_pages_pass(self, tmp_path: Path) -> None:
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [GOOD_ISSUE])
        assert validate(titles, issues) == []

    def test_zero_pages_fails(self, tmp_path: Path) -> None:
        zero_pages_issue = GOOD_ISSUE[:6] + ["0"] + GOOD_ISSUE[7:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [zero_pages_issue])
        violations = validate(titles, issues)
        assert any("rule6" in v.rule for v in violations)

    def test_negative_pages_fails(self, tmp_path: Path) -> None:
        neg_pages_issue = GOOD_ISSUE[:6] + ["-5"] + GOOD_ISSUE[7:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [neg_pages_issue])
        violations = validate(titles, issues)
        assert any("rule6" in v.rule for v in violations)

    def test_missing_pages_skipped(self, tmp_path: Path) -> None:
        no_pages_issue = GOOD_ISSUE[:6] + [""] + GOOD_ISSUE[7:]
        titles = _write_csv(tmp_path, "titles.csv", TITLE_HEADERS, [GOOD_TITLE])
        issues = _write_csv(tmp_path, "issues.csv", ISSUE_HEADERS, [no_pages_issue])
        assert validate(titles, issues) == []
