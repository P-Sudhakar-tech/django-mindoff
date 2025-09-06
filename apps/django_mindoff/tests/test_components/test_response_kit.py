"""
VALID:
1. json_response - code ok
2. json_response - code fail
3. json_response - category -- success, warning, info, danger
4. json_response - exception hide if debug false and show if debug true
5. @response_guardian - catch and throw exception
6. mo_response_kit.file_response - trigger download of file from disk
7. mo_response_kit.file_response - trigger download of file from memory
8. html_response - trigger html response
9. text_response - trigger text response
INVALID:
1. json_response - Error Code Missing / Incorrect
2. json_response - Error Category Missing / Incorrect
"""

import pytest
import csv
import logging
import io
import uuid
from copy import deepcopy
from pathlib import Path
from django.conf import settings as django_settings
from apps.django_mindoff.components.tdd_kit import MindoffTestCase
from typeguard import TypeCheckError
from django.http import HttpResponse, FileResponse
from apps.django_mindoff.components.response_kit import (
    mo_response_kit,
    load_responses_csv,
    MINDOFF_RESPONSES,
)


default_data = [{"a": 1}, {"b": 2}]
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


class TestJsonResponse(MindoffTestCase):
    def setup_method(self, method):
        self._original_responses = deepcopy(MINDOFF_RESPONSES)

    def teardown_method(self, method):
        MINDOFF_RESPONSES.clear()
        MINDOFF_RESPONSES.update(self._original_responses)

    @pytest.mark.parametrize("is_debug", [True, False])
    @pytest.mark.parametrize(
        "exception",
        [
            (None),
            (ValueError("Test Exception")),
        ],
    )
    @pytest.mark.parametrize(
        "category",
        [
            ("danger"),
            ("warning"),
            ("info"),
            ("success"),
        ],
    )
    @pytest.mark.parametrize(
        "code, expected_title, expected_description, expected_status",
        [
            ("SUCCESS", "Success", "Operation completed successfully.", "ok"),
            (
                "VALIDATION_ERR",
                "Validation Failed",
                "Submitted data failed validation.",
                "ok",
            ),
            (
                "UNEXPECTED_ERR",
                "Different Title",
                "An Unexpected Error has occurred.",
                "fail",
            ),
        ],
    )
    def test_json_response_valid(
        self,
        settings,
        capsys,
        caplog,
        is_debug,
        code,
        expected_title,
        expected_description,
        expected_status,
        category,
        exception,
    ):
        self._write_csv(CSV_HEADERS_VALID, CSV_DATA_VALID)
        csv_path = Path(django_settings.BASE_DIR) / "config" / "responses.csv"
        load_responses_csv(csv_path)
        assert len(MINDOFF_RESPONSES) == 13
        settings.DEBUG = is_debug
        result = getattr(mo_response_kit, "json_response")(
            code=code, category=category, data=default_data, exception=exception
        )
        if expected_status == "ok":
            assert result.status_code == 200
        else:
            assert result.status_code == 400
        result = result.data
        assert result["status"] == expected_status
        assert result["message"]["code"] == code
        assert result["message"]["title"] == expected_title
        assert expected_description in result["message"]["description"]
        assert len(result["data"]) == len(default_data)
        if exception and expected_status != "ok":
            description = result["message"]["description"]
            exc_name = exception.__class__.__name__
            if is_debug:
                assert exc_name in description
                captured = capsys.readouterr()
                assert "Traceback" in captured.out
                assert "Test Exception" in captured.out
            else:
                assert exc_name not in description
                with caplog.at_level(logging.ERROR):
                    assert any("Traceback" in rec.message for rec in caplog.records)
                    assert any(
                        "Test Exception" in rec.message for rec in caplog.records
                    )

    @pytest.mark.parametrize("is_debug", [True, False])
    @pytest.mark.parametrize(
        "code, expected_error_code",
        [("", "UNEXPECTED_ERR"), ("INVALID_CODE", "UNEXPECTED_ERR")],
    )
    @pytest.mark.parametrize(
        "category",
        [
            ("danger"),
            ("Danger"),
            (""),
            (None),
            ("invalid_category"),
        ],
    )
    def test_json_response_invalid(
        self, settings, capsys, caplog, is_debug, code, expected_error_code, category
    ):
        settings.DEBUG = is_debug

        if category != "danger":
            with pytest.raises(TypeCheckError):
                getattr(mo_response_kit, "json_response")(
                    code=code, category=category, data=default_data
                )
        else:
            result = getattr(mo_response_kit, "json_response")(
                code=code, category=category, data=default_data
            )
            assert result.status_code == 400
            result = result.data
            assert result["status"] == "fail"
            assert result["message"]["code"] == expected_error_code
            if is_debug:
                assert "ValueError" in result["message"]["description"]
                captured = capsys.readouterr()
                assert "Traceback" in captured.out
            else:
                assert "ValueError" not in result["message"]["description"]
                with caplog.at_level(logging.ERROR):
                    assert any("Traceback" in rec.message for rec in caplog.records)

    def _write_csv(self, headers, data):
        config_dir = self.init_temp_dir(addon_path="config")
        csv_file_path = config_dir / "responses.csv"
        with open(csv_file_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(data)


class TestFileResponse(MindoffTestCase):
    def test_from_disk_valid(self, tmp_path):
        test_file = tmp_path / "sample.txt"
        test_file.write_text("hello world")
        response = mo_response_kit.file_response(str(test_file))
        assert isinstance(response, FileResponse)
        header = response["Content-Disposition"]
        assert all(
            part in header for part in ["attachment;", "filename=", "sample.txt"]
        )
        content = b"".join(response)
        assert content == b"hello world"

    def test_from_memory_with_filename_valid(self):
        file_data = io.BytesIO(b"hello memory")
        response = mo_response_kit.file_response(file_data, filename="mem.txt")
        assert isinstance(response, FileResponse)
        assert response["Content-Disposition"] == 'attachment; filename="mem.txt"'
        content = b"".join(response)
        assert content == b"hello memory"

    def test_from_memory_no_filename_valid(self, monkeypatch):
        monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID(int=0))
        file_data = io.BytesIO(b"hello no name")
        response = mo_response_kit.file_response(file_data)
        assert isinstance(response, FileResponse)
        assert response["Content-Disposition"].endswith('.bin"')
        content = b"".join(response)
        assert content == b"hello no name"

    def test_wrong_type_invalid(self):
        response = mo_response_kit.file_response(123)
        response = response.data
        assert response["message"]["code"] == "UNEXPECTED_ERR"
        assert response["status"] == "fail"


class TestHtmlResponse(MindoffTestCase):
    @pytest.mark.parametrize(
        "html, status_code",
        [
            ("<h1>hellow</h1>", 200),
            ("<h1>world</h1>", 201),
            ("<h1>bad request</h1>", 400),
            ("<h1>Not Found</h1>", 404),
        ],
    )
    def test_html_response_valid(self, html, status_code):
        response = mo_response_kit.html_response(html, status_code=status_code)
        assert isinstance(response, HttpResponse)
        assert response.status_code == status_code
        assert response["Content-Type"] == "text/html"
        assert response.content == html.encode()


class TestTextResponse(MindoffTestCase):
    @pytest.mark.parametrize(
        "text, status_code",
        [
            ("hello", 200),
            ("world", 201),
            ("bad request", 400),
        ],
    )
    def test_text_response_valid(self, text, status_code):
        response = mo_response_kit.text_response(text, status_code=status_code)
        assert isinstance(response, HttpResponse)
        assert response.status_code == status_code
        assert response["Content-Type"] == "text/plain"
        assert response.content == text.encode()


class TestExceptionHandler(MindoffTestCase):
    def test_exception_handler_valid(self, rf):
        @mo_response_kit.response_guardian
        def view(request):
            return mo_response_kit.json_response(
                "SUCCESS", category="success", data=default_data
            )

        request = rf.get("/")
        response = view(request)
        assert response.status_code == 200
        result = response.data
        assert result["status"] == "ok"

    @pytest.mark.parametrize("is_debug", [True, False])
    def test_exception_handler_invalid(self, rf, settings, capsys, caplog, is_debug):
        @mo_response_kit.response_guardian
        def view(request):
            raise ValueError("boom")

        settings.DEBUG = is_debug
        request = rf.get("/")
        response = view(request)
        assert response.status_code == 400
        result = response.data
        assert result["status"] == "fail"
        assert result["message"]["code"] == "UNEXPECTED_ERR"
        if is_debug == True:
            assert "ValueError" in result["message"]["description"]
            captured = capsys.readouterr()
            assert "Traceback" in captured.out
            assert "boom" in captured.out
        else:
            assert "ValueError" not in result["message"]["description"]
            with caplog.at_level(logging.ERROR):
                assert any("Traceback" in rec.message for rec in caplog.records)
                assert any("boom" in rec.message for rec in caplog.records)
