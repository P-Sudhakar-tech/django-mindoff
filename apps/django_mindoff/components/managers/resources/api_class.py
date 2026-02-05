from django_mindoff.components.api_kit import mo_api_kit
from django_mindoff.components.response_kit import mo_response_kit
from rest_framework.authentication import OAuth2Authentication
from rest_framework.permissions import IsAuthenticated
from typing import Any, Dict, List, Union, Optional, Literal
from django_mindoff.components.validation_kit import mo_validation_kit
from django_mindoff.components.polars_kit import mo_polars_kit
from django_mindoff.components.crud_kit import mo_crud_kit


class MindOffSampleAPI(mo_api_kit.MindoffAPIMixin):
    # 1. API Configuration -- MANAGED BY MINDOFF -- DO NOT REMOVE ANY OF THE FOLLOWING
    api_url_name: str = "{{API_URL_NAME}}"
    api_name: str = "{{API_HUMAN_NAME}}"
    api_description: str = "API Description"
    process_mode: Literal["direct", "queue"] = "direct"
    allowed_method: Literal["get", "post", "put", "delete"] = "get"

    # 2. Input and Output Configuration -- MANAGED BY MINDOFF -- DO NOT REMOVE ANY OF THE FOLLOWING
    response_type: Literal["json", "plain", "html", "xml", "binary"] = "json"
    max_payload_size: int | float | None = 10  # in Megabytes(MB)
    max_payload_depth: int | None = 20
    payload_validation: Literal["strict", "basic", None] = "strict"
    payload_schema: list | dict | None = None

    # 3. Authentication and Permissions -- Remove the following if authentication not needed
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    @mo_api_kit.api_guardian
    def run(self, request, *args, **kwargs):
        # === Standard Mindoff request access guide ===
        # request.method         → HTTP method
        # request.data           → Body payload
        # request.query_params   → Query string (?key=value)
        # request.headers        → Dictionary-like access to HTTP headers
        # request.user           → Authenticated user (if authentication is enabled)
        # request.auth           → Authentication details/token (if any)
        # request.FILES          → Uploaded files (multipart/form-data)
        # kwargs.get("user_id")  → Value from <int:user_id> in the URL
        # ----- 🚩 Add your API Logic below -----------

        return mo_response_kit.json_response(
            code="SUCCESS", category="success", data={}
        )
