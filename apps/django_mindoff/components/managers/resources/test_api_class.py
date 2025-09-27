import pytest
from .. import views
from django_mindoff.components.tdd_kit import MindoffTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


@pytest.mark.django_db
class TestSampleAPIView(MindoffTestCase):
    api_name = "app_name__api_name"

    def test_request_valid(self):
        response = self.mo_test_api(
            self.api_name,
            user=self._create_user(),
            method="get",
            headers=None,
            payload=None,
            url_kwargs=None,
            query_params=None,
            expected_status_code=200,
        )
        # Assert your response here
        assert response is not None

    def _create_user(self, username="testuser", password="password123"):
        user_model = get_user_model()
        user = user_model.objects.create_user(username=username, password=password)
        return user
