package org.example;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

class GoldenSampleContractTest {

    @Test
    void goldenSampleSatisfiesBusinessRules() throws IOException {
        Path root = Path.of("..");
        Map<String, String> title = readSingleRow(root.resolve("valid-periodical-titles-sample.csv"));
        Map<String, String> issue = readSingleRow(root.resolve("valid-periodical-issues-sample.csv"));

        assertNotNull(title);
        assertNotNull(issue);

        String titleId = title.get("id");
        assertEquals(titleId, issue.get("title_id"), "issue.title_id must match title.id");

        LocalDate startDate = LocalDate.parse(title.get("start_date"));
        LocalDate endDate = LocalDate.parse(title.get("end_date"));
        LocalDate issueDate = LocalDate.parse(issue.get("date"));

        assertFalse(startDate.isAfter(endDate), "title start_date must be <= end_date");
        assertTrue((!issueDate.isBefore(startDate)) && (!issueDate.isAfter(endDate)),
            "issue date must be within title date range");

        int startYear = Integer.parseInt(title.get("start_year"));
        int endYear = Integer.parseInt(title.get("end_year"));
        assertTrue(startYear <= endYear, "title start_year must be <= end_year");

        int issueCount = Integer.parseInt(title.get("issue_count"));
        assertEquals(1, issueCount, "title issue_count must equal linked issue row count in sample");

        int pages = Integer.parseInt(issue.get("pages"));
        assertTrue(pages > 0, "issue pages must be positive");
    }

    private static Map<String, String> readSingleRow(Path file) throws IOException {
        List<String> lines = Files.readAllLines(file);
        if (lines.size() < 2) {
            throw new IllegalStateException("Expected header + 1 data row in " + file);
        }

        String[] header = lines.get(0).split(",", -1);
        String[] row = lines.get(1).split(",", -1);
        if (header.length != row.length) {
            throw new IllegalStateException("Header/data column mismatch in " + file);
        }

        Map<String, String> record = new HashMap<>();
        for (int i = 0; i < header.length; i++) {
            record.put(header[i], row[i]);
        }
        return record;
    }
}
