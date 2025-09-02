"""
_response_kit -> load_response.py -- Test Cases:
Approach: Write a temp csv file and load it from a temp directory. settings also needs to
be altered temporarily to point to the right directory.
---ACCEPTANCE---
1. load_csv_with_data_valid: Load the file successfuly with 5 success and 5 fail responses
2. Load the file with extra headers -> just take only the required headers and proceed.
3. Case sensitive headers -> convert to lowercase and proceed.
4. Duplicate Title -> Allowed
---REJECTION---
1. Missing File -> Raise Error
2. Missing Headers -> Raise Error -> Ask to check if the headers are not mispronounced
3. Duplicate Code -> Raise Error
4. Duplicate Description -> Raise Error
5. No Empty values in any column -> Raise Error
6. Invalid Status -> Raise Error
---BOUNDARY---
None
---ANOMALY---
None
"""

import pytest
import os
import uuid
import csv
from pathlib import Path
from django.conf import settings
from apps.django_mindoff.components.response_kit import (
    load_responses_csv,
    MINDOFF_RESPONSES,
)
from django_mindoff.components.helpers.tdd_fixtures import LogicTestCase


CSV_HEADERS_VALID = ["code", "title", "description", "status"]
CSV_DATA_VALID = [
    ["UNEXPECTED_ERR", "Different Title", "An Unexpected Error has occurred.", "fail"],
    ["VALIDATION_ERR", "Validation Failed", "Submitted data failed validation.", "ok"],
    ["SUCCESS", "Success", "Operation completed successfully.", "ok"],
    ["SUCCESS001", "User Created", "The user has been created.", "ok"],
    ["SUCCESS002", "Data Saved", "Data saved without any issues.", "ok"],
    ["SUCCESS003", "Operation Completed", "The request completed.", "ok"],
    ["SUCCESS004", "Email Sent", "Email has been sent successfully.", "ok"],
    ["SUCCESS005", "File Uploaded", "File uploaded successfully.", "ok"],
    ["ERR001", "Invalid Input", "The provided input is invalid.", "fail"],
    ["ERR002", "Not Found", "The requested resource was not found.", "fail"],
    ["ERR003", "Permission Denied", "You do not have permission.", "fail"],
    ["ERR004", "Server Error", "An unexpected server error occurred.", "fail"],
    ["ERR005", "Timeout", "The operation timed out. Please try again.", "fail"],
]
CSV_DATA_EMPTY_VALID = []
CSV_EXTRA_HEADERS_VALID = [row + ["extra_column_value"] for row in CSV_DATA_VALID]
CSV_HEADERS_CASE_MIXED_VALID = ["Code", "TITLE", "Description", "STATUS"]
CSV_DATA_DUPLICATE_TITLE_VALID = CSV_DATA_VALID + [
    ["DUPT001", "User Created", "A different description.", "ok"]
]
CSV_MISSING_HEADERS_REJECT = ["code", "title", "description", "status"]
CSV_DATA_MISSING_HEADERS_REJECT = [
    ["SUCCESS001", "User Created", "The user has been created."]
]
CSV_DATA_DUPLICATE_CODE_REJECT = CSV_DATA_VALID + [
    ["SUCCESS001", "Duplicate Code", "Duplicate code description.", "ok"]
]
CSV_DATA_PARTIAL_EMPTY_REJECT = [
    ["SUCCESS001", "User Created", "The user has been created.", "ok"],
    ["SUCCESS002", "Data Saved", "Data saved without any issues.", "ok"],
    ["SUCCESS003", "Operation Completed", "", "ok"],
    ["SUCCESS004", "Email Sent", "Email has been sent successfully.", "ok"],
    ["SUCCESS005", "File Uploaded", "File uploaded successfully.", "ok"],
    ["", "", "The provided input is invalid.", "fail"],
    ["ERR002", "Not Found", "The requested resource was not found.", ""],
    ["ERR003", "Permission Denied", "You do not have permission.", "fail"],
    ["ERR004", "Server Error", "An unexpected server error occurred.", "fail"],
    ["ERR005", "Timeout", "The operation timed out. Please try again.", "fail"],
]
CSV_DATA_INVALID_STATUS_REJECT = [
    ["SUCCESS001", "User Created", "The user has been created.", "ok"],
    ["SUCCESS002", "Data Saved", "Data saved without any issues.", "fail"],
]


class TestLoadResponsesCSV(LogicTestCase):

    # ================= VALID TEST CASES =================
    def test_load_csv_with_data_valid(self):
        self._write_csv(CSV_HEADERS_VALID, CSV_DATA_VALID)
        self._common_assertions(CSV_DATA_VALID)

    def test_load_csv_with_extra_headers(self):
        extra_headers = CSV_HEADERS_VALID + ["extra_column"]
        extra_data = [row + ["extra_value"] for row in CSV_DATA_VALID]
        self._write_csv(extra_headers, extra_data)
        self._common_assertions(CSV_DATA_VALID)  # Should ignore extra column

    def test_load_csv_case_insensitive_headers(self):
        headers_mixed = ["Code", "TITLE", "Description", "STATUS"]
        self._write_csv(headers_mixed, CSV_DATA_VALID)
        self._common_assertions(CSV_DATA_VALID)  # Should convert headers to lowercase

    def test_load_csv_with_duplicate_title_allowed(self):
        duplicate_title_data = CSV_DATA_VALID + [
            ["DUPT001", "User Created", "Another description", "ok"]
        ]
        self._write_csv(CSV_HEADERS_VALID, duplicate_title_data)
        self._common_assertions(duplicate_title_data)

    def _common_assertions(self, expected_data):
        """Common function to validate MINDOFF_RESPONSES dict after loading CSV"""
        csv_path = Path(settings.BASE_DIR) / "config" / "responses.csv"
        load_responses_csv(csv_path)
        responses = MINDOFF_RESPONSES
        self.asserts.assertEqual(len(responses), len(expected_data))
        for row in expected_data:
            code, title, description, status = row
            self.asserts.assertIn(code, responses)
            self.asserts.assertEqual(responses[code]["title"], title)
            self.asserts.assertEqual(responses[code]["description"], description)
            self.asserts.assertEqual(responses[code]["status"], status)

    def _write_csv(self, headers, data):
        config_dir = self.init_temp_dir(addon_path="config")
        csv_file_path = config_dir / "responses.csv"
        with open(csv_file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)

    # ================= REJECTION TEST CASES =================
    def test_missing_file_raises_error(self):
        self._write_csv(CSV_HEADERS_VALID, CSV_DATA_VALID)
        csv_path = Path(settings.BASE_DIR) / "config" / "responses.csv"
        if csv_path.exists():
            os.remove(csv_path)
        with self.asserts.assertRaises(FileNotFoundError):
            load_responses_csv()

    def test_missing_headers_raises_error(self):
        incomplete_headers = ["code", "title"]  # Missing description and status
        self._write_csv(incomplete_headers, CSV_DATA_VALID)
        with self.asserts.assertRaises(Exception) as cm:
            load_responses_csv()

    def test_duplicate_code_raises_error(self):
        duplicate_code_data = CSV_DATA_VALID + [
            ["SUCCESS", "Duplicate Code", "Desc", "ok"]
        ]
        self._write_csv(CSV_HEADERS_VALID, duplicate_code_data)
        with self.asserts.assertRaises(Exception) as cm:
            load_responses_csv()
        self.asserts.assertIn("duplicate code", str(cm.exception).lower())

    def test_no_empty_values_allowed(self):
        self._write_csv(CSV_HEADERS_VALID, CSV_DATA_PARTIAL_EMPTY_REJECT)
        with self.asserts.assertRaises(ValueError) as cm:
            load_responses_csv()
        self.asserts.assertIn("empty", str(cm.exception).lower())

    def test_invalid_status_raises_error(self):
        self._write_csv(CSV_HEADERS_VALID, CSV_DATA_INVALID_STATUS_REJECT)
        with self.asserts.assertRaises(LookupError) as cm:
            load_responses_csv()
        self.asserts.assertIn("status", str(cm.exception).lower())


# Helper function to write CSV
