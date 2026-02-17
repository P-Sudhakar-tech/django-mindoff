import pytest
from django_mindoff.components.tdd_kit import MindoffTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


@pytest.mark.django_db
class TestSampleAPIView(MindoffTestCase):
    api_url_name = "{{API_URL_NAME}}"

    def test_api_works(self):
        # 1. Call API
        response = self.mo_test_api(
            api_url_name=self.api_url_name,
            user=self._create_user(),
            headers=None,
            custom_method=None,
            custom_payload=None,
            custom_url_kwargs=None,
            custom_query_params=None,
        )
        # 2. Assert response
        self.mo_assert_api_response(
            api_url_name=self.api_url_name,
            response=response,
            custom_response_type=None,  # options: json | plain | html | xml | binary
            expected_status_code=200,  # options: 200 | 400
        )
        # -- Add additional assertions here --

    def _create_user(self, username="testuser", password="password123"):
        user_model = get_user_model()
        user = user_model.objects.create_user(username=username, password=password)
        return user
