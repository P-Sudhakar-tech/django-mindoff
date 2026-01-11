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
    api_name = "Sample API Name"
    api_description = "Sample API Description"
    method = "get"  # Available Options: "get", "post", "put", "delete"
    process_mode = "direct"

    # 2. Sample input for automated testing -- Fill the ones applicable
    query_parameter_sample = {}
    payload_sample = []

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
        # ----- Add your API Logic below -----------

        return mo_response_kit.json_response(
            code="SUCCESS", category="success", data={}
        )
