from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from types import SimpleNamespace
from functools import wraps
from .response_kit import mo_response_kit
from .validation_kit import mo_validation_kit
from typing import Any, Dict
from ._helper_kit.validate_schema import validate_schema
import json
from typing import Any, Dict, List, Union, Optional, Literal, Callable
from django.views import View

ALLOWED_METHODS = ["get", "post", "put", "delete"]
MAX_PAYLOAD_MB = 5  # MB


def api_guardian(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        try:
            return func(request, *args, **kwargs)
        except Exception as e:
            return mo_response_kit.json_response(
                code="UNEXPECTED_ERR", category="danger", data=[], exception=e
            )

    return wrapper


class MindoffAPIMixin(View):
    api_name: str = ""
    api_description: str = ""
    method: Literal["get", "post", "put", "delete"] = ""
    query_parameter_sample: Dict[str, Any] = {}
    payload_sample: Any = None

    # process_mode can be:
    # - "direct"
    # - "polling"
    # - callable returning one of above
    process_mode: Union[str, Callable[[Any, Dict[str, Any], Dict[str, Any]], str]] = (
        "direct"
    )

    @api_guardian
    def dispatch(self, request, *args, **kwargs):
        # --- method check ---
        mo_validation_kit.ensure_in(
            self.method.lower(),
            ALLOWED_METHODS,
            msg=f"Method '{self.method}' not allowed",
        )

        # --- payload check ---
        payload = request.data
        raw_body = getattr(request, "body", b"")
        if isinstance(raw_body, (bytes, bytearray)):
            size_mb = len(raw_body) / (1024 * 1024)
            mo_validation_kit.ensure_lesser_equal(
                size_mb,
                MAX_PAYLOAD_MB,
                msg=f"Payload too large: {size_mb:.2f} MB (limit {MAX_PAYLOAD_MB} MB)",
            )

        # --- query param check ---
        if self.query_parameter_sample:
            for k, sample_type in self.query_parameter_sample.items():
                mo_validation_kit.ensure_in(
                    k, request.GET, msg=f"Missing query param '{k}'"
                )
                validate_schema(request.GET[k], sample_type)

        # --- payload schema ---
        if self.payload_sample:
            validate_schema(payload, self.payload_sample)

        # --- decide mode ---
        mode = self.process_mode
        if callable(mode):
            mode = mode(request, request.GET, kwargs)

        return self.run(request, *args, **kwargs)
        # if mode == "direct":
        #     return self.run(request, *args, **kwargs)
        # elif mode == "queue":
        #     return start_polling_task(self.run, request, *args, **kwargs)
        # else:
        #     raise ImproperlyConfigured(
        #         "process_mode must be 'direct', 'queue', or a callable returning one of them"
        #     )

    def run(self, request, *args, **kwargs):
        raise NotImplementedError("You must implement run() in your API class")


mo_api_kit = SimpleNamespace(
    api_guardian=api_guardian,
    MindoffAPIMixin=MindoffAPIMixin,
)
