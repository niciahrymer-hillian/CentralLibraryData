Java Team Sample Package (Cleaned)

This package contains compact sample datasets generated from cleaned_data/CentralLibraryData.

Sampling method:
- CSV files: header + first 20 data rows + last 20 data rows
- NDJSON files: first 20 lines + last 20 lines

Validation status:
- Source cleaned files were validated on 2026-04-22
- CSV column-shape checks passed
- JSON/NDJSON parsing checks passed

Golden valid sample records:
- valid-periodical-titles-sample.csv
- valid-periodical-issues-sample.csv

Business-rule contract for the golden sample:
- periodical-issues.title_id must match periodical-titles.id
- periodical-titles.issue_count must equal the number of linked issue rows in the sample
- periodical-titles.start_date <= periodical-titles.end_date
- periodical-titles.start_year <= periodical-titles.end_year
- periodical-issues.date must be within the title date range
- periodical-issues.pages must be a positive integer

Java contract test:
- Location: java-contract-tests/
- Run: cd java-contract-tests && mvn test
- Test class: src/test/java/org/example/GoldenSampleContractTest.java
