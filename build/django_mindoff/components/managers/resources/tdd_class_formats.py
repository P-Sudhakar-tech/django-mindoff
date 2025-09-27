import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


# =================================================================
# 1. MODEL TESTS - Standard Input → Model Client → Output Assertion
# =================================================================
@pytest.mark.django_db
class TestModel:
    def test_create_and_retrieve(self, my_model_factory):
        """Create a model instance and verify persistence."""
        instance = my_model_factory(name="Test Name", value=42)

        # Query back
        result = type(instance).objects.get(pk=instance.pk)

        assert result.name == "Test Name"
        assert result.value == 42
        assert result.pk is not None

    def test_validation_errors(self, my_model_class):
        """Invalid input should raise ValidationError."""
        from django.core.exceptions import ValidationError

        obj = my_model_class(name="", value=-1)
        with pytest.raises(ValidationError):
            obj.full_clean()


# =================================================================
# 2. API TESTS - Standard Input → API Client → Output Assertion
# =================================================================
@pytest.mark.django_db
class TestAPI:
    def test_list_endpoint(self, api_client):
        """Verify list API returns data in expected format."""
        response = api_client.get("/api/items/")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_create_endpoint(self, api_client):
        """Verify creation API works with valid payload."""
        payload = {"name": "Item A", "value": 10}
        response = api_client.post("/api/items/", payload, format="json")

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Item A"
        assert data["value"] == 10


# =================================================================
# 3. COMMAND TESTS → Standard Input → Command Client → Output Assertion → Cleanup
# =================================================================
@pytest.mark.django_db
class TestCommands:
    def test_custom_command_runs(self):
        """Custom command should run without errors."""
        call_command("my_custom_command", "--dry-run")

    def test_command_with_invalid_args(self):
        """Command should error on bad input."""
        with pytest.raises(CommandError):
            call_command("my_custom_command", "--bad-arg")


# =================================================================
# 4. LOGIC TESTS - Custom Input → Custom Process → Output Assertion
# =================================================================
class TestLogicFeatureName:
    """
    ClassName Format - TestLogic{FeatureName}
    """

    def test_logic_valid(self, sample_input):
        """Pure function logic test - valid case."""
        from myapp.utils import process_data

        output = process_data(sample_input)
        assert output["status"] == "success"
        assert output["count"] > 0

    def test_logic_invalid(self):
        """Pure function logic test - invalid case."""
        from myapp.utils import process_data

        with pytest.raises(ValueError):
            process_data(None)
