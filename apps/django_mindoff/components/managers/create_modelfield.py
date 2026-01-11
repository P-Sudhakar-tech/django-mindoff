# --- NOT YET SUPPORTED ---#
# OneToOneField
# ManyToManyField
# BinaryField
# FileUpload
# ImageUpload

import re
from pathlib import Path
from dataclasses import dataclass
from ..helper_kit import mo_helper_kit


# ======== CONSTANTS ========
MODEL_FILE_NAME = "models.py"
FIELD_INSERT_MARKER = (
    "# Add model fields above this line -- "
    "(MANAGED BY MINDOFF. DO NOT TOUCH THIS LINE)"
)

VALID_ON_DELETE = {
    "CASCADE",
    "PROTECT",
    "SET_NULL",
    "SET_DEFAULT",
    "DO_NOTHING",
}

FIELD_REGISTRY = {
    "foreign_key": {
        "django_field": "ForeignKey",
        "required": {"to"},
        "optional": {
            "on_delete",
            "allow_null",
            "is_unique",
            "is_db_index",
            "disable_related_name",
        },
    },
    "char": {
        "django_field": "CharField",
        "required": {"max_length"},
        "optional": {
            "allow_null",
            "allow_blank",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "email": {
        "django_field": "EmailField",
        "required": {"max_length"},
        "optional": {
            "allow_null",
            "allow_blank",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "url": {
        "django_field": "URLField",
        "required": {"max_length"},
        "optional": {
            "allow_null",
            "allow_blank",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "slug": {
        "django_field": "SlugField",
        "required": {"max_length"},
        "optional": {
            "allow_null",
            "allow_blank",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "integer": {
        "django_field": "IntegerField",
        "required": set(),
        "optional": {
            "min_value",
            "max_value",
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "big_integer": {
        "django_field": "BigIntegerField",
        "required": set(),
        "optional": {
            "min_value",
            "max_value",
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "small_integer": {
        "django_field": "SmallIntegerField",
        "required": set(),
        "optional": {
            "min_value",
            "max_value",
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "positive_integer": {
        "django_field": "PositiveIntegerField",
        "required": set(),
        "optional": {
            "max_value",
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "positive_small_integer": {
        "django_field": "PositiveSmallIntegerField",
        "required": set(),
        "optional": {
            "max_value",
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "float": {
        "django_field": "FloatField",
        "required": set(),
        "optional": {
            "min_value",
            "max_value",
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "decimal": {
        "django_field": "DecimalField",
        "required": {"max_digits", "decimal_places"},
        "optional": {
            "min_value",
            "max_value",
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "date": {
        "django_field": "DateField",
        "required": set(),
        "optional": {
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
            "is_auto_now",
            "is_auto_now_add",
        },
    },
    "datetime": {
        "django_field": "DateTimeField",
        "required": set(),
        "optional": {
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
            "is_auto_now",
            "is_auto_now_add",
        },
    },
    "time": {
        "django_field": "TimeField",
        "required": set(),
        "optional": {
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
            "is_auto_now",
            "is_auto_now_add",
        },
    },
    "duration": {
        "django_field": "DurationField",
        "required": set(),
        "optional": {
            "allow_null",
            "is_unique",
            "is_db_index",
        },
    },
    "json": {
        "django_field": "JSONField",
        "required": set(),
        "optional": {
            "allow_null",
            "allow_blank",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "text": {
        "django_field": "TextField",
        "required": set(),
        "optional": {
            "allow_null",
            "allow_blank",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "bool": {
        "django_field": "BooleanField",
        "required": set(),
        "optional": {
            "allow_null",
            "is_unique",
            "is_db_index",
            "is_choice_field",
        },
    },
    "auto": {
        "django_field": "AutoField",
        "required": set(),
        "optional": {"is_db_index"},
    },
    "big_auto": {
        "django_field": "BigAutoField",
        "required": set(),
        "optional": {"is_db_index"},
    },
    "small_auto": {
        "django_field": "SmallAutoField",
        "required": set(),
        "optional": {"is_db_index"},
    },
    "ip_address": {
        "django_field": "GenericIPAddressField",
        "required": set(),
        "optional": {
            "allow_null",
            "allow_blank",
            "is_unique",
            "is_db_index",
        },
    },
    "uuid": {
        "django_field": "UUIDField",
        "required": set(),
        "optional": {
            "allow_null",
            "is_unique",
            "is_db_index",
        },
    },
}


# ======== CLASSES ========
@dataclass
class InputBasedParameters:
    default: str | None = None
    to: str | None = None
    on_delete: str = "CASCADE"
    max_length: int | None = None
    max_digits: int | None = None
    decimal_places: int | None = None
    min_value: float | int | None = None
    max_value: float | int | None = None


@dataclass
class BooleanBasedParameters:
    allow_null: bool = False
    allow_blank: bool = False
    is_unique: bool = False
    is_db_index: bool = False
    is_choice_field: bool = False
    is_auto_now: bool = False
    is_auto_now_add: bool = False
    disable_related_name: bool = False


# ========= MAIN CLASS =========
class DjangoModelFieldCreator:
    """
    Creates a Django model field and injects it into models.py
    """

    # -----------------
    # Init
    # -----------------
    def __init__(
        self,
        model_path: str,
        field_name: str,
        field_type: str,
        *,
        boolean_based_parameters=None,
        input_based_parameters=None,
    ):
        self.model_path = model_path
        self.field_name = field_name
        self.field_type = field_type
        self.model_import_alias = None
        self.parent_model = None
        self.boolean_based_parameters = boolean_based_parameters
        self.input_based_parameters = input_based_parameters

    # -----------------
    # Public Entry
    # -----------------
    @mo_helper_kit.file_guardian
    def run(self):
        self._parse_model_path()
        self._validate_field_and_parameters()
        field_code = self._build_model_field()
        self._ensure_choice_blueprint()
        self.__insert_field(field_code)

    # -----------------
    # 1. PARSE
    # -----------------
    def _parse_model_path(self):
        try:
            app, model_raw = self.model_path.split("/")
        except ValueError:
            raise ValueError("❌ Model path must be <app>/<ModelName>")

        self.app_slug = app.lower()
        self.model_name = self.__format_model_name(model_raw)

        self.model_file = Path("apps") / self.app_slug / MODEL_FILE_NAME
        if not self.model_file.exists():
            raise FileNotFoundError("❌ models.py not found")

        text = self.model_file.read_text()
        if f"class {self.model_name}(" not in text:
            raise ValueError(f"❌ Model {self.model_name} not found")

        if FIELD_INSERT_MARKER not in text:
            raise ValueError("❌ Field insert marker missing")

    # -----------------
    # 2. VALIDATE
    # -----------------
    def _validate_field_and_parameters(self):
        # 1. Validate field type
        if self.field_type not in FIELD_REGISTRY:
            raise ValueError(f"❌ Unsupported field type: {self.field_type}")

        rules = FIELD_REGISTRY[self.field_type]

        # 2. Validate field name
        if not re.match(r"^[a-z][a-z0-9_]*$", self.field_name):
            raise ValueError("❌ Invalid field name")

        if self.field_name.endswith(("_fk", "_rk")):
            raise ValueError("❌ Reserved suffix used")

        lines = self.model_file.read_text().splitlines()
        start, end = self.__get_model_block(lines)
        model_block = "\n".join(lines[start:end])
        if re.search(rf"\b{self.field_name}\s*=", model_block):
            raise ValueError(
                f"❌ Field '{self.field_name}' already exists in {self.model_name}"
            )

        # 3. Validate field parameters
        params = self.__collect_all_params()

        required = rules["required"]
        optional = rules["optional"]
        allowed = required | optional

        missing = required - params.keys()
        if missing:
            raise ValueError(
                f"❌ Missing required parameters for {self.field_type}: "
                f"{', '.join(sorted(missing))}"
            )

        invalid = params.keys() - allowed
        if invalid:
            raise ValueError(
                f"❌ Invalid parameters for {self.field_type}: "
                f"{', '.join(sorted(invalid))}"
            )

        # 4. Field-specific validation
        self.__validate_field_specific_rules(params)

    # -----------------
    # 3. BUILD
    # -----------------
    def _build_model_field(self):
        opts = []
        if self.field_type == "foreign_key":
            app, model = self.input_based_parameters.to.split("/")
            self.parent_model = self.__format_model_name(model)
            self.model_import_alias = f"apps_{app}_models"
            target = f"{self.model_import_alias}.{self.parent_model}"
            opts = [
                f"{target}",
                f"on_delete=models.{self.input_based_parameters.on_delete}",
                f"db_column='{self.field_name}_fk'",
            ]
            import_stmt = (
                f"from apps.{self.input_based_parameters.to.split('/')[0]} "
                f"import models as {self.model_import_alias}"
            )
            self.__insert_import_line(import_stmt)
        elif self.field_type in ("char", "email", "url", "slug"):
            opts = [
                f"max_length={self.input_based_parameters.max_length or 255}",
            ]
        elif self.field_type in (
            "integer",
            "big_integer",
            "small_integer",
            "positive_integer",
            "positive_small_integer",
            "float",
            "decimal",
        ):
            if self.field_type == "decimal":
                opts.append(
                    f"max_digits={self.input_based_parameters.max_digits or 10}"
                )
                opts.append(
                    f"decimal_places={self.input_based_parameters.decimal_places or 2}"
                )
            validators = self.__build_validators()
            if validators:
                opts.append(f"validators=[{', '.join(validators)}]")
        if self.field_type == "uuid":
            self.__insert_import_line("import uuid")
        if self.input_based_parameters.default is not None:
            opts.append(
                f"default={self.__format_default(self.input_based_parameters.default)}"
            )
        opts.extend([*self.__build_common_parameters()])
        return self.__render_field(opts)

    def _ensure_choice_blueprint(self):
        if not (
            self.boolean_based_parameters
            and self.boolean_based_parameters.is_choice_field
        ):
            return

        const_name = self.__build_choices_const_name()
        lines = self.model_file.read_text().splitlines()

        if any(line.startswith(f"{const_name} =") for line in lines):
            return  # already exists

        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith(("from ", "import ")):
                insert_at = i + 1

        blueprint = [
            "",
            f"{const_name} = (",
            "    # ('value', 'Label'),",
            ")",
            "",
        ]

        lines[insert_at:insert_at] = blueprint
        self.model_file.write_text("\n".join(lines))

    # -----------------
    # Helpers
    # -----------------
    def __format_model_name(self, name: str) -> str:
        pascal = re.sub(r"(?:^|_)([a-z])", lambda m: m.group(1).upper(), name)
        return pascal if pascal.endswith("Model") else f"{pascal}Model"

    def __get_model_block(self, lines: list[str]) -> tuple[int, int]:
        """
        Returns (start_index, end_index) of the target model class.
        """
        class_pattern = f"class {self.model_name}("
        start = None

        for i, line in enumerate(lines):
            if line.startswith(class_pattern):
                start = i
                break

        if start is None:
            raise ValueError(f"❌ Model '{self.model_name}' not found")

        for i in range(start + 1, len(lines)):
            if lines[i].startswith("class "):
                return start, i

        return start, len(lines)

    def __collect_all_params(self) -> dict:
        params = {}

        if self.input_based_parameters:
            for k, v in vars(self.input_based_parameters).items():
                if v not in (None, False):
                    params[k] = v

        if self.boolean_based_parameters:
            for k, v in vars(self.boolean_based_parameters).items():
                if v is True:
                    params[k] = True

        return params

    def __validate_field_specific_rules(self, params: dict):
        # ForeignKey rules
        if self.field_type == "foreign_key":
            if not self.input_based_parameters.to:
                raise ValueError("❌ ForeignKey requires --to")

            if self.input_based_parameters.on_delete not in VALID_ON_DELETE:
                raise ValueError("❌ Invalid on_delete value")

            if (
                self.input_based_parameters.on_delete == "SET_DEFAULT"
                and self.input_based_parameters.default is None
            ):
                raise ValueError("❌ ForeignKey with SET_DEFAULT requires default")

        # BooleanField cannot be nullable
        if self.field_type == "bool" and params.get("allow_null"):
            raise ValueError("❌ BooleanField cannot have allow_null=True")
        if self.field_type == "bool" and self.input_based_parameters.default:
            if self.input_based_parameters.default not in {
                "True",
                "False",
                True,
                False,
            }:
                raise ValueError("❌ BooleanField default must be True or False")

        # auto_now rules
        if self.field_type in {"date", "datetime", "time"}:
            if params.get("is_auto_now") and params.get("is_auto_now_add"):
                raise ValueError("❌ auto_now and auto_now_add cannot be used together")

        # UUID default validation
        if self.field_type == "uuid" and self.input_based_parameters.default:
            if self.input_based_parameters.default != "uuid4":
                try:
                    import uuid as _uuid

                    _uuid.UUID(str(self.input_based_parameters.default), version=4)
                except Exception:
                    raise ValueError("❌ UUID default must be 'uuid4' or valid UUID v4")

        # Number field validation
        if self.field_type in {
            "integer",
            "big_integer",
            "small_integer",
            "positive_integer",
            "positive_small_integer",
            "float",
            "decimal",
        }:
            min_v = self.input_based_parameters.min_value
            max_v = self.input_based_parameters.max_value

            if min_v is not None and max_v is not None and min_v > max_v:
                raise ValueError("❌ min_value cannot be greater than max_value")
        if self.field_type in {"positive_integer", "positive_small_integer"}:
            if self.input_based_parameters.min_value is not None:
                raise ValueError(
                    "❌ min_value is not allowed for positive integer fields"
                )
        # Duration Field Validation
        if self.field_type == "duration" and self.input_based_parameters.default:
            if not isinstance(self.input_based_parameters.default, str):
                raise ValueError("❌ Duration default must be a string like 2d4h30m")
            if not self.input_based_parameters.default.strip():
                raise ValueError("❌ Duration default cannot be empty")

        # Date and Time
        if self.field_type in {"date", "datetime", "time"}:
            if self.input_based_parameters.default and (
                params.get("is_auto_now") or params.get("is_auto_now_add")
            ):
                raise ValueError(
                    "❌ default cannot be used with auto_now or auto_now_add"
                )

    def __parse_duration(self, value: str):
        import datetime
        import re

        pattern = (
            r"^(?:(?P<days>\d+)d)?"
            r"(?:(?P<hours>\d+)h)?"
            r"(?:(?P<minutes>\d+)m)?"
            r"(?:(?P<seconds>\d+)s)?"
            r"(?:(?P<milliseconds>\d+)ms)?$"
        )

        match = re.fullmatch(pattern, value)
        if not match:
            raise ValueError("❌ Invalid duration format. " "Use 2d4h30m15s12ms")

        parts = {k: int(v) for k, v in match.groupdict().items() if v is not None}

        if not parts:
            raise ValueError("❌ Duration cannot be empty")

        return datetime.timedelta(**parts)

    def __format_default(self, value):
        if self.field_type in {
            "integer",
            "big_integer",
            "small_integer",
            "positive_integer",
            "positive_small_integer",
            "float",
            "decimal",
        }:
            try:
                value = float(value) if "." in str(value) else int(value)
            except:
                raise ValueError("❌ Default must be numeric")
            return value
        if self.field_type == "uuid":
            if value == "uuid4":
                return "uuid.uuid4"
            try:
                import uuid as _uuid

                parsed = _uuid.UUID(str(value), version=4)
                return f"uuid.UUID('{parsed}')"
            except Exception:
                raise ValueError(
                    "❌ UUID default must be 'uuid4' or a valid UUID v4 value"
                )
        if self.field_type == "bool":
            if str(value).lower() == "true":
                return "True"
            if str(value).lower() == "false":
                return "False"
            raise ValueError("❌ Boolean default must be True or False")
        if self.field_type == "duration":
            try:
                td = self.__parse_duration(value)
                self.__insert_import_line("from datetime import timedelta")
                return "timedelta(" f"milliseconds={int(td.total_seconds() * 1000)}" ")"
            except Exception as e:
                raise ValueError(str(e))
        return repr(value)

    def __render_field(self, args: list[str]):
        django_field = FIELD_REGISTRY[self.field_type]["django_field"]
        lines = [
            f"{self.field_name} = models.{django_field}(",
            f"        {', '.join(args)}",
            f"    )",
        ]

        if self.input_based_parameters.min_value is not None:
            lines.append(
                f"{self.field_name}.min_value = "
                f"{self.input_based_parameters.min_value}"
            )
        if self.input_based_parameters.max_value is not None:
            lines.append(
                f"{self.field_name}.max_value = "
                f"{self.input_based_parameters.max_value}"
            )

        return "\n".join(lines)

    def __insert_import_line(self, import_line: str):
        lines = self.model_file.read_text().splitlines()

        if import_line in lines:
            return

        insert_at = 0
        for i, line in enumerate(lines):
            if line.startswith(("from ", "import ")):
                insert_at = i + 1

        lines.insert(insert_at, import_line)
        self.model_file.write_text("\n".join(lines))

    def __insert_field(self, field_code: str):
        text = self.model_file.read_text()
        updated = text.replace(
            FIELD_INSERT_MARKER,
            f"{field_code}\n\n    {FIELD_INSERT_MARKER}",
        )
        self.model_file.write_text(updated)

    def __build_related_name(self):
        if (
            self.boolean_based_parameters
            and self.boolean_based_parameters.disable_related_name
        ):
            return "+"
        prefix = self.app_slug
        model_base = self.model_name.removesuffix("Model").lower()
        return f"{prefix}_{model_base}_{self.field_name}_rk"

    def __build_validators(self):
        validators = []

        if self.input_based_parameters.min_value is not None:
            validators.append(
                f"MinValueValidator({self.input_based_parameters.min_value})"
            )

        if self.input_based_parameters.max_value is not None:
            validators.append(
                f"MaxValueValidator({self.input_based_parameters.max_value})"
            )

        if validators:
            self.__insert_import_line(
                "from django.core.validators import MinValueValidator, MaxValueValidator"
            )

        return validators

    def __build_choices_const_name(self) -> str:
        base_model = self.model_name.removesuffix("Model")
        return f"{base_model.upper()}_{self.field_name.upper()}_CHOICES"

    def __build_common_parameters(self):
        if not self.boolean_based_parameters:
            return []

        params = self.boolean_based_parameters
        opts = []

        if params.allow_null:
            opts.append("null=True")
        if params.allow_blank and self.field_type in {
            "char",
            "email",
            "url",
            "slug",
            "text",
            "json",
        }:
            opts.append("blank=True")
        if params.is_unique:
            opts.append("unique=True")
        if params.is_db_index:
            opts.append("db_index=True")
        if params.is_auto_now:
            opts.append("auto_now=True")
        if params.is_auto_now_add:
            opts.append("auto_now_add=True")
        if params.is_choice_field:
            opts.append(f"choices={self.__build_choices_const_name()}")
        if self.field_type == "foreign_key":
            related_name = self.__build_related_name()
            opts.append(f"related_name='{related_name}'")

        return opts


# ======== FUNCTIONS ========
def register_subcommand(subparsers):
    def _create_model_field(args):
        input_based_parameters = InputBasedParameters(
            default=args.default,
            to=args.to,
            on_delete=args.on_delete,
            max_length=args.max_length,
            min_value=args.min_value,
            max_value=args.max_value,
            max_digits=args.max_digits,
            decimal_places=args.decimal_places,
        )
        boolean_based_parameters = BooleanBasedParameters(
            allow_null=args.allow_null,
            allow_blank=args.allow_blank,
            is_unique=args.is_unique,
            is_db_index=args.is_db_index,
            is_choice_field=args.is_choice_field,
            is_auto_now=args.is_auto_now,
            is_auto_now_add=args.is_auto_now_add,
            disable_related_name=args.disable_related_name,
        )
        DjangoModelFieldCreator(
            model_path=args.model_path,
            field_name=args.field_name,
            field_type=args.field_type,
            input_based_parameters=input_based_parameters,
            boolean_based_parameters=boolean_based_parameters,
        ).run()

    parser = subparsers.add_parser(
        "create_model_field", help="Create a single field inside a Django model"
    )
    parser.add_argument("model_path", help="<app_name>/<ModelName>")
    parser.add_argument("field_name", help="Field name to create")
    parser.add_argument("field_type", help="Type of field to create")

    # Input Based Parameters
    parser.add_argument("--default")
    parser.add_argument("--to", help="Foreign key target model")
    parser.add_argument("--on_delete", default="CASCADE")
    parser.add_argument("--max_length", type=int)
    parser.add_argument("--min_value", type=float)
    parser.add_argument("--max_value", type=float)
    parser.add_argument("--max_digits", type=int)
    parser.add_argument("--decimal_places", type=int)

    # Boolean Based Parameters
    parser.add_argument("--allow_null", action="store_true")
    parser.add_argument("--allow_blank", action="store_true")
    parser.add_argument("--is_unique", action="store_true")
    parser.add_argument("--is_db_index", action="store_true")
    parser.add_argument("--is_choice_field", action="store_true")
    parser.add_argument("--is_auto_now", action="store_true")
    parser.add_argument("--is_auto_now_add", action="store_true")
    parser.add_argument("--disable_related_name", action="store_true")

    parser.set_defaults(handler=_create_model_field)
