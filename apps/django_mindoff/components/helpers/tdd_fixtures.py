# ==========================================================
# 1. IMPORTS
#     - Standard Library
#     - Third-Party
#     - Local Modules
# ==========================================================

# ==========================================================
# 2. CONSTANTS
# ==========================================================


import pytest
import uuid
import sys
import tempfile
import shutil
import pytest
from pathlib import Path
from typing import List, Tuple
from collections import namedtuple
from django.apps import apps, AppConfig
from django.db import models, connection
from django.test import SimpleTestCase, override_settings
from django.conf import settings
from django_mindoff.components.helpers.string_conversion import pascal_to_snake
from django_mindoff.components.helpers.django_info import get_current_app_name

# ==== 2. Constants ====
PASCAL_CASE_REGEX = r"^[A-Z][a-zA-Z0-9]+$"
SNAKE_CASE_REGEX = r"^[a-z0-9_]+$"
test_case = SimpleTestCase()


# ==========================================================
# 3. CLASSES
#     3.1 Master Functions -- master_function_name
#     3.2 Butler Functions -- _butler_function_name
#     3.3 Helper Functions -- __helper_function_name
# ==========================================================
class LogicTestCase:
    @pytest.fixture(autouse=True)
    def run(self, request):
        self.asserts = request.getfixturevalue("_asserts")
        self.init_temp_app = request.getfixturevalue("_init_temp_app")
        self.init_temp_model = request.getfixturevalue("_init_temp_model")
        self.init_temp_dir = request.getfixturevalue("_init_temp_dir")

    @pytest.fixture(scope="session")
    def _asserts(self):
        return SimpleTestCase()

    @pytest.fixture
    def _init_temp_app(self, request):
        """Temporary Django App Creation Fixure."""
        CreatedApp = namedtuple("CreatedApp", ["app_name", "temp_dir", "override"])
        created_apps = []

        def __setup(app_name: str = None):
            app_name = _validate_or_generate_app_name(created_apps, app_name)
            app_name = app_name.lower().replace(" ", "_")
            temp_dir = Path(tempfile.mkdtemp())
            if "." in app_name:
                parts = app_name.split(".")
                app_path = temp_dir.joinpath(*parts)
            else:
                app_path = temp_dir / app_name
            app_path.mkdir(parents=True, exist_ok=True)
            (app_path / "__init__.py").write_text("")
            (app_path / "models.py").write_text("from django.db import models\n")
            sys.path.insert(0, str(temp_dir))
            new_installed = list(settings.INSTALLED_APPS) + [app_name]
            override = override_settings(INSTALLED_APPS=new_installed)
            override.enable()
            apps.set_installed_apps(new_installed)
            created_apps.append(CreatedApp(app_name, temp_dir, override))
            return app_name

        def __teardown():
            while created_apps:
                app_name, temp_dir, override = created_apps.pop()
                apps.app_configs.pop(app_name, None)
                apps.clear_cache()
                sys.path[:] = [p for p in sys.path if p != str(temp_dir)]
                sys_modules = list(sys.modules.keys())
                for mod in sys_modules:
                    if mod == app_name or mod.startswith(f"{app_name}."):
                        sys.modules.pop(mod, None)
                shutil.rmtree(temp_dir, ignore_errors=True)
                override.disable()
            apps.clear_cache()
            apps.populate(settings.INSTALLED_APPS)

        request.addfinalizer(__teardown)
        return __setup

    @pytest.fixture
    def _init_temp_model(self, request):
        """Temporary Django Model Creation Fixure."""
        # ---- Setup ----
        created_models = []

        def __setup(
            model_name: str = None,
            *,
            app_name: str = None,
            table_name: str = None,
            foreign_keys: List[Tuple[str, str]] = [],
            fields: dict = {},
            base_model=models.Model,
        ):
            _validate_inittempmodel_parameters(model_name, table_name, foreign_keys)
            if app_name:
                app_name = _validate_or_generate_app_name(
                    app_name=app_name, is_exists=True
                )
            else:
                app_name = get_current_app_name()
            model_name = _validate_or_generate_model_name(created_models, model_name)
            if not table_name:
                table_name = pascal_to_snake(model_name.lower().removesuffix("model"))
            model_class = _create_model(
                app_name, model_name, table_name, foreign_keys, fields, base_model
            )
            with connection.schema_editor() as editor:
                table = model_class._meta.db_table
                if table in connection.introspection.table_names():
                    editor.delete_model(model_class)
                editor.create_model(model_class)
            created_models.append(model_class)
            _validate_model(model_class)
            return model_class

        def __teardown():
            if not created_models:
                return
            with connection.schema_editor() as editor:
                for model in created_models:
                    editor.delete_model(model)

        request.addfinalizer(__teardown)
        return __setup

    @pytest.fixture
    def _init_temp_dir(self, request, tmp_path):
        original_base_dir = settings.BASE_DIR

        def __setup(addon_path=""):
            # Create UUID folder without hyphens
            temp_base_dir = tmp_path / uuid.uuid4().hex
            temp_base_dir.mkdir()

            # Create all directories in the relative path
            nested_dir = temp_base_dir / Path(addon_path)
            nested_dir.mkdir(parents=True, exist_ok=True)

            # Patch settings.BASE_DIR
            settings.BASE_DIR = temp_base_dir

            return nested_dir

        def __teardown():
            # Restore original BASE_DIR
            settings.BASE_DIR = original_base_dir

        request.addfinalizer(__teardown)
        return __setup


# ==========================================================
# 4. MAIN FUNCTIONS
# ==========================================================
# Add Main Functions Below


# ==========================================================
# 5. HELPER FUNCTIONS
# ==========================================================
# Add Helper Functions Below
def _create_model(
    app_name: str,
    model_name: str,
    table_name: str,
    foreign_keys: list,
    fields: dict,
    base_model=models.Model,
):
    model_fields = {
        "id": models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False,
            db_column=f"{table_name}_id",
        ),
        "__module__": __name__,
    }
    for main_app_name, main_model_name in foreign_keys:
        fk_name = main_model_name.lower().removesuffix("model")
        # Look up the actual model class from registry
        try:
            main_model_class = apps.get_model(main_app_name, main_model_name)
        except LookupError:
            raise LookupError(
                f"Foreign key target {main_app_name}.{main_model_name} not found in app registry"
            )

        model_fields[fk_name] = models.ForeignKey(
            main_model_class, on_delete=models.CASCADE, db_column=f"{fk_name}_id"
        )
    model_fields.update(fields)

    class Meta:
        app_label = app_name
        db_table = f"tbl_{table_name}"

    model_fields["Meta"] = Meta

    def __str__(self):
        return str(self.id)

    model_fields["__str__"] = __str__
    return type(model_name, (base_model,), model_fields)


def _validate_or_generate_app_name(
    created_apps: list = [], app_name: str = None, is_exists: bool = False
):
    existing_apps = set(apps.app_configs.keys()) | set(created_apps)
    if not app_name:
        base_name = "test_app"
        counter = 1
        while base_name in existing_apps:
            base_name = f"test_app_{counter}"
            counter += 1
        app_name = base_name
    if not is_exists and app_name in existing_apps:
        raise ValueError(f"App name '{app_name}' already exists.")
    elif is_exists and app_name not in existing_apps:
        raise ValueError(f"App name '{app_name}' does not exist.")
    return app_name


def _validate_or_generate_model_name(created_models: list = [], model_name: str = None):
    existing_model_names = {m.__name__ for m in created_models}
    if not model_name:
        base_name = "TestModel"
        counter = 1
        while base_name in existing_model_names:
            base_name = f"Test{counter}Model"
            counter += 1
        model_name = base_name
    else:
        if model_name in existing_model_names:
            raise ValueError(f"Model name '{model_name}' already exists.")
    return model_name


def _validate_inittempmodel_parameters(model_name, table_name, foreign_keys):
    if model_name:
        test_case.assertRegex(model_name, PASCAL_CASE_REGEX, msg="Invalid Model Name")
        test_case.assertTrue(
            model_name.endswith("Model"),
            msg=f"Model name '{model_name}' must end with 'Model'",
        )
    if table_name:
        test_case.assertRegex(table_name, SNAKE_CASE_REGEX)
    for _, model_name in foreign_keys or []:
        if model_name:
            test_case.assertRegex(model_name, PASCAL_CASE_REGEX)


def _validate_model(model_class):
    test_case.assertTrue(hasattr(model_class, "_meta"))
    test_case.assertTrue(model_class._meta.db_table)

    # Check model fields exist and have proper types
    fields = {f.name: f for f in model_class._meta.get_fields()}
    test_case.assertIn("id", fields)
    for field in fields.values():
        if field.is_relation and field.many_to_one:
            test_case.assertIsNotNone(field.related_model)
            test_case.assertTrue(field.column)
    try:
        qs = model_class.objects.all()
        list(qs)
    except Exception as e:
        test_case.fail(f"Querying model failed: {e}")


# ==========================================================
# 6. SCRIPT ENTRYPOINT
# ==========================================================
