import re
from pathlib import Path
from apps.django_mindoff.components.helper_kit import mo_helper_kit


# ======== CONSTANTS =======
# Add Constants here
MODEL_FILE_NAME = "models.py"


# ======== CLASSES =======
# Add Classes here
class DjangoModelCreator:
    def __init__(self, model_path: str, parents: list[str] = None):
        self.model_path = model_path
        self.parents = parents or []
        self.original_app_name = None
        self.normalized_app_name = None
        self.raw_model = None
        self.final_model_name = None
        self.base_name = None
        self.parent_class = None
        self.app = None
        self.model_imports = []
        self.serializer_imports = []
        self.foreign_key_fields = []
        self.foreign_serializer_fields = []

    def _normalize_app_name(self, dotted_path: str) -> str:
        if not dotted_path.startswith("apps."):
            dotted_path = f"apps.{dotted_path}"
        app_names = dotted_path.split(".")
        if len(app_names) != 2:
            raise ValueError(f"Invalid App Name or Path'{dotted_path}'")
        normalized = [app_names[0]] + [p.lower() for p in app_names[1:]]
        if any(not p for p in normalized):
            raise ValueError(
                f"Invalid path '{dotted_path}': segments cannot be empty after normalization."
            )
        return ".".join(normalized)

    def _parse_input(self):
        try:
            self.original_app_name, self.raw_model = self.model_path.split("/")
        except ValueError:
            print("❌ Model path must be in format <app_name>/<model_name>")
            return False
        self.normalized_app_name = self._normalize_app_name(self.original_app_name)
        self.app = self.normalized_app_name
        self.final_model_name, changes = self._format_model_name(self.raw_model)
        if changes:
            print(f"Generated model name: '{self.final_model_name}'")
        self.base_name = self.raw_model.lower().replace("model", "")
        return True

    def _format_model_name(self, name):
        pascal = re.sub(r"(?:^|_)([a-z])", lambda x: x.group(1).upper(), name)
        final = pascal if pascal.endswith("Model") else f"{pascal}Model"
        changes = []
        if name != pascal:
            changes.append(f"PascalCase: '{name}' → '{pascal}'")
        if not pascal.endswith("Model"):
            changes.append(f"Added 'Model' suffix: '{pascal}' → '{final}'")
        return final, changes

    def _get_base_model(self):
        self.parent_class = "mindoffmodels.TimeStampModel"
        print(f"✅ Class set to {self.parent_class}")

    def _validate_and_prepare_parents(self):
        for parent in self.parents:
            try:
                parent_path, parent_model_raw = parent.split("/")
            except ValueError:
                raise ValueError(
                    f"❌ Invalid parent format '{parent}', expected <app_name>/<model_name>"
                )
            if parent == self.model_path:
                raise ValueError(f"❌ A model cannot be its own parent: {parent}")
            normalized_path = self._normalize_app_name(parent_path)
            app_dir = Path(normalized_path.replace(".", "/"))
            model_file = app_dir / MODEL_FILE_NAME
            parent_model, _ = self._format_model_name(parent_model_raw)
            if (
                not model_file.exists()
                or f"class {parent_model}(" not in model_file.read_text()
            ):
                raise ValueError(
                    f"❌ Parent model '{parent_model}' not found in '{normalized_path}'"
                )
            import_alias = normalized_path.replace(".", "_") + "_model"
            if normalized_path == self.app:
                import_alias = None  # Same app – no import required
            field_name = parent_model_raw.lower().removesuffix("model")
            self.foreign_key_fields.append(
                f"{field_name} = models.ForeignKey("
                f'{"" if not import_alias else import_alias + "."}{parent_model}, '
                f'on_delete=models.CASCADE, db_column="{field_name}_id")'
            )
            if import_alias:
                self.model_imports.append((normalized_path, import_alias))

    def _generate_foreign_serializer_fields(self):
        for parent in self.parents:
            parent_path, parent_model_raw = parent.split("/")
            normalized_path = self._normalize_app_name(parent_path)
            parent_model, _ = self._format_model_name(parent_model_raw)
            serializer_name = f"{parent_model}Serializer"
            app_dir = Path(normalized_path.replace(".", "/"))
            serializer_file = app_dir / "serializers.py"
            if not serializer_file.exists():
                raise FileNotFoundError(
                    f"❌ serializers.py not found in '{normalized_path}'"
                )
            serializer_text = serializer_file.read_text()
            if f"class {serializer_name}(" not in serializer_text:
                raise ValueError(
                    f"❌ Serializer '{serializer_name}' not found in {serializer_file}"
                )
            if normalized_path == self.app:
                serializer_ref = serializer_name
            else:
                import_alias = normalized_path.replace(".", "_")
                self.serializer_imports.append(
                    (normalized_path, import_alias, serializer_name)
                )
                serializer_ref = f"{import_alias}_serializer.{serializer_name}"
            field_name = parent_model_raw.lower().removesuffix("model")
            self.foreign_serializer_fields.append(
                f"    {field_name} = {serializer_ref}()"
            )

    def _generate_files(self):
        model_path = Path(self.app.replace(".", "/")) / MODEL_FILE_NAME
        serializer_path = Path(self.app.replace(".", "/")) / "serializers.py"
        fields_code = "\n    ".join(
            [
                f'id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="{self.base_name}_id")'
            ]
            + self.foreign_key_fields
            + ["# Add model fields here"]
        )
        model_code = f"""
class {self.final_model_name}({self.parent_class}):
    {fields_code}

    class Meta:
        db_table = 'tbl_{self.base_name}'

    def __str__(self):
        return str(self.{self.base_name}_id)
""".strip()
        foreign_fields = "\n".join(self.foreign_serializer_fields)
        serializer_code = f"""
class {self.final_model_name}Serializer(serializers.ModelSerializer):
{foreign_fields if foreign_fields else ''}
    class Meta:
        model = models.{self.final_model_name}
        fields = '__all__'
""".strip()
        self._append_to_file(
            model_path,
            model_code,
            self.final_model_name,
            self.model_imports,
            kind="models",
        )
        self._append_to_file(
            serializer_path,
            serializer_code,
            f"{self.final_model_name}Serializer",
            self.serializer_imports,
            kind="serializers",
        )

    def _append_to_file(
        self, path: Path, content: str, check_class: str, import_tuples, kind: str
    ):
        if kind not in ("models", "serializers"):
            raise ValueError(f"❌ Invalid kind '{kind}'")
        base_import, imports = self._generate_imports(kind, import_tuples)
        if path.exists():
            text = path.read_text()
            if f"class {check_class}(" in text:
                print(
                    f"❌ Class '{check_class}' already exists in {path.name}. Skipping."
                )
                return
            lines = text.splitlines()
            existing_imports = {
                l.strip() for l in lines if l.strip().startswith("from")
            }
            new_imports = [line for line in imports if line not in existing_imports]
            insert_index = next(
                (
                    i + 1
                    for i, line in enumerate(lines)
                    if line.strip().startswith(("from", "import"))
                ),
                0,
            )
            if new_imports:
                lines[insert_index:insert_index] = new_imports
            lines.append("")
            lines.append(content)
            path.write_text("\n".join(lines))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            lines = [base_import] + imports + ["", content]
            path.write_text("\n".join(lines))
        print(f"✅ Written to {path}")

    def _generate_imports(self, kind: str, import_tuples):
        if kind == "models":
            imports = [
                f"from {p} import models as {alias}" for p, alias in import_tuples
            ]
            base_import = "from django.db import models"
        else:  # serializers
            imports = [
                f"from {p}.serializers import {s} as {alias}_serializer"
                for p, alias, s in import_tuples
            ]
            base_import = "from rest_framework import serializers"
        return base_import, imports

    @mo_helper_kit.file_guardian
    def run(self):
        if not self._parse_input():
            return
        project_root = Path.cwd()
        app_dir = project_root / self.app.replace(".", "/")
        if not app_dir.exists():
            print(f"❌ App directory '{app_dir}' doesn't exist")
            return
        self._get_base_model()
        self._validate_and_prepare_parents()
        self._generate_foreign_serializer_fields()
        self._generate_files()


# ======== FUNCTIONS =======
# Add Functions here
# F1. Command Entry Point -- Registers the command into the CLI.
def register_subcommand(subparsers):
    def _create_model(args):
        DjangoModelCreator(args.model_path, args.parents).run()

    parser = subparsers.add_parser(
        "createmodel", help="Create Django model with optional parents"
    )
    parser.add_argument(
        "model_path", help="New Model path in format <app_name>/<ModelName>"
    )
    parser.add_argument(
        "--parents",
        nargs="*",
        help="Parent Model path in format <app_name>/<ModelName> spaced apart for multiple foreign keys",
    )
    parser.set_defaults(handler=_create_model)


# ======== SUB-FUNCTIONS =======
# Add Sub-functions here
