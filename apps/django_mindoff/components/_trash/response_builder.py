import logging
import traceback
from typing import List, Dict, Any, Literal
from django.conf import settings
from apps.django_mindoff.components._response_kit.load_responses_csv import (
    MINDOFF_RESPONSES,
)

logger = logging.getLogger(__name__)
CategoryOptions = Literal["danger", "warning", "info", "success"]


def json_response(
    code: str,
    category: CategoryOptions,
    data: List[Dict[str, Any]] = [],
    exception: Exception | None = None,
):
    if code not in MINDOFF_RESPONSES:
        raise ValueError(f"Unknown error code: {code}")

    response = MINDOFF_RESPONSES[code]
    description = response["description"]

    if exception is not None:
        tb = traceback.format_exception(
            type(exception), exception, exception.__traceback__
        )
        tb_text = "".join(tb)

        if settings.DEBUG:
            description = (
                f"{description} | Exception: {exception}\nTraceback:\n{tb_text}"
            )
            print(f"[MINDOFF DEBUG EXCEPTION] {exception}\n{tb_text}")
        else:
            logger.error(f"[{code}] {response['message']} | {exception}\n{tb_text}")

    return {
        "status": response["status"],
        "message": {
            "code": response["code"],
            "title": response["title"],
            "description": description,
            "category": category,
        },
        "data": data or [],
    }
