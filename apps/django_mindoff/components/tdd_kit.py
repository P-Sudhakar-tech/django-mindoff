# ==========================================================
# 1. IMPORTS
#     - Standard Library
#     - Third-Party
#     - Local Modules
# ==========================================================
import pytest
import uuid
import sys
import tempfile
import shutil
import pytest
import random
import string
import datetime
from decimal import Decimal
from pathlib import Path
from typing import List, Tuple, Type, Optional
import polars as pl
from model_bakery import baker
from itertools import product
from collections import namedtuple
from typeguard import typechecked
from django.apps import apps, AppConfig
from django.db import models, connection
from django.test import SimpleTestCase, override_settings
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django_mindoff.components.helper_kit import mo_helper_kit
from django_mindoff.components.validation_kit import mo_validation_kit
from ._tdd_kit import field_value_generator

# ==========================================================
# 2. CONSTANTS
# ==========================================================
PASCAL_CASE_REGEX = r"^[A-Z][a-zA-Z0-9]+$"
SNAKE_CASE_REGEX = r"^[a-z0-9_]+$"
test_case = SimpleTestCase()


# ==========================================================
# 3. CLASSES
#     3.1 Master Functions -- master_function_name
#     3.2 Butler Functions -- _butler_function_name
#     3.3 Helper Functions -- __helper_function_name
# ==========================================================
class MindoffTestCase:
    @pytest.fixture(autouse=True)
    def run(self, request):
        self.asserts = request.getfixturevalue("_asserts")
        self.mo_mock_app = request.getfixturevalue("_mo_mock_app")
        self.mo_mock_model = request.getfixturevalue("_mo_mock_model")
        self.init_temp_dir = request.getfixturevalue("_init_temp_dir")
        self.mo_mock_model_dfs = request.getfixturevalue("_mo_mock_model_dfs")
        if hasattr(mo_validation_kit, "reset"):
            mo_validation_kit.reset()

    @pytest.fixture(scope="session")
    def _asserts(self):
        return SimpleTestCase()

    @pytest.fixture
    def _mo_mock_app(self, request):
        """Temporary Django App Creation Fixure."""
        CreatedApp = namedtuple("CreatedApp", ["app_name", "temp_dir", "override"])
        created_apps = []

        @typechecked
        def __setup(app_name: str | None = None):
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
    def _mo_mock_model(self, request):
        """Temporary Django Model Creation Fixure."""
        # ---- Setup ----
        created_models = []

        @typechecked
        def __setup(
            model_name: str | None = None,
            *,
            app_name: str | None = None,
            table_name: str | None = None,
            foreign_keys: List[Tuple[str, str] | Tuple[str, str, str]] = [],
            fields: dict = {},
            base_model=models.Model,
        ):
            status, foreign_keys = _normalize_fk_and_validate_mockmodel_params(
                model_name, table_name, foreign_keys
            )
            mo_validation_kit.ensure_truthy(status)
            if app_name:
                app_name = _validate_or_generate_app_name(
                    app_name=app_name, is_exists=True
                )
            else:
                app_name = mo_helper_kit.get_current_app_name()
            model_name = _validate_or_generate_model_name(created_models, model_name)
            if not table_name:
                table_name = mo_helper_kit.pascal_to_snake(
                    model_name.lower().removesuffix("model")
                )
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

    @pytest.fixture
    def _mo_mock_model_dfs(self, request):
        @typechecked
        def __bake_model_df_dict(
            models: List[Type],
            *,
            counts: List[int] = [],
            exclude_columns: List[List[str]] = [],
            modify: List[dict] = [],
            is_fk_as_id: bool = True,
            is_enforce_db_column: bool = True,
            is_uuid_hex: bool = True,
        ) -> dict[Type, pl.DataFrame]:
            counts = counts or [1] * len(models)
            exclude_columns = exclude_columns or []
            modify = modify or []
            df_dict = {}
            baked_objects_per_model = []
            for idx, model in enumerate(models):
                objs = _generate_model_factory_objects(
                    idx, model, models, baked_objects_per_model, counts, is_uuid_hex
                )
                baked_objects_per_model.append(objs)
                df = pl.DataFrame(
                    [_obj_to_dict(obj, is_fk_as_id=is_fk_as_id) for obj in objs]
                )
                if is_enforce_db_column:
                    field_map = {
                        f.name: (f.db_column or f.get_attname_column()[1])
                        for f in model._meta.concrete_fields
                        if hasattr(f, "attname")
                    }
                    df = df.rename({col: field_map.get(col, col) for col in df.columns})
                df = _apply_exclude_columns(idx, df, exclude_columns)
                df = _apply_modify(idx, df, modify)
                df_dict[model] = df
            return df_dict

        return __bake_model_df_dict


# ==========================================================
# 4. MAIN FUNCTIONS
# ==========================================================
# Add Main Functions Below


# ==========================================================
# 5. HELPER FUNCTIONS
# ==========================================================
# Add Helper Functions Below


def _normalize_fk_and_validate_mockmodel_params(model_name, table_name, foreign_keys):
    if model_name:
        test_case.assertRegex(model_name, PASCAL_CASE_REGEX, msg="Invalid Model Name")
        test_case.assertTrue(
            model_name.endswith("Model"),
            msg=f"Model name '{model_name}' must end with 'Model'",
        )
    if table_name:
        test_case.assertRegex(table_name, SNAKE_CASE_REGEX)
    for idx, fk in enumerate(foreign_keys):
        fk_list = list(fk)
        model_name = fk_list[1]
        if model_name:
            test_case.assertRegex(model_name, PASCAL_CASE_REGEX)
        if len(fk_list) == 2:
            fk_list.append("required")
        elif len(fk_list) == 3:
            option = fk_list[2]
            mo_validation_kit.ensure_in(option, ["required", "optional"])
        foreign_keys[idx] = tuple(fk_list)
    return True, foreign_keys


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
    for main_app_name, main_model_name, option in foreign_keys:
        fk_name = main_model_name.lower().removesuffix("model")
        try:
            main_model_class = apps.get_model(main_app_name, main_model_name)
        except LookupError:
            raise LookupError(
                f"Foreign key target {main_app_name}.{main_model_name} not found in app registry"
            )
        if option == "optional":
            model_fields[fk_name] = models.ForeignKey(
                main_model_class,
                on_delete=models.CASCADE,
                db_column=f"{fk_name}_id",
                null=True,
                blank=True,
            )
        else:
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
    created_apps: list = [], app_name: str | None = None, is_exists: bool = False
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


def _validate_or_generate_model_name(
    created_models: list = [], model_name: str | None = None
):
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


def _validate_model(model_class):
    test_case.assertTrue(hasattr(model_class, "_meta"))
    test_case.assertTrue(model_class._meta.db_table)

    # Check model fields exist and have proper types
    fields = {f.name: f for f in model_class._meta.concrete_fields}
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


def _obj_to_dict(obj, is_fk_as_id):
    """Convert a Django model instance to dict, optionally replacing FK fields with PKs."""
    result = {}
    for field in obj._meta.fields:
        val = getattr(obj, field.name)
        if is_fk_as_id and hasattr(field, "related_model") and val is not None:
            if hasattr(val, "pk"):
                val = val.pk
        result[field.name] = val
    return result


def _generate_model_factory_objects(
    idx, model, models, baked_objects_per_model, counts, is_uuid_hex
):
    n_per_parent = counts[idx]

    # Map FK fields to previously baked models
    fk_fields_map = {
        f.name: baked_objects_per_model[i]
        for i, m in enumerate(models[:idx])
        for f in model._meta.fields
        if getattr(f, "related_model", None) is m
    }

    objs = []

    if not fk_fields_map:  # top-level
        baked = _prepare_with_constraints(model, is_uuid_hex, quantity=n_per_parent)
        return baked if isinstance(baked, list) else [baked]

    immediate_parent_name, immediate_parent_objs = list(fk_fields_map.items())[-1]

    # replicate per immediate parent
    for parent_obj in immediate_parent_objs:
        fk_kwargs = {immediate_parent_name: parent_obj}

        # assign other FKs from parent_obj if available
        for fk_name, fk_list in fk_fields_map.items():
            if fk_name == immediate_parent_name:
                continue
            if hasattr(parent_obj, fk_name):
                fk_kwargs[fk_name] = getattr(parent_obj, fk_name)
            else:
                # fallback: pick first object from list
                fk_kwargs[fk_name] = fk_list[0]

        objs.extend(
            _prepare_with_constraints(
                model, is_uuid_hex, quantity=n_per_parent, **fk_kwargs
            )
        )

    return objs


def _prepare_with_constraints(model, is_uuid_hex, quantity=1, **fk_kwargs):
    objs = []
    used_uniques = {}

    for _ in range(quantity):
        kwargs = dict(fk_kwargs)

        for field in model._meta.fields:
            if field.name in kwargs:
                continue
            value = field_value_generator.generate_field_value(
                field, used_uniques, kwargs, is_uuid_hex
            )
            if value is not None:
                kwargs[field.name] = value

        objs.append(baker.prepare(model, **kwargs))

    return objs


def _apply_exclude_columns(idx, df, exclude_columns: List[List[str]]):
    cols = exclude_columns[idx] if idx < len(exclude_columns) else []
    if cols:
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise ValueError(
                f"Cannot exclude non-existing columns {missing} "
                f"at index {idx}. Available columns: {list(df.columns)}"
            )
        return df.drop(cols)

    return df


def _apply_modify(idx, df, modify: List[dict]):
    changes = modify[idx] if idx < len(modify) else {}
    for row_idx, updates in changes.items():
        if not (0 <= row_idx < df.height):
            raise IndexError(
                f"Row index {row_idx} out of range for DataFrame with {df.height} rows "
                f"(modify idx={idx})."
            )
        for col, val in updates.items():
            if col not in df.columns:
                raise ValueError(
                    f"Cannot modify non-existing column '{col}' at index {idx}. "
                    f"Available columns: {list(df.columns)}"
                )
            try:
                df = df.with_columns(
                    [
                        pl.when(pl.arange(0, df.height) == row_idx)
                        .then(pl.lit(val, allow_object=True))
                        .otherwise(pl.col(col))
                        .alias(col)
                    ]
                )
            except Exception as e:
                raise ValueError(
                    f"Failed to modify value in column '{col}' at row {row_idx}. "
                    f"Attempted value: {val!r}. Original error: {e}"
                )
    return df


# ==========================================================
# 6. SCRIPT ENTRYPOINT
# ==========================================================
