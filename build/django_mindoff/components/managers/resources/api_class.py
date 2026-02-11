from django_mindoff.components.api_kit import mo_api_kit
from django_mindoff.components.response_kit import mo_response_kit
from rest_framework.authentication import OAuth2Authentication
from rest_framework.permissions import IsAuthenticated
from typing import Any, Dict, List, Union, Optional, Literal
from django_mindoff.components.validation_kit import mo_validation_kit
from django_mindoff.components.polars_kit import mo_polars_kit
from django_mindoff.components.crud_kit import mo_crud_kit


class MindOffSampleAPI(mo_api_kit.MindoffAPIMixin):
    # 1. API Settings
    api_name = "{{API_HUMAN_NAME}}"
    api_url_name = "{{API_URL_NAME}}"
    api_description = "API Description"
    process_mode = "direct"  # Options: "direct" | "queue"
    method = "get"  # Options: "get" | "post" | "put" | "delete"
    payload_validation = "strict"  # Options: None | "strict" | "flexible" | "basic"
    max_payload_size = 10  # in Megabytes(MB)

    # 2. Sample input and output for automated testing -- Fill the ones applicable
    query_parameter_sample: dict | None = None
    payload_sample: list | dict | None = None
    url_kwargs_sample: dict | None = None
    response_type = "json"  # options: json | plain | html | xml | binary

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
