import json
import re
import logging
from pathlib import Path
from unittest.mock import patch
from rest_framework.test import APIClient
from django.urls import reverse, clear_url_caches, get_resolver
from rest_framework import status
from django.contrib.auth import get_user_model
from django.core.checks import run_checks
import pytest
import sys
from django.core.cache import cache

from ...components.tdd_kit import MindoffTestCase
from ...components.response_kit import mo_response_kit
from ...components.helper_kit import mo_helper_kit

User = get_user_model()

# ========================================================================================
# ⚓ CONSTANTS
# ========================================================================================
ALLOWED_METHODS = ["get", "post", "put", "delete"]
ALLOWED_PROCESS_MODES = ["direct", "queue"]
ALLOWED_RESPONSE_TYPES = ["json", "plain", "html", "xml", "binary", "others"]
VALIDATION_MODES = ["strict", "basic", None]


@pytest.mark.django_db(transaction=True)
class TestAPIConfigurationValidation(MindoffTestCase):
    """
    Tests that verify API configuration validation happens at Django startup
    via the checks framework. These ensure invalid configs prevent app from starting.
    """

    EXPECTED_CHECK_ID = "django_mindoff.API_CONFIG_ERR"

    # ------------------------------------------------------------------
    # Invalid Attribute Tests (grouped by type)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        ("attribute", "value", "error_message"),
        [
            ("api_url_name", "", "`api_url_name` must not be empty"),
            ("api_name", "", "`api_name` must not be empty"),
        ],
    )
    def test_config_empty_required_attributes(self, attribute, value, error_message):
        """Verify empty string validation for required attributes"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = f"test_empty_{attribute}_api"
        _create_test_api(app_name, api_name=api_name, base_path=temp_dir_path)

        _modify_api_attribute(
            app_name, api_name, attribute, value, base_path=temp_dir_path
        )
        clear_url_caches()
        _reload_view_module(app_name)

        self._assert_config_error(error_message)

    def test_config_invalid_api_url_name_not_in_urls(self):
        """Verify api_url_name must exist in urls.py"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        _create_test_api(
            app_name, api_name="test_invalid_url_name_api", base_path=temp_dir_path
        )

        _modify_api_attribute(
            app_name,
            "test_invalid_url_name_api",
            "api_url_name",
            "non_existent_url_name",
            base_path=temp_dir_path,
        )

        clear_url_caches()
        _reload_view_module(app_name)

        self._assert_config_error("not found in urls.py")

    def test_config_none_api_description(self):
        """Verify api_description cannot be None"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        _create_test_api(
            app_name, api_name="test_none_desc_api", base_path=temp_dir_path
        )

        _modify_api_attribute(
            app_name,
            "test_none_desc_api",
            "api_description",
            None,
            base_path=temp_dir_path,
        )

        clear_url_caches()
        _reload_view_module(app_name)

        self._assert_config_error(
            "`api_description` must be a string and cannot be None"
        )

    def test_config_non_boolean_allow_duplicate_queue(self):
        """Verify allow_duplicate_queue must be boolean"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        _create_test_api(
            app_name, api_name="test_invalid_dup_queue_api", base_path=temp_dir_path
        )

        _modify_api_attribute(
            app_name,
            "test_invalid_dup_queue_api",
            "allow_duplicate_queue",
            "true",
            base_path=temp_dir_path,
        )

        clear_url_caches()
        _reload_view_module(app_name)

        self._assert_config_error("`allow_duplicate_queue` must be boolean")

    @pytest.mark.parametrize(
        ("attribute", "value", "error_message"),
        [
            (
                "payload_schema",
                "invalid_string_schema",
                "`payload_schema` must be list | dict | None",
            ),
            (
                "max_payload_size",
                "not_a_number",
                "`max_payload_size` must be int | float | None",
            ),
        ],
    )
    def test_config_invalid_type_attributes(self, attribute, value, error_message):
        """Verify type validation for numeric/collection attributes"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = f"test_invalid_{attribute}_type_api"
        _create_test_api(app_name, api_name=api_name, base_path=temp_dir_path)

        _modify_api_attribute(
            app_name, api_name, attribute, value, base_path=temp_dir_path
        )
        clear_url_caches()
        _reload_view_module(app_name)

        self._assert_config_error(error_message)

    def test_config_invalid_payload_validation_type(self):
        """Verify payload_validation accepts only 'strict', 'basic', or None"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        _create_test_api(
            app_name,
            api_name="test_invalid_validation_type_api",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_validation_type_api",
            "payload_validation",
            "invalid_mode",
            base_path=temp_dir_path,
        )

        clear_url_caches()
        _reload_view_module(app_name)

        self._assert_config_error(
            "`payload_validation` must be 'strict', 'basic' or None"
        )

    def test_config_invalid_response_type(self):
        """Verify response_type must be one of allowed types"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        _create_test_api(
            app_name, api_name="test_invalid_response_type_api", base_path=temp_dir_path
        )

        _modify_api_attribute(
            app_name,
            "test_invalid_response_type_api",
            "response_type",
            "invalid_type",
            base_path=temp_dir_path,
        )

        clear_url_caches()
        _reload_view_module(app_name)

        self._assert_config_error("`response_type` must be one of")

    def test_config_invalid_rate_limit_format(self):
        """Verify api_request_limit matches '<int>/(s|m|h|d)' format"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        _create_test_api(
            app_name, api_name="test_invalid_rate_api", base_path=temp_dir_path
        )

        _modify_api_attribute(
            app_name,
            "test_invalid_rate_api",
            "api_request_limit",
            "abc/m",
            base_path=temp_dir_path,
        )

        clear_url_caches()
        _reload_view_module(app_name)
        self._assert_config_error("must match '<int>/(s|m|h|d)' format")

    def _assert_config_error(self, expected_msg_fragment: str):
        errors = run_checks()
        matching = [
            e
            for e in errors
            if e.id == self.EXPECTED_CHECK_ID and expected_msg_fragment in e.msg
        ]
        assert matching, (
            f"Expected config error with id={self.EXPECTED_CHECK_ID} "
            f"and message containing '{expected_msg_fragment}'.\n"
            f"Actual errors: {[ (e.id, e.msg) for e in errors ]}"
        )


@pytest.mark.django_db(transaction=True)
class TestAPIMixinAcceptance(MindoffTestCase):
    """
    Tests that verify valid API configurations work correctly at runtime.
    """

    @pytest.fixture(autouse=True)
    def setup_user(self):
        """Setup test user for authentication tests"""
        self.user = User.objects.create_user(username="testuser", password="pass123")

    def test_api_success_with_generated_api(self):
        """ACCEPTANCE_1: API succeeds with as-is generated API"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_basic_api", base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    @pytest.mark.parametrize(
        "response_type", ["json", "plain", "html", "xml", "binary"]
    )
    def test_api_success_with_response_types(self, response_type):
        """ACCEPTANCE_2: API succeeds with valid response types"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_response_type_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_response_type_api",
            "response_type",
            response_type,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    @pytest.mark.parametrize("http_method", ["get", "post", "put", "delete"])
    def test_api_success_with_allowed_methods(self, http_method):
        """ACCEPTANCE_3: API succeeds with allowed HTTP methods"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_method_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, "test_method_api", "method", http_method, base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = getattr(self.client, http_method)(url)
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    @pytest.mark.parametrize("validation_mode", ["strict", "basic", None])
    def test_api_success_with_payload_validation_modes(self, validation_mode):
        """ACCEPTANCE_4: API succeeds with valid payload_validation modes"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_validation_mode_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_validation_mode_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_validation_mode_api",
            "payload_schema",
            '{"name": str, "age": int}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_validation_mode_api",
            "payload_validation",
            validation_mode,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.post(url, {"name": "John", "age": 30}, format="json")
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    def test_api_success_authenticated_user_with_auth_enabled(self):
        """ACCEPTANCE_5: API succeeds for authenticated users when auth enabled"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_auth_enabled_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_auth_enabled_api",
            "authentication_classes",
            "[BasicAuthentication]",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_auth_enabled_api",
            "permission_classes",
            "[IsAuthenticated]",
            base_path=temp_dir_path,
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(api_url_name)
        response = self.client.get(url)
        self.client.force_authenticate(user=None)
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    def test_api_success_unauthenticated_user_with_auth_disabled(self):
        """ACCEPTANCE_6: API succeeds for unauthenticated users when auth disabled"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_public_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_public_api",
            "permission_classes",
            "[AllowAny]",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    @pytest.mark.parametrize(
        ("attribute", "value"),
        [
            ("api_request_limit", None),
            ("queue_status_streaming_limit", None),
            ("response_validation", False),
        ],
    )
    def test_api_success_optional_attribute_overrides(self, attribute, value):
        """ACCEPTANCE: API succeeds when optional attributes are overridden"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = f"test_acceptance_{attribute}_api"
        api_url_name = _create_test_api(
            app_name,
            api_name=api_name,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            api_name,
            attribute,
            value,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    def test_api_success_basic_validation_allows_extra_fields(self):
        """ACCEPTANCE: API succeeds when extra fields in basic validation mode"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = "test_basic_extra_fields_api"
        api_url_name = _create_test_api(
            app_name,
            api_name=api_name,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name, api_name, "method", "post", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            api_name,
            "payload_schema",
            '{"name": str}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name, api_name, "payload_validation", "basic", base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = self.client.post(
            url,
            {"name": "John", "unexpected": "extra"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"


@pytest.mark.django_db(transaction=True)
class TestAPIMixinRejection(MindoffTestCase):
    """
    Tests that verify API properly rejects invalid requests and exceptions.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(username="testuser", password="pass123")

    @pytest.mark.parametrize("debug_mode", [False, True])
    def test_rejection_exception_from_run_method(self, settings, caplog, debug_mode):
        """REJECTION: Exception from run() is captured at DEBUG={debug_mode}"""
        settings.DEBUG = debug_mode
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_exception_run_api", base_path=temp_dir_path
        )
        run_code = """        raise ValueError("Test run exception")"""
        _modify_api_run_method(
            app_name, "test_exception_run_api", run_code, base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.status_code == 500
        assert response.data["message"]["code"] == "UNEXPECTED_ERR"

    @pytest.mark.parametrize(
        ("configured_method", "requested_method"),
        [
            ("get", "post"),
            ("post", "get"),
            ("put", "delete"),
            ("delete", "post"),
        ],
    )
    def test_rejection_request_method_mismatch(
        self, configured_method, requested_method
    ):
        """REJECTION: Request method must match configured method"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_mismatch_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_mismatch_api",
            "method",
            configured_method,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = getattr(self.client, requested_method)(url)
        assert (
            response.status_code == 400
            and response.data["message"]["code"] == "INVALID_METHOD"
        )

    def test_rejection_unauthenticated_user_with_auth_required(self):
        """REJECTION: Unauthenticated users rejected when auth enabled"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_auth_required_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_auth_required_api",
            "permission_classes",
            "[IsAuthenticated]",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_auth_required_api",
            "authentication_classes",
            "[BasicAuthentication]",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.data["message"]["code"] == "NOT_AUTHENTICATED"
        assert response.status_code == 401

    @patch("apps.django_mindoff.components.api_kit.is_ratelimited")
    def test_rejection_api_request_limit_exceeded(self, mock_limit):
        """REJECTION: API request exceeding rate limit is rejected"""
        cache.clear()
        mock_limit.return_value = True
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_rate_limit_api", base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.data["message"]["code"] == "API_RATE_LIMITED"

    def test_rejection_payload_size_exceeded(self):
        """REJECTION: Payload exceeding max_payload_size is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_size_exceeded_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_size_exceeded_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_size_exceeded_api",
            "max_payload_size",
            0.001,  # 1 KB
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_size_exceeded_api",
            "payload_schema",
            '{"data": str}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_size_exceeded_api",
            "payload_validation",
            "basic",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.post(url, {"data": "x" * 10000}, format="json")
        assert response.data["message"]["code"] == "PAYLOAD_TOO_LARGE"

    @pytest.mark.parametrize(
        ("payload", "schema", "validation_mode", "error_code"),
        [
            (
                {"name": "John"},
                '{"name": str, "age": int}',
                "strict",
                "INVALID_PAYLOAD",
            ),
            (
                {"name": "John", "age": "thirty"},
                '{"name": str, "age": int}',
                "strict",
                "INVALID_PAYLOAD",
            ),
        ],
    )
    def test_rejection_payload_validation_strict_errors(
        self, payload, schema, validation_mode, error_code
    ):
        """REJECTION: Payload fails strict validation with missing/wrong-type fields"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = "test_strict_validation_api"
        api_url_name = _create_test_api(
            app_name, api_name=api_name, base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, api_name, "method", "post", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, api_name, "payload_schema", schema, base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            api_name,
            "payload_validation",
            validation_mode,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.post(url, payload, format="json")
        assert response.data["message"]["code"] == error_code

    def test_rejection_payload_depth_exceeded(self):
        """REJECTION: Payload exceeding max_payload_depth is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_depth_exceeded_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_depth_exceeded_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_depth_exceeded_api",
            "payload_schema",
            '{"level1": {"level2": {"level3": str}}}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_depth_exceeded_api",
            "payload_validation",
            "strict",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_depth_exceeded_api",
            "max_payload_depth",
            2,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        payload = {"level1": {"level2": {"level3": "value"}}}
        response = self.client.post(url, payload, format="json")
        assert response.data["message"]["code"] == "INVALID_PAYLOAD"

    def test_rejection_mindoff_validation_error_from_run(self):
        """REJECTION: MindoffValidationError raised in run() is handled"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name,
            api_name="test_mindoff_validation_error_api",
            base_path=temp_dir_path,
        )
        run_code = """
            from apps.django_mindoff.components.validation_kit import MindoffValidationError
            raise MindoffValidationError(
                code="VALIDATION_ERR",
                category="warning",
                data={"detail": "Custom validation failure"}
            )
        """
        _modify_api_run_method(
            app_name,
            "test_mindoff_validation_error_api",
            run_code,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.status_code == 400
        assert response.data["message"]["code"] == "VALIDATION_ERR"
        assert response.data["message"]["category"] == "warning"

    @pytest.mark.parametrize(
        (
            "exception_code",
            "exception_import",
            "exception_raise",
            "expected_status",
            "expected_code",
        ),
        [
            (
                "PERMISSION_DENIED",
                "from rest_framework.exceptions import PermissionDenied",
                'raise PermissionDenied("Access denied")',
                403,
                "PERMISSION_DENIED",
            ),
            (
                "RATE_LIMITED",
                "from rest_framework.exceptions import Throttled",
                "raise Throttled(wait=60)",
                429,
                "RATE_LIMITED",
            ),
        ],
    )
    def test_rejection_drf_exceptions_from_run(
        self,
        exception_code,
        exception_import,
        exception_raise,
        expected_status,
        expected_code,
    ):
        """REJECTION: DRF exceptions from run() are handled appropriately"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = f"test_{exception_code.lower()}_api"
        api_url_name = _create_test_api(
            app_name, api_name=api_name, base_path=temp_dir_path
        )
        run_code = f"""
            {exception_import}
            {exception_raise}
        """
        _modify_api_run_method(
            app_name,
            api_name,
            run_code,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.status_code == expected_status
        assert response.data["message"]["code"] == expected_code

    def test_rejection_payload_not_allowed_when_schema_none(self):
        """REJECTION: Non-empty payload rejected when payload_schema=None"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = "test_payload_not_allowed_api"
        api_url_name = _create_test_api(
            app_name,
            api_name=api_name,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name, api_name, "method", "post", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, api_name, "payload_schema", None, base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, api_name, "payload_validation", "strict", base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = self.client.post(
            url,
            {"unexpected": "data"},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["message"]["code"] == "PAYLOAD_NOT_ALLOWED"


@pytest.mark.django_db(transaction=True)
class TestAPIMixinBoundary(MindoffTestCase):
    """
    Tests that verify API behavior at boundary and edge case conditions.
    """

    @patch("apps.django_mindoff.components.api_kit.is_ratelimited")
    def test_boundary_api_request_at_exact_limit(self, mock_limit):
        """BOUNDARY: API succeeds when at exact request limit"""
        mock_limit.return_value = False
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_limit_boundary_api", base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    def test_boundary_payload_size_at_exact_limit(self):
        """BOUNDARY: API succeeds when payload size equals max_payload_size"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_size_boundary_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_size_boundary_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_size_boundary_api",
            "max_payload_size",
            1,  # 1 MB
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_size_boundary_api",
            "payload_schema",
            '{"data": str}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_size_boundary_api",
            "payload_validation",
            "basic",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.post(url, {"data": "x" * 1048565}, format="json")
        assert response.data["message"]["code"] == "SUCCESS"

    def test_boundary_payload_validation_none_with_mismatched_payload(self):
        """BOUNDARY: API succeeds with mismatched payload when validation=None"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_validation_none_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_validation_none_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_validation_none_api",
            "payload_schema",
            '{"name": str, "age": int}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_validation_none_api",
            "payload_validation",
            None,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.post(
            url, {"name": "John", "age": "not_an_int"}, format="json"
        )
        assert response.data["message"]["code"] == "SUCCESS"

    def test_boundary_payload_depth_exact(self):
        """BOUNDARY: API succeeds at exact max_payload_depth limit"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_depth_exact_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_depth_exact_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_depth_exact_api",
            "payload_schema",
            '{"level1": {"level2": {"level3": str}}}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_depth_exact_api",
            "payload_validation",
            "strict",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_depth_exact_api",
            "max_payload_depth",
            3,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        payload = {"level1": {"level2": {"level3": "value"}}}
        response = self.client.post(url, payload, format="json")
        assert response.data["message"]["code"] == "SUCCESS"

    @pytest.mark.parametrize(
        ("rate_value", "description"),
        [
            ("1/s", "minimal valid rate"),
            ("9999/d", "large but valid rate"),
        ],
    )
    def test_boundary_valid_rate_limits(self, rate_value, description):
        """BOUNDARY: API succeeds with valid extreme rate limits"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = f"test_boundary_rate_{rate_value.replace('/', '_')}_api"
        api_url_name = _create_test_api(
            app_name,
            api_name=api_name,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            api_name,
            "api_request_limit",
            rate_value,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    def test_boundary_float_max_payload_size(self):
        """BOUNDARY: API succeeds when max_payload_size is a float"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = "test_boundary_float_size_api"
        api_url_name = _create_test_api(
            app_name,
            api_name=api_name,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name, api_name, "method", "post", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, api_name, "max_payload_size", 0.5, base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            api_name,
            "payload_schema",
            '{"data": str}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name, api_name, "payload_validation", "basic", base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = self.client.post(url, {"data": "x" * 1000}, format="json")
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"

    def test_boundary_missing_content_length_header(self):
        """BOUNDARY: API succeeds when CONTENT_LENGTH header is absent"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_name = "test_boundary_missing_content_length_api"
        api_url_name = _create_test_api(
            app_name,
            api_name=api_name,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name, api_name, "method", "post", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, api_name, "max_payload_size", 1, base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            api_name,
            "payload_schema",
            '{"data": str}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name, api_name, "payload_validation", "basic", base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = self.client.post(
            url,
            {"data": "small"},
            format="json",
            CONTENT_LENGTH="",
        )
        assert response.status_code == 200
        assert response.data["message"]["code"] == "SUCCESS"


# ========================================================================================
# 🔧 HELPER FUNCTIONS
# ========================================================================================
def _reload_view_module(app_name: str):
    """Force reload of view module to pick up changes."""
    view_module_name = f"{app_name}.views"
    if view_module_name in sys.modules:
        del sys.modules[view_module_name]


def _create_test_api(
    app_name: str,
    api_name: str,
    url_patterns: list = None,
    base_path: Path = None,
    **overrides,
) -> str:
    """
    Create a test API with optional attribute overrides.

    Args:
        app_name: Name of the app
        api_name: Name of the API (snake_case)
        url_patterns: URL patterns (optional)
        base_path: Base path for the app (defaults to apps directory)
        **overrides: Keyword arguments for attribute overrides

    Returns:
        api_url_name: The URL name for the created API
    """
    base_path = base_path or Path.cwd() / "apps"

    from ...components.managers.create_api import DjangoApiCreator

    creator = DjangoApiCreator(
        api_path=f"{app_name}/{api_name}", url_paths=url_patterns, base_path=base_path
    )
    creator.run()

    app_root = base_path / app_name
    views_path = app_root / "views.py"
    __fix_mock_app_imports(app_root)

    if overrides:
        __apply_api_overrides(views_path, overrides)

    view_module_name = f"{app_name}.views"
    if view_module_name in sys.modules:
        del sys.modules[view_module_name]

    clear_url_caches()

    return f"{app_name}__{api_name}"


def __fix_mock_app_imports(app_root: Path):
    """
    Replace 'django_mindoff' with 'apps.django_mindoff' in core files.

    Args:
        app_root: Root path of the app
    """
    files_to_patch = [
        app_root / "views.py",
        app_root / "models.py",
        app_root / "tests" / "test_views.py",
    ]

    for file_path in files_to_patch:
        if file_path.exists():
            content = file_path.read_text()
            new_content = re.sub(
                r"\bfrom django_mindoff\b", "from apps.django_mindoff", content
            )
            if content != new_content:
                file_path.write_text(new_content)


def __apply_api_overrides(views_path: Path, overrides: dict):
    """
    Apply attribute overrides to the generated views.py file.

    Args:
        views_path: Path to views.py
        overrides: Dictionary of attribute overrides

    Raises:
        FileNotFoundError: If views.py doesn't exist
    """
    if not views_path.exists():
        raise FileNotFoundError(f"Could not find views.py at {views_path}")

    content = views_path.read_text()

    for attr, value in overrides.items():
        if isinstance(value, str):
            v_str = f'"{value}"'
        elif value is None or isinstance(value, bool):
            v_str = str(value)
        else:
            v_str = str(value)

        pattern = rf"(\s+{attr}:\s*[^=]+=\s*)(.+?)(\s*#|$)"
        content = re.sub(pattern, rf"\1{v_str}\3", content, flags=re.MULTILINE)

    views_path.write_text(content)


def _modify_api_attribute(
    app_name: str, api_name: str, attribute: str, value, base_path: Path = None
):
    """
    Modify a specific attribute in an already-created API.

    Args:
        app_name: Name of the app
        api_name: Name of the API (snake_case)
        attribute: Attribute name to modify
        value: New value for the attribute
        base_path: Base path for the app (defaults to apps directory)
    """
    base_path = base_path or Path("apps")
    views_path = base_path / app_name / "views.py"
    content = views_path.read_text()

    if value is None:
        value_str = "None"
    elif isinstance(value, bool):
        value_str = str(value)
    elif isinstance(value, (list, dict)):
        value_str = str(value)
    elif isinstance(value, str):
        code_indicators = ["[", "{", "None"]
        if (
            any(value.strip().startswith(char) for char in code_indicators)
            or value.strip() == "None"
        ):
            value_str = value
        else:
            value_str = f'"{value}"'
    else:
        value_str = str(value)

    pattern = rf"(\s+{attribute}:\s*[^=]+=\s*)(.+?)(\s*(?:#|$))"
    content = re.sub(pattern, rf"\g<1>{value_str}\g<3>", content, flags=re.MULTILINE)

    views_path.write_text(content)


def _modify_api_run_method(
    app_name: str, api_name: str, run_code: str, base_path: Path = None
):
    """
    Replace the run() method implementation.

    Args:
        app_name: Name of the app
        api_name: Name of the API (snake_case)
        run_code: New implementation code for the run method
        base_path: Base path for the app (defaults to apps directory)
    """
    base_path = base_path or Path("apps")
    views_path = base_path / app_name / "views.py"
    content = views_path.read_text()

    pattern = (
        r"(def run\(self, request, \*args, \*\*kwargs\):)"
        r"([\s\S]*?)"
        r"(?=\n {4}def |\nclass |\Z)"
    )
    new_run = f"\\1\n{run_code}\n"
    content = re.sub(pattern, new_run, content, flags=re.DOTALL)

    views_path.write_text(content)
