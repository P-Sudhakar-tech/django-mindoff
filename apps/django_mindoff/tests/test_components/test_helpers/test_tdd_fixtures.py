import pytest
from django_mindoff.components.helpers.tdd_fixtures import LogicTestCase
import re
from django.db import models
from django.apps import apps
from django.conf import settings

# ------------------------
# ⚓ CONSTANTS
# ------------------------
snake_case_regex = r"^[a-z0-9_]+$"
pascal_case_regex = r"^[A-Z][a-zA-Z0-9]+$"


class TestInitTempApp(LogicTestCase):
    # ------------------------
    # ✅ ACCEPTANCE TESTS
    # ------------------------
    def test_auto_app_creation_unique_names(self):
        """
        1. **Auto App Creation** — Creates an app with a system-generated name
        when none is given and can create multiple auto-generated apps sequentially
        without name collisions.
        """
        app1 = self.init_temp_app()
        app2 = self.init_temp_app()
        self.asserts.assertNotEqual(app1, app2)
        self._common_assertions(app1)
        self._common_assertions(app2)

    def test_defined_app_creation_and_mixed_environment(self):
        """
        2. **Defined App Creation** — Creates an app with a user-specified name
        and can create multiple defined apps without name collisions.
        """
        auto_app = self.init_temp_app()
        defined_app1 = self.init_temp_app(app_name="custom_app")
        defined_app2 = self.init_temp_app(app_name="customapp")
        self.asserts.assertIn("custom_app", apps.app_configs)
        self._common_assertions(auto_app)
        self._common_assertions(defined_app1)
        self._common_assertions(defined_app2)

    def _common_assertions(self, app_name):
        """
        3. **Common:**
        """
        # - Can import models from the new app without errors.
        models_module = __import__(f"{app_name}.models")
        self.asserts.assertTrue(hasattr(models_module, "models"))
        # - Generated name follows naming rules (`snake_case`, no special chars, no leading digits).
        self.asserts.assertRegex(app_name, snake_case_regex)
        self.asserts.assertTrue(app_name.islower())
        # - App appears in `apps.app_configs` with correct label.
        self.asserts.assertIn(app_name, apps.app_configs)

    # ------------------------
    # 🚫 REJECTION TESTS
    # ------------------------
    def test_invalid_app_name(self):
        """
        1. **Invalid App Name** — Names with special characters (`@`, `#`, ),
        starting with a digit., Reserved Python keywords (`class`, `import`).
        """
        bad_names = ["invalid@app", "123startdigit", "apps.app_name"]
        for name in bad_names:
            with self.asserts.assertRaises(Exception):
                self.init_temp_app(app_name=name)

    def test_app_name_collision(self):
        """
        2. **App Name Collision** — Creating an app with a name that already
        exists in `INSTALLED_APPS` and Creating an auto-generated app when the
        generated name already exists.
        """
        _ = self.init_temp_app(app_name="duplicate_app")
        with self.asserts.assertRaises(Exception):
            self.init_temp_app(app_name="duplicate_app")

    def test_invalid_app_path(self):
        """
        3. **Invalid App Path** — Attempt to create app outside of
        allowed namespace (e.g., `../../evil`).
        """
        with self.asserts.assertRaises(Exception):
            self.init_temp_app(app_name="apps/app_name/evil")

    def test_concurrent_creation_same_name(self):
        self.init_temp_app("temp_app_concurrent")
        with self.asserts.assertRaises(ValueError):
            self.init_temp_app("temp_app_concurrent")

    # ------------------------
    # 🚧 BOUNDARY TESTS
    # ------------------------
    def test_minimum_length_name(self):
        name = self.init_temp_app("a")
        self.asserts.assertIn(name, apps.app_configs)

    def test_maximum_length_name(self):
        name = "x" * 100
        created_name = self.init_temp_app(name)
        self.asserts.assertIn(created_name, apps.app_configs)

    def test_case_sensitivity_normalization(self):
        app1 = self.init_temp_app("MixedCaseApp")
        app2 = self.init_temp_app("Mixed Case app")
        app3 = self.init_temp_app("mixedCase App")
        self.asserts.assertEqual(app1, "mixedcaseapp")
        self.asserts.assertEqual(app2, "mixed_case_app")
        self.asserts.assertEqual(app3, "mixedcase_app")

    def test_auto_name_suffix_overflow(self):
        apps.app_configs["test_app"] = object()
        for i in range(1, 10000):
            apps.app_configs[f"test_app_{i}"] = object()
        name = self.init_temp_app()
        self.asserts.assertTrue(name.startswith("test_app_"))

    # ------------------------
    # 🌀 ANOMALY TESTS
    # ------------------------
    def test_empty_string_name_fallbacks_to_auto(self):
        name = self.init_temp_app("")
        self.asserts.assertTrue(name.startswith("test_app"))

    def test_exceeds_max_length_throws_error(self):
        with self.asserts.assertRaises(Exception):
            self.init_temp_app("x" * 1024)


@pytest.mark.django_db(transaction=True)
class TestInitTempModel(LogicTestCase):
    # ------------------------
    # ✅ ACCEPTANCE TESTS
    # ------------------------
    def test_auto_model_creation_unique_names(self):
        """
        1. Auto Model Creation: Create unique and matching pascalCase class name and
        snake_case table name with no parameter input and Works when called multiple times
        sequentially with unique model name generation
        """
        model1 = self.init_temp_model()
        model2 = self.init_temp_model()
        self.asserts.assertNotEqual(
            model1.__name__, model2.__name__, msg="Model Name duplication Found"
        )
        self.asserts.assertNotEqual(
            model1._meta.db_table,
            model2._meta.db_table,
            msg="Table Name Duplication Found",
        )
        self._common_assertions(model1)
        self._common_assertions(model2)

    def test_defined_and_auto_model_creation_together(self):
        """
        2. Auto Model Creation & Defined Model Creation Can exist for Same Test
        """
        defined_name_1 = "TestModel"
        defined_name_2 = "Test2Model"
        defined_model_1 = self.init_temp_model(model_name=defined_name_1)
        defined_model_2 = self.init_temp_model(model_name=defined_name_2)
        auto_model_1 = self.init_temp_model()
        auto_model_2 = self.init_temp_model()
        model_names_dict = {
            defined_model_1.__name__,
            defined_model_2.__name__,
            auto_model_1.__name__,
            auto_model_2.__name__,
        }
        table_names_dict = {
            defined_model_1._meta.db_table,
            defined_model_2._meta.db_table,
            auto_model_1._meta.db_table,
            auto_model_2._meta.db_table,
        }
        self.asserts.assertEqual(defined_model_1.__name__, defined_name_1)
        self.asserts.assertEqual(defined_model_2.__name__, defined_name_2)
        self.asserts.assertEqual(
            len(model_names_dict),
            4,
            msg=f"Duplicate model names found: \n{model_names_dict}",
        )

        self.asserts.assertEqual(
            len(table_names_dict),
            4,
            msg=f"Duplicate table names found: {table_names_dict}",
        )
        self._common_assertions(defined_model_1)
        self._common_assertions(defined_model_2)
        self._common_assertions(auto_model_1)
        self._common_assertions(auto_model_2)

    def test_foreign_key_addon(self):
        """
        3. **Foreign Key Addon:** Link Multiple Existing Model Names → Add multiple FK fields
        and db_columns Should match the db_columns of corresponding model’s primary key
        - Link one of the Foreign key to Other Auto Temporary Model from another app
        - Link one of the Foreign key to Other Defined Temporary Model from another app
        - Link one of the Foreign key to Other Permanent Model from same app
        - Link one of the Foreign key to Other Permanent Model from another app
        """
        self.init_temp_app(app_name="temp_otherapp")
        self.init_temp_app(app_name="another.temp_app")
        temp_other_auto = self.init_temp_model(app_name="temp_otherapp")
        temp_other_defined = self.init_temp_model(
            app_name="temp_app", model_name="DefinedOtherModel"
        )
        perm_same_app = apps.get_model("auth", "User")
        perm_other_app = apps.get_model("contenttypes", "ContentType")
        model = self.init_temp_model(
            foreign_keys=[
                (temp_other_auto._meta.app_label, temp_other_auto.__name__),
                (temp_other_defined._meta.app_label, temp_other_defined.__name__),
                (perm_same_app._meta.app_label, perm_same_app.__name__),
                (perm_other_app._meta.app_label, perm_other_app.__name__),
            ]
        )
        fk_fields = [
            f for f in model._meta.get_fields() if isinstance(f, models.ForeignKey)
        ]
        self.asserts.assertEqual(
            len(fk_fields), 4, msg="Not All Foreign key fields are created"
        )
        linked_models = {fk.related_model for fk in fk_fields}
        expected_models = {
            temp_other_auto,
            temp_other_defined,
            perm_same_app,
            perm_other_app,
        }
        self.asserts.assertEqual(
            linked_models, expected_models, msg="Foreign key model not matching"
        )
        temp_app_prefixes = "temp_"
        for fk in fk_fields:
            related_model = fk.related_model
            if related_model._meta.app_label.startswith(temp_app_prefixes):
                pk_field = related_model._meta.pk
                expected_db_column = pk_field.db_column or pk_field.attname
                actual_db_column = fk.db_column or fk.attname
                self.asserts.assertEqual(
                    actual_db_column,
                    expected_db_column,
                    msg=(
                        f"Mismatch in db_column for FK '{fk.name}': "
                        f"expected '{expected_db_column}', found '{actual_db_column}'."
                    ),
                )
        self._common_assertions(model)

    def test_fields_addon_single_and_multiple(self):
        fields = {
            "char_field": models.CharField(max_length=50, help_text="A short string"),
            "int_field": models.IntegerField(help_text="An integer field"),
            "char_field_parameters": models.CharField(
                max_length=100,
                null=True,
                blank=True,
                default="default text",
                unique=True,
                db_column="char_col",
            ),
            "int_field_parameters": models.IntegerField(
                null=True, blank=True, default=10, unique=True, db_column="int_column"
            ),
        }
        model = self.init_temp_model(fields=fields)
        attrs_to_check = [
            "max_length",
            "null",
            "blank",
            "default",
            "db_column",
            "unique",
            "editable",
            "primary_key",
            "help_text",
            "verbose_name",
            "choices",
            "max_digits",
            "decimal_places",
        ]
        for field_name, field_obj in fields.items():
            model_field = model._meta.get_field(field_name)
            self.asserts.assertIsInstance(model_field, type(field_obj))
            for attr in attrs_to_check:
                if hasattr(field_obj, attr):
                    expected = getattr(field_obj, attr)
                    actual = getattr(model_field, attr, None)
                    self.asserts.assertEqual(
                        actual,
                        expected,
                        msg=f"Field '{field_name}' attribute '{attr}' mismatch: expected {expected!r}, got {actual!r}",
                    )

        self._common_assertions(model)

    def _common_assertions(self, model):
        app_label = model._meta.app_label
        self.asserts.assertIsNotNone(app_label, msg="app_label should not be None")
        self.asserts.assertNotEqual(
            app_label, "", msg="app_label should not be an empty string"
        )
        self.asserts.assertRegex(
            model._meta.db_table,
            snake_case_regex,
            msg=f"Table name '{model._meta.db_table}' is not snake_case",
        )
        self.asserts.assertRegex(
            model.__name__,
            pascal_case_regex,
            msg="Model Name Not Pascal Case",
        )
        for field in model._meta.get_fields():
            if hasattr(field, "db_column") and field.db_column:
                self.asserts.assertRegex(
                    model._meta.db_table,
                    snake_case_regex,
                    msg=f"DB Column name '{field.db_column}' is not snake_case",
                )

    # ------------------------
    # 🚫 REJECTION TESTS
    # ------------------------
    def test_string_naming_errors(self):
        # 1. ModelName is not PascalCase
        with pytest.raises(AssertionError):
            self.init_temp_model(model_name="notPascalModel")
        # 2. TableName is not snake_case
        with pytest.raises(AssertionError):
            self.init_temp_model(table_name="NotSnakeCase")
        # 3. ModelName does not end with 'Model'
        with pytest.raises(AssertionError):
            self.init_temp_model(model_name="Test")
        # 4. ModelName contains invalid chars (e.g. starting with number, spaces, special chars)
        invalid_names = ["123Model", "My Model", "Model$", "Model!"]
        for name in invalid_names:
            with pytest.raises(AssertionError):
                self.init_temp_model(model_name=name)

    def test_existential_crisis_errors(self):
        # 1. App label does not exist
        with pytest.raises(ValueError):
            self.init_temp_model(app_name="nonexistentapp")
        # 2. Duplicate model name already registered
        self.init_temp_model(model_name="DuplicateModel")
        with pytest.raises(ValueError):
            self.init_temp_model(model_name="DuplicateModel")
        # 3. FK model in fk_models_list does not exist
        with pytest.raises(LookupError):
            self.init_temp_model(foreign_keys=[("nonexistentapp", "NonexistentModel")])

    def test_fk_model_string_path_invalid(self):
        self.init_temp_app(app_name="directory.temp_app")
        self.init_temp_model(model_name="DuplicateModel", app_name="temp_app")
        with pytest.raises(LookupError):
            self.init_temp_model(
                foreign_keys=[("directory.temp_app", "DuplicateModel")]
            )

    def test_field_related_errors(self):
        # 1. Duplicate field names in fields
        fields1 = {"field_1": models.CharField(max_length=10)}
        fields2 = {"field_1": models.IntegerField()}  # duplicate key 'field1'
        model_class = self.init_temp_model(fields={**fields1, **fields2})
        field_1_fields = [
            f for f in model_class._meta.get_fields() if f.name == "field_1"
        ]
        self.asserts.assertEqual(
            len(field_1_fields),
            1,
            f"Expected exactly one 'field_1' field, found {len(field_1_fields)}",
        )
        field_1 = field_1_fields[0]
        self.asserts.assertIsInstance(
            field_1,
            models.IntegerField,
            f"'field_1' must be IntegerField, found {field_1.__class__.__name__}",
        )

        # 2. Unsupported field parameter passed
        class BadField(models.CharField):
            def __init__(self, *args, **kwargs):
                kwargs["nonexistent_param"] = True
                super().__init__(*args, **kwargs)

        with pytest.raises(TypeError):
            self.init_temp_model(fields={"bad_field": BadField(max_length=10)})

    # ------------------------
    # 🚧 BOUNDARY TESTS
    # ------------------------
    def test_custom_model_table_name_at_max_length(self):
        max_length = getattr(settings, "DB_TABLE_NAME_MAX_LENGTH", 63)
        long_table_name = "a" * max_length
        model_name = "TestModel"
        model = self.init_temp_model(model_name=model_name, table_name=long_table_name)
        self.asserts.assertEqual(len(model._meta.db_table) - 4, max_length)

    def test_dynamic_creator_allows_10_plus_fk_fields(self):
        # Create 10 different temporary models in a test app
        fk_models = []
        for i in range(10):
            model_name = f"TempModel{i}Model"
            temp_model = self.init_temp_model(model_name=model_name)
            fk_models.append((temp_model._meta.app_label, temp_model.__name__))
        model = self.init_temp_model(foreign_keys=fk_models)
        fk_fields = [
            f for f in model._meta.get_fields() if isinstance(f, models.ForeignKey)
        ]
        self.asserts.assertEqual(len(fk_fields), 10)

    def test_charfield_max_length_exactly_255(self):
        fields = {"char255": models.CharField(max_length=255)}
        model = self.init_temp_model(fields=fields)
        char_field = model._meta.get_field("char255")
        self.asserts.assertEqual(char_field.max_length, 255)

    def test_auto_generated_table_name_length_at_max_limit(self):
        max_length = getattr(settings, "DB_TABLE_NAME_MAX_LENGTH", 63)
        model_name = "A" * 63 + "Model"
        model = self.init_temp_model(model_name=model_name)
        self.asserts.assertEqual(len(model._meta.db_table) - 4, max_length)

    # ------------------------
    # 🌀 ANOMALY TESTS
    # ------------------------
    def test_app_name_empty_autofills_current_app(self):
        model = self.init_temp_model(app_name="")
        self._common_assertions(model)


# =================================================================
# 🧩 SUB FUNCTIONS
# =================================================================
