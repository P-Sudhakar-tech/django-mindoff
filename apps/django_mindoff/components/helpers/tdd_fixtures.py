import pytest
import uuid
from django.db import models, connection

#TDD0001 -- Make Temporary Model
@pytest.fixture
def initialize_temp_model():
    def _make_model_connection(*, 
                            app_name: str,
                            model_name: str = "TestModel",
                            table_name: str = "tbl_test",
                            main_models: list = [],
                            fields: dict = {},
                            base_model=models.Model):
        # Create target and FK models dynamically
        model_class = _make_model(app_name, model_name, table_name, main_models, fields, base_model)
        with connection.schema_editor() as editor:
            table = model_class._meta.db_table
            if table in connection.introspection.table_names():
                editor.delete_model(model_class)
            editor.create_model(model_class)

        created_models.append(model_class)
        return model_class
    
    # ---- Setup models ----
    created_models = []
    yield _make_model_connection

    # ---- Teardown models ----
    with connection.schema_editor() as editor:
        for model in created_models:
            editor.delete_model(model)


# ======= ⚓ SUB FUNCTIONS =======
def _make_model(
    app_name: str,
    model_name: str,
    table_name: str,
    main_models: list,
    fields: dict,
    base_model=models.Model
):
    model_fields = {
        "id": models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False,
            db_column=f"{table_name}_id"
        ),
        "__module__": __name__,
    }
    for main_model_class, fk_name in main_models:
        model_fields[fk_name] = models.ForeignKey(
            main_model_class,
            on_delete=models.CASCADE,
            db_column=f"{fk_name}_id"
        )
    model_fields.update(fields)
    
    class Meta:
        app_label = app_name
        db_table = table_name

    model_fields["Meta"] = Meta

    def __str__(self):
        return str(self.id)
    model_fields["__str__"] = __str__
    return type(model_name, (base_model,), model_fields)
