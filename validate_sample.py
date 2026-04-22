#!/usr/bin/env python3
"""Validate golden valid-sample CSV files against the data contract business rules.

Business rules (must all pass):
  1. Every issue.title_id must match an existing title.id
  2. title.issue_count must equal the number of linked issue rows
  3. title.start_date <= title.end_date (when both are present)
  4. title.start_year <= title.end_year (when both are present)
  5. issue.date must fall within the title date range (when all three are present)
  6. issue.pages must be a positive integer

Usage:
  python validate_sample.py <titles_csv> <issues_csv>

  # Validate both package variants in one call:
  python validate_sample.py \
      java_team_package_small/valid-periodical-titles-sample.csv \
      java_team_package_small/valid-periodical-issues-sample.csv

Exit code: 0 on success, 1 on any violation.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path


def _parse_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    return date.fromisoformat(value)


def _parse_int(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    return int(value)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


class Violation:
    def __init__(self, rule: str, detail: str) -> None:
        self.rule = rule
        self.detail = detail

    def __str__(self) -> str:
        return f"[{self.rule}] {self.detail}"


def validate(titles_path: Path, issues_path: Path) -> list[Violation]:
    titles = load_csv(titles_path)
    issues = load_csv(issues_path)
    violations: list[Violation] = []

    # Index titles by id
    title_by_id: dict[str, dict[str, str]] = {}
    for t in titles:
        tid = t.get("id", "").strip()
        if tid:
            title_by_id[tid] = t

    # Build count of issues per title_id
    issues_per_title: dict[str, int] = {}
    for issue in issues:
        tid = issue.get("title_id", "").strip()
        issues_per_title[tid] = issues_per_title.get(tid, 0) + 1

    # --- Rule 1 & 2: referential integrity + issue_count ---
    for issue in issues:
        iid = issue.get("id", "").strip()
        tid = issue.get("title_id", "").strip()
        if tid not in title_by_id:
            violations.append(Violation(
                "rule1-referential-integrity",
                f"issue {iid!r}: title_id {tid!r} has no matching title.id",
            ))

    for t in titles:
        tid = t.get("id", "").strip()
        try:
            declared_count = _parse_int(t.get("issue_count", ""))
        except ValueError:
            violations.append(Violation(
                "rule2-issue-count",
                f"title {tid!r}: issue_count is not an integer",
            ))
            continue
        if declared_count is None:
            continue
        actual_count = issues_per_title.get(tid, 0)
        if declared_count != actual_count:
            violations.append(Violation(
                "rule2-issue-count",
                f"title {tid!r}: issue_count={declared_count} but {actual_count} linked issue row(s) in file",
            ))

    # --- Rules 3 & 4: title date/year ordering ---
    for t in titles:
        tid = t.get("id", "").strip()
        try:
            start_date = _parse_date(t.get("start_date", ""))
            end_date = _parse_date(t.get("end_date", ""))
        except ValueError as exc:
            violations.append(Violation("rule3-date-order", f"title {tid!r}: unparseable date — {exc}"))
            continue

        if start_date and end_date and start_date > end_date:
            violations.append(Violation(
                "rule3-date-order",
                f"title {tid!r}: start_date {start_date} is after end_date {end_date}",
            ))

        try:
            start_year = _parse_int(t.get("start_year", ""))
            end_year = _parse_int(t.get("end_year", ""))
        except ValueError as exc:
            violations.append(Violation("rule4-year-order", f"title {tid!r}: unparseable year — {exc}"))
            continue

        if start_year is not None and end_year is not None and start_year > end_year:
            violations.append(Violation(
                "rule4-year-order",
                f"title {tid!r}: start_year {start_year} > end_year {end_year}",
            ))

    # --- Rule 5: issue date within title date range ---
    for issue in issues:
        iid = issue.get("id", "").strip()
        tid = issue.get("title_id", "").strip()
        title = title_by_id.get(tid)
        if not title:
            continue  # already reported by rule 1

        try:
            issue_date = _parse_date(issue.get("date", ""))
            start_date = _parse_date(title.get("start_date", ""))
            end_date = _parse_date(title.get("end_date", ""))
        except ValueError as exc:
            violations.append(Violation("rule5-issue-date-in-range", f"issue {iid!r}: unparseable date — {exc}"))
            continue

        if issue_date and start_date and issue_date < start_date:
            violations.append(Violation(
                "rule5-issue-date-in-range",
                f"issue {iid!r}: date {issue_date} is before title start_date {start_date}",
            ))
        if issue_date and end_date and issue_date > end_date:
            violations.append(Violation(
                "rule5-issue-date-in-range",
                f"issue {iid!r}: date {issue_date} is after title end_date {end_date}",
            ))

    # --- Rule 6: positive page count ---
    for issue in issues:
        iid = issue.get("id", "").strip()
        try:
            pages = _parse_int(issue.get("pages", ""))
        except ValueError:
            violations.append(Violation("rule6-pages-positive", f"issue {iid!r}: pages is not an integer"))
            continue
        if pages is not None and pages <= 0:
            violations.append(Violation(
                "rule6-pages-positive",
                f"issue {iid!r}: pages={pages} must be > 0",
            ))

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate golden sample CSVs against business rules.")
    parser.add_argument("titles_csv", type=Path, help="Path to valid-periodical-titles-sample.csv")
    parser.add_argument("issues_csv", type=Path, help="Path to valid-periodical-issues-sample.csv")
    args = parser.parse_args()

    violations = validate(args.titles_csv, args.issues_csv)
    if violations:
        print(f"FAIL — {len(violations)} violation(s):")
        for v in violations:
            print(f"  {v}")
        return 1

    print("OK — all business rules satisfied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
