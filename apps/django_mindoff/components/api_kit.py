from rest_framework import status
from rest_framework.response import Response
from django.http import JsonResponse
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
from ._api_kit.service import enqueue_process

ALLOWED_METHODS = ["get", "post", "put", "delete"]


# [API KIT] SECTION 1. THE API GUARDIAN
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


# [API KIT] SECTION 2. THE API GATEWAY
class MindoffAPIMixin(View):
    # 1. API Settings
    api_url_name: str = ""
    api_name: str = ""
    api_description: str = ""
    process_mode: Literal["direct", "queue"] = "direct"
    allowed_method: Literal["get", "post", "put", "delete"] = ""

    # 2. Sample input and output for automated testing
    response_type: Literal["json", "plain", "html", "xml", "binary"] = "json"
    max_payload_size: int | float | None = 10  # in Megabytes(MB)
    max_payload_depth: int | None = 20
    payload_validation: Literal["strict", "basic", None] = "strict"
    payload_schema: list | dict | None = None

    @api_guardian
    def dispatch(self, request, *args, **kwargs):
        # --- 1. allowed_method check ---
        mo_validation_kit.ensure_exists(
            self.allowed_method,
            msg=f"Valid Method must be configured in {self.api_url_name} api",
            is_exception=True,
        )
        mo_validation_kit.ensure_in(
            self.allowed_method.lower(),
            ALLOWED_METHODS,
            msg=f"Method {self.allowed_method} configured in API is not allowed",
            is_exception=True,
        )
        mo_validation_kit.ensure_equal(
            self.allowed_method.upper(),
            request.method,
            msg=f"Method '{request.method}' not allowed",
        )

        if self.payload_schema and request.method in ("POST", "PUT"):
            payload = request.data
            # --- 2. payload size check ---
            if self.max_payload_size is not None:
                raw_body = getattr(request, "body", b"")
                mo_validation_kit.ensure_greater(
                    self.max_payload_size,
                    0,
                    msg=(
                        f"`max_payload_size` must be configured with a positive integer (> 0) "
                        f"for the `{self.api_url_name}` API"
                    ),
                    is_exception=True,
                )
                if isinstance(raw_body, (bytes, bytearray)):
                    size_mb = len(raw_body) / (1024 * 1024)
                    mo_validation_kit.ensure_lesser_equal(
                        float(size_mb),
                        float(self.max_payload_size),
                        msg=f"Payload too large: {size_mb:.2f} MB (Limit: {self.max_payload_size} MB)",
                    )

            # --- 3. payload schema check ---
            if self.max_payload_depth is not None:
                mo_validation_kit.ensure_greater(
                    self.max_payload_depth,
                    0,
                    msg=(
                        f"`max_payload_depth` must be configured with a positive integer (> 0) "
                        f"for the `{self.api_url_name}` API"
                    ),
                    is_exception=True,
                )
            if self.payload_validation is not None:
                validate_schema(
                    payload,
                    self.payload_schema,
                    max_nesting_depth=self.max_payload_depth,
                    validation_mode=self.payload_validation,
                )

        # --- 4. Queue Process if applicable ---
        mo_validation_kit.ensure_in(
            self.process_mode,
            ("direct", "queue"),
            is_exception=True,
            msg=f"Process_mode must be either 'direct' or 'queue' in {self.api_url_name} API",
        )
        if self.process_mode == "queue":
            queue_id = enqueue_process(
                request=request,
                api_instance=self,
            )

            return JsonResponse(
                {
                    "status": "queue",
                    "queue_id": queue_id,
                    "ws_url": build_ws_url(queue_id),
                },
                status=202,
            )
        return super().dispatch(request, *args, **kwargs)

    def run(self, request, *args, **kwargs):
        raise NotImplementedError("You must implement run() in your API class")


mo_api_kit = SimpleNamespace(
    api_guardian=api_guardian,
    MindoffAPIMixin=MindoffAPIMixin,
)
