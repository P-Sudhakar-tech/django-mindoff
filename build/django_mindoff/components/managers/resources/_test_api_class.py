import pytest
from django_mindoff.components.tdd_kit import MindoffTestCase
from typing import Literal


@pytest.mark.django_db
class TestSampleAPIView(MindoffTestCase):
    api_url_name = "{{API_URL_NAME}}"

    def test_acceptance_api_success(self):
        user = self.mo_create_user()
        custom_payload: dict | list | None = None
        url_kwargs: dict | None = None
        query_params: dict | None = None
        headers: dict | None = None
        list_dict_count: int = 1
        expected_status_code: int = 200
        custom_response_type: Literal[
            "json", "plain", "html", "binary", "others", None
        ] = None

        response = self.mo_test_api(
            self.api_url_name,
            user=user,
            custom_payload=custom_payload,
            url_kwargs=url_kwargs,
            custom_query_params=query_params,
            headers=headers,
            list_dict_count=list_dict_count,
        )
        self.mo_assert_api_response(
            api_url_name=self.api_url_name,
            response=response,
            expected_status_code=expected_status_code,
            custom_response_type=custom_response_type,
        )
        # result = response.json()
        # assert result["data"] == []
