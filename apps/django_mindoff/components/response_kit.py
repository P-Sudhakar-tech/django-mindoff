# ----------------------------------
# response_kit.py
# ----------------------------------
"""
USAGE:
mo_response_kit.json_response(code="ERR", category="danger", data=[])
mo_response_kit.json_response(code="ERR", category="danger", data=[], exception=e)
@mo_response_kit.response_guardian
"""
import io
import logging
import traceback
import csv
import uuid
import mimetypes
import textwrap
import inspect
from pathlib import Path
from typing import List, Dict, Any, Literal, Union
from types import SimpleNamespace
from functools import wraps
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from django.http import FileResponse
from typeguard import typechecked
from .validation_kit import mo_validation_kit
from .helper_kit import mo_helper_kit

# ----------------------------------
# Constants
# ----------------------------------
REQUIRED_HEADERS = ["code", "title", "description", "status"]
ALLOWED_STATUSES = {"ok", "fail"}
MINDOFF_RESPONSES = {}
logger = logging.getLogger(__name__)
CategoryOptions = Literal["danger", "warning", "info", "success"]
default_json_response_status = "fail"
default_json_response_code = "UNEXPECTED_ERR"
default_json_response_title = "Uh Oh!"
default_json_response_description = "An Unexpected Error has occurred."
default_json_response = {
    "status": default_json_response_status,
    "message": {
        "code": default_json_response_code,
        "title": default_json_response_title,
        "description": default_json_response_description,
        "category": "danger",
    },
    "data": [],
}


# ----------------------------------
# Main Functions
# ----------------------------------
# 1. Load responses from config/responses.csv into MINDOFF_RESPONSES dict.
def load_responses_csv(csv_location=None):
    csv_path = csv_location or _get_csv_path()
    mo_validation_kit.ensure_exists(path=csv_path, is_exception=True)
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        sample = csvfile.read(1024)
        csvfile.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t")
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(csvfile, dialect=dialect, quotechar='"')
        actual_headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        missing = [h for h in REQUIRED_HEADERS if h not in actual_headers]
        mo_validation_kit.ensure_falsey(
            value=missing,
            msg=f"Missing required headers: {missing}. Perhaps a typo? Or too many additional columns?",
            is_exception=True,
        )
        header_map = {h.lower(): h for h in reader.fieldnames}
        responses = {}
        seen_codes = set()

        for line_num, row in enumerate(reader, start=2):
            row_data = {
                h: (row[header_map[h]].strip() if row[header_map[h]] else "")
                for h in REQUIRED_HEADERS
            }
            code = str(row_data["code"]).strip().upper()
            mo_validation_kit.ensure_truthy(
                value=code, msg=f"Empty 'code' at line {line_num}", is_exception=True
            )
            mo_validation_kit.ensure_not_in(
                code,
                seen_codes,
                msg=f"Duplicate code '{code}' at line {line_num}",
                is_exception=True,
            )
            seen_codes.add(code)
            row_data["code"] = code
            status_value = row_data["status"].strip().lower()
            mo_validation_kit.ensure_in(
                status_value,
                ALLOWED_STATUSES,
                msg=(
                    f"Invalid status '{row_data['status']}' at line {line_num}. "
                    f"Allowed values: {sorted(ALLOWED_STATUSES)}"
                ),
                is_exception=True,
            )
            for k, v in row_data.items():
                mo_validation_kit.ensure_truthy(
                    value=v, msg=f"Empty '{k}' at line {line_num}", is_exception=True
                )
            responses[code] = {
                "title": row_data["title"],
                "description": row_data["description"],
                "status": status_value,
            }
    defaults = {
        default_json_response_code: {
            "status": default_json_response_status,
            "code": default_json_response_code,
            "title": default_json_response_title,
            "description": default_json_response_description,
        },
        "VALIDATION_ERR": {
            "status": default_json_response_status,
            "code": "VALIDATION_ERR",
            "title": "Validation Failed",
            "description": "Submitted data failed validation.",
        },
        "SUCCESS": {
            "status": "ok",
            "code": "SUCCESS",
            "title": "Success",
            "description": "Operation completed successfully.",
        },
    }

    for k, v in defaults.items():
        responses.setdefault(k, v)
    global MINDOFF_RESPONSES
    MINDOFF_RESPONSES.clear()
    MINDOFF_RESPONSES.update(responses)


# 2. Responses on demand.
# -- 2.1. Json response
@typechecked
def json_response(
    code: str = "",
    category: CategoryOptions = "danger",
    data: List[Dict[str, Any]] = [],
    exception: Exception | None = None,
):
    json_response_msg = default_json_response.copy()
    if code not in MINDOFF_RESPONSES or code == "":
        e = ValueError(f"Unknown error code: '{code}'")
        return json_response(
            code="UNEXPECTED_ERR", category="danger", data=[], exception=e
        )
    response = MINDOFF_RESPONSES[code]
    description = response["description"]
    if exception is not None:
        exception_name = exception.__class__.__name__
        if exception is not None and exception.__traceback__ is not None:
            tb_text = "".join(
                traceback.format_exception(
                    type(exception), exception, exception.__traceback__
                )
            )
        else:
            tb_text = mo_helper_kit.get_exact_traceback()
        pretty_tb = textwrap.indent(tb_text, "    ")
        if settings.DEBUG:
            description = f"{description} | {exception_name}"
            print(
                f"\n========== [MINDOFF EXCEPTION START] ==========\n"
                f"Exception: {exception}\n"
                f"Traceback:\n{pretty_tb}\n"
                f"========== [MINDOFF EXCEPTION END] ==========\n"
            )
        else:
            logger.error(
                "\n========== [MINDOFF EXCEPTION START: %s] ==========\n"
                "Exception:\n%s\n"
                "Traceback:\n%s"
                "\n========== [MINDOFF EXCEPTION END: %s] ==========\n",
                code,
                exception,
                tb_text,
                code,
            )
    json_response_msg["status"] = response["status"]
    json_response_msg["message"]["code"] = code
    json_response_msg["message"]["title"] = response["title"]
    json_response_msg["message"]["description"] = description
    json_response_msg["message"]["category"] = category
    json_response_msg["data"] = data or []
    return Response(
        json_response_msg,
        status=(
            status.HTTP_200_OK
            if json_response_msg.get("status") == "ok"
            else status.HTTP_400_BAD_REQUEST
        ),
    )


# -- 2.2. File response
def file_response(
    file_obj: Union[str, io.BytesIO],
    *,
    filename: str | None = None,
    content_type: str | None = None,
):
    """
    Return a file download response.
    - file_obj can be a file path (str) or a BytesIO object.
    - filename is optional; if not provided, a unique name will be generated.
    - content_type is auto-detected from filename if not provided.
    """
    try:
        if isinstance(file_obj, str):
            guessed_type, _ = mimetypes.guess_type(file_obj)
            response = FileResponse(
                open(file_obj, "rb"), content_type=content_type or guessed_type
            )
            filename = filename or file_obj.split("/")[-1]

        elif isinstance(file_obj, io.BytesIO):
            file_obj.seek(0)  # ensure pointer is at start
            guessed_type, _ = mimetypes.guess_type(filename or "")
            response = FileResponse(file_obj, content_type=content_type or guessed_type)
            if not filename:
                ext = (
                    mimetypes.guess_extension(
                        content_type or guessed_type or "application/octet-stream"
                    )
                    or ".bin"
                )
                filename = f"{uuid.uuid4().hex}{ext}"

        else:
            raise TypeError("file_obj must be a file path (str) or BytesIO")

        if filename:
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return json_response(
            code="UNEXPECTED_ERR", category="danger", data=[], exception=e
        )


# -- 2.3. Text response
def text_response(
    text: str,
    *,
    status_code: int = 200,
):
    return HttpResponse(text, content_type="text/plain", status=status_code)


# -- 2.4. HTML response
def html_response(
    html: str,
    *,
    status_code: int = 200,
):
    return HttpResponse(html, content_type="text/html", status=status_code)


# 3. Try Catch Decorator
def response_guardian(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            return json_response(
                code="UNEXPECTED_ERR", category="danger", data=[], exception=e
            )

    return wrapper


mo_response_kit = SimpleNamespace(
    json_response=json_response,
    file_response=file_response,
    text_response=text_response,
    html_response=html_response,
    response_guardian=response_guardian,
)


# ----------------------------------
# Supporting Functions
# ----------------------------------
def _get_csv_path():
    return Path(settings.BASE_DIR) / "config" / "responses.csv"
