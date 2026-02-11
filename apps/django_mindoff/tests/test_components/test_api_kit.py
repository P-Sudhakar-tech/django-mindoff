import json
import re
import logging
from pathlib import Path
from unittest.mock import patch
from rest_framework.test import APIClient
from django.urls import reverse, clear_url_caches, get_resolver
from rest_framework import status
from django.contrib.auth import get_user_model
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


# ========================================================================================
# ✅ ACCEPTANCE TESTS
# ========================================================================================
@pytest.mark.django_db(transaction=True)
class TestAPIAcceptance(MindoffTestCase):
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
        """ACCEPTANCE_3: API succeeds with allowed HTTP methods (get, post, put, delete)"""
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
        """ACCEPTANCE_4: API succeeds with valid payload_validation modes (strict, basic, None)"""
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
        """ACCEPTANCE_5: API succeeds for authenticated users when authentication is enabled"""
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
        """ACCEPTANCE_6: API succeeds for unauthenticated users when authentication is disabled"""
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


# ========================================================================================
# ❌ REJECTION TESTS
# ========================================================================================
@pytest.mark.django_db(transaction=True)
class TestAPIRejection(MindoffTestCase):
    @pytest.fixture(autouse=True)
    def setup(self):
        self.user = User.objects.create_user(username="testuser", password="pass123")

    def test_rejection_exception_from_run_method_with_debug_false(
        self, settings, caplog
    ):
        """REJECTION_2: Exception from run() is captured and logged when DEBUG=False"""
        settings.DEBUG = False

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
        assert any("ValueError" in rec.message for rec in caplog.records)

    def test_rejection_exception_from_run_method_with_debug_true(self, settings):
        """REJECTION_4: Exception from run() is returned with details when DEBUG=True"""
        settings.DEBUG = True
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_exception_debug_api", base_path=temp_dir_path
        )
        run_code = """        raise ValueError("Debug run exception")"""
        _modify_api_run_method(
            app_name, "test_exception_debug_api", run_code, base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.status_code == 500
        assert response.data["message"]["code"] == "UNEXPECTED_ERR"
        assert "ValueError" in response.data["message"]["description"]

    @pytest.mark.parametrize(
        "invalid_method", ["patch", "options", "head", "connect", "trace"]
    )
    def test_rejection_invalid_http_method(self, invalid_method, settings):
        """REJECTION_5: Invalid HTTP method not in ALLOWED_METHODS is rejected"""
        settings.DEBUG = True
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name,
            api_name=f"test_invalid_method_api_{invalid_method}",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            f"test_invalid_method_api_{invalid_method}",
            "method",
            invalid_method,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert (
            response.status_code == 500
            and response.data["message"]["code"] == "API_CONFIG_ERR"
        )
        assert "LookupError" in response.data["message"]["description"]

    @pytest.mark.parametrize("invalid_mode", ["async", "background", "invalid_mode"])
    def test_rejection_invalid_process_mode(self, invalid_mode, settings):
        """REJECTION_6: Invalid process_mode not in ALLOWED_PROCESS_MODES is rejected"""
        settings.DEBUG = True
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_mode_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_mode_api",
            "process_mode",
            invalid_mode,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert (
            response.status_code == 500
            and response.data["message"]["code"] == "API_CONFIG_ERR"
        )
        assert "LookupError" in response.data["message"]["description"]

    @pytest.mark.parametrize(
        "configured,actual", [("get", "post"), ("post", "get"), ("put", "delete")]
    )
    def test_rejection_request_method_mismatch(self, configured, actual):
        """REJECTION_7: Request method must match the configured method"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_mismatch_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, "test_mismatch_api", "method", configured, base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = getattr(self.client, actual)(url)
        assert (
            response.status_code == 400
            and response.data["message"]["code"] == "INVALID_METHOD"
        )
        assert "not allowed" in response.data["data"]["message"]

    def test_rejection_unauthenticated_user_with_auth_required(self):
        """REJECTION_8: Unauthenticated users are rejected when authentication is enabled"""
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
        assert response.status_code in [401]

    @patch("apps.django_mindoff.components.api_kit.is_ratelimited")
    def test_rejection_api_request_limit_exceeded(self, mock_limit):
        """REJECTION_9: API request exceeding api_request_limit is rejected"""
        cache.clear()
        mock_limit.return_value = True
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_rate_limit_api", base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.data["message"]["code"] == "API_RATE_LIMITED"
        assert "Service Limit Reached" in response.data["message"]["title"]

    def test_rejection_invalid_api_request_limit_format(self):
        """REJECTION_10: Invalid api_request_limit format string is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_limit_format_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_limit_format_api",
            "api_request_limit",
            "20/minutedfds",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_rejection_payload_size_exceeded(self):
        """REJECTION_11: Payload exceeding max_payload_size is rejected"""
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

    def test_rejection_payload_validation_strict_missing_field(self):
        """REJECTION_13: Payload with missing required fields fails in strict mode"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_strict_missing_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_strict_missing_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_strict_missing_api",
            "payload_schema",
            '{"name": str, "age": int}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_strict_missing_api",
            "payload_validation",
            "strict",
            base_path=temp_dir_path,
        )

        url = reverse(api_url_name)
        response = self.client.post(url, {"name": "John"}, format="json")
        assert response.data["message"]["code"] == "INVALID_PAYLOAD"

    def test_rejection_payload_validation_strict_wrong_type(self):
        """REJECTION_13: Payload with wrong type fails in strict mode"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_strict_type_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, "test_strict_type_api", "method", "post", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_strict_type_api",
            "payload_schema",
            '{"name": str, "age": int}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_strict_type_api",
            "payload_validation",
            "strict",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.post(
            url, {"name": "John", "age": "thirty"}, format="json"
        )
        assert response.data["message"]["code"] == "INVALID_PAYLOAD"

    def test_rejection_payload_depth_exceeded(self):
        """REJECTION_14: Payload exceeding max_payload_depth is rejected"""
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


# ========================================================================================
# 🎯 BOUNDARY TESTS - API behavior at boundary conditions
# ========================================================================================


@pytest.mark.django_db(transaction=True)
class TestAPIBoundary(MindoffTestCase):
    @patch("apps.django_mindoff.components.api_kit.is_ratelimited")
    def test_boundary_api_request_at_exact_limit(self, mock_limit):
        """BOUNDARY_1: API succeeds when request count equals api_request_limit"""
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
        """BOUNDARY_2: API succeeds when payload size equals max_payload_size"""
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
        """BOUNDARY_4: API succeeds with mismatched payload when validation mode is None"""
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

    @pytest.mark.parametrize("mode", ["basic", "strict"])
    @pytest.mark.parametrize(
        ("schema", "payload"),
        [("{}", {"any_key": "any_value"}), ("[]", [{"key": "value"}])],
    )
    def test_boundary_empty_schema_with_valid_payload(self, mode, schema, payload):
        """BOUNDARY_5: API succeeds with empty schema {} and non-empty payload in basic mode"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_empty_schema_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_empty_schema_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_empty_schema_dict_api",
            "payload_schema",
            schema,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_empty_schema_dict_api",
            "payload_validation",
            mode,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.post(url, payload, format="json")
        assert response.data["message"]["code"] == "SUCCESS"

    @pytest.mark.parametrize("mode", ["basic", "strict"])
    @pytest.mark.parametrize("payload", ["", False])
    def test_boundary_schema_none_with_payload_falsey(self, mode, payload):
        """BOUNDARY_5: API succeeds with empty schema {} and non-empty payload in basic mode"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_empty_schema_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_empty_schema_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_empty_schema_dict_api",
            "payload_schema",
            None,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_empty_schema_dict_api",
            "payload_validation",
            mode,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.post(url, payload, format="json")
        assert response.data["message"]["code"] == "SUCCESS"

    def test_boundary_payload_depth_exact(self):
        """REJECTION_14: Payload exceeding max_payload_depth is rejected"""
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
            3,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        payload = {"level1": {"level2": {"level3": "value"}}}
        response = self.client.post(url, payload, format="json")
        assert response.data["message"]["code"] == "SUCCESS"


# ========================================================================================
# 🔍 ANOMALY TESTS
# ========================================================================================
@pytest.mark.django_db(transaction=True)
class TestAPIAnomaly(MindoffTestCase):
    def test_anomaly_empty_api_url_name(self, settings, caplog):
        """ANOMALY_1: Empty api_url_name is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_empty_url_name_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_empty_url_name_api",
            "api_url_name",
            "",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_invalid_api_url_name_not_in_urls(self, settings, caplog):
        """ANOMALY_2: api_url_name not matching any URL in urls.py is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_url_name_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_url_name_api",
            "api_url_name",
            "non_existent_url_name",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_empty_api_name(self, settings, caplog):
        """ANOMALY_4: Empty api_name is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_empty_api_name", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name, "test_empty_api_name", "api_name", "", base_path=temp_dir_path
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_success_empty_api_description(self):
        """ANOMALY_5: Empty api_description is allowed and API succeeds"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_empty_desc_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_empty_desc_api",
            "api_description",
            "",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        response = self.client.get(url)
        assert response.data["message"]["code"] == "SUCCESS"

    def test_anomaly_none_api_description(self, settings, caplog):
        """ANOMALY_6: None api_description is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_none_desc_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_none_desc_api",
            "api_description",
            None,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_non_boolean_allow_duplicate_queue(self, settings, caplog):
        """ANOMALY_7: Non-boolean allow_duplicate_queue is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_dup_queue_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_dup_queue_api",
            "allow_duplicate_queue",
            "true",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_invalid_payload_schema_type(self, settings, caplog):
        """ANOMALY_8: Invalid payload_schema type (not list/dict/None) is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_schema_type_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_schema_type_api",
            "payload_schema",
            "invalid_string_schema",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_invalid_max_payload_size_type(self, settings, caplog):
        """ANOMALY_9: Non int/float/None max_payload_size is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_size_type_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_size_type_api",
            "max_payload_size",
            "not_a_number",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_invalid_max_payload_depth_type(self, settings, caplog):
        """ANOMALY_10: Non int/float/None max_payload_depth is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_depth_type_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_depth_type_api",
            "max_payload_depth",
            "not_a_number",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_invalid_payload_validation_type(self, settings, caplog):
        """ANOMALY_11: Invalid payload_validation type is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
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
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_invalid_response_type(self, settings, caplog):
        """ANOMALY_12: Invalid response_type not in allowed types is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_response_type_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_response_type_api",
            "response_type",
            "invalid_type",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_non_boolean_response_validation(self, settings, caplog):
        """ANOMALY_13: Non-boolean response_validation is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name,
            api_name="test_invalid_resp_validation_api",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_resp_validation_api",
            "response_validation",
            "true",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_invalid_api_request_limit_type(self, settings, caplog):
        """ANOMALY_14: Non-string/None api_request_limit is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_limit_type_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_limit_type_api",
            "api_request_limit",
            123,
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_invalid_queue_streaming_limit_type(self, settings, caplog):
        """ANOMALY_15: Non-int/None queue_status_streaming_limit is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_invalid_stream_limit_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_invalid_stream_limit_api",
            "queue_status_streaming_limit",
            "three",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.get(url)
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_negative_max_payload_size(self, settings, caplog):
        """ANOMALY_16: Negative max_payload_size is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_negative_size_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_negative_size_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_negative_size_api",
            "max_payload_size",
            -5,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_negative_size_api",
            "payload_schema",
            '{"data": str}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_negative_size_api",
            "payload_validation",
            "basic",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.post(url, {"data": "test"}, format="json")
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_zero_max_payload_size(self, settings, caplog):
        """ANOMALY_17: Zero max_payload_size is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_zero_size_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_zero_size_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_zero_size_api",
            "max_payload_size",
            0,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_zero_size_api",
            "payload_schema",
            '{"data": str}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_zero_size_api",
            "payload_validation",
            "basic",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        with caplog.at_level(logging.ERROR):
            response = self.client.post(url, {"data": "test"}, format="json")
        assert response.data["message"]["code"] == "API_CONFIG_ERR"

    def test_anomaly_zero_max_payload_depth(self, settings, caplog):
        """ANOMALY_18: Zero max_payload_depth is rejected"""
        app_name, temp_dir_path = self.mo_mock_app(is_return_path=True)
        api_url_name = _create_test_api(
            app_name, api_name="test_zero_depth_api", base_path=temp_dir_path
        )
        _modify_api_attribute(
            app_name,
            "test_zero_depth_api",
            "method",
            "post",
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_zero_depth_api",
            "max_payload_depth",
            0,
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_zero_depth_api",
            "payload_schema",
            '{"level1": {"level2": str}}',
            base_path=temp_dir_path,
        )
        _modify_api_attribute(
            app_name,
            "test_zero_depth_api",
            "payload_validation",
            "strict",
            base_path=temp_dir_path,
        )
        url = reverse(api_url_name)
        payload = {"level1": {"level2": "value"}}
        with caplog.at_level(logging.ERROR):
            response = self.client.post(url, payload, format="json")
        assert response.data["message"]["code"] == "API_CONFIG_ERR"


# ========================================================================================
# 🔧 HELPER FUNCTIONS
# ========================================================================================


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
            new_content = re.sub(r"\bdjango_mindoff\b", "apps.django_mindoff", content)
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

    pattern = r"(def run\(self, request, \*args, \*\*kwargs\):)(.*?)(?=\n    def |\nclass |\Z)"
    new_run = f"\\1\n{run_code}\n"
    content = re.sub(pattern, new_run, content, flags=re.DOTALL)

    views_path.write_text(content)
