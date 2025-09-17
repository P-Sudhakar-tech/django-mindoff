import csv
from pathlib import Path

from django.conf import settings

from .if_validator import MindoffValidator

REQUIRED_HEADERS = ["code", "title", "description", "status"]
ALLOWED_STATUSES = {"ok", "fail"}
MINDOFF_RESPONSES = {}
mo_validator = MindoffValidator()


def load_responses_csv(csv_location=None):
    """Load responses from config/responses.csv into MINDOFF_RESPONSES dict."""
    csv_path = csv_location or _get_csv_path()
    mo_validator.ensure_exists(path=csv_path)
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
        mo_validator.ensure_falsey(
            value=missing,
            msg=f"Missing required headers: {missing}. Perhaps a typo? Or too many additional columns?",
        )
        header_map = {h.lower(): h for h in reader.fieldnames}
        responses = {}
        seen_codes = set()

        for line_num, row in enumerate(reader, start=2):
            row_data = {
                h: (row[header_map[h]].strip() if row[header_map[h]] else "")
                for h in REQUIRED_HEADERS
            }

            # --- Normalize code ---
            code = str(row_data["code"]).strip().upper()
            mo_validator.ensure_truthy(
                value=code, msg=f"Empty 'code' at line {line_num}"
            )
            mo_validator.ensure_not_in(
                code, seen_codes, msg=f"Duplicate code '{code}' at line {line_num}"
            )
            seen_codes.add(code)
            row_data["code"] = code

            # --- Validate status ---
            status_value = row_data["status"].strip().lower()
            mo_validator.ensure_in(
                status_value,
                ALLOWED_STATUSES,
                msg=(
                    f"Invalid status '{row_data['status']}' at line {line_num}. "
                    f"Allowed values: {sorted(ALLOWED_STATUSES)}"
                ),
            )

            # --- Enforce no empty fields ---
            for k, v in row_data.items():
                mo_validator.ensure_truthy(
                    value=v, msg=f"Empty '{k}' at line {line_num}"
                )
            responses[code] = {
                "title": row_data["title"],
                "description": row_data["description"],
                "status": status_value,  # stored lowercase
            }

    global MINDOFF_RESPONSES
    MINDOFF_RESPONSES = responses


def _get_csv_path():
    return Path(settings.BASE_DIR) / "config" / "responses.csv"
