import subprocess
import sys
from pathlib import Path
import re

apps_folder = Path("apps")


# -------------------
# Main Registration
# -------------------
def register_subcommand(subparsers):
    def run(args):
        options = {
            "1": ("app", "createapp"),
            "2": ("model", "createmodel"),
            "3": ("model-field", "create_model_field"),
            "4": ("api", "createapi"),
        }
        print("\n# ------- Mindoff > Create ------- #")
        print("🔢 What would you like to create ?")
        for num, (name, _) in options.items():
            print(f"{num}. {name}")
        choice = input("Enter choice of number: ").strip()
        if choice not in options and choice not in [v[0] for v in options.values()]:
            print("Invalid choice. Exiting...")
            return

        command = (
            options.get(choice, (None, None))[1]
            or [c for _, c in options.values() if _ == choice][0]
        )

        local_apps = _get_local_apps()
        remaining_args = []

        if command == "createmodel":
            remaining_args = _create_model_flow(local_apps)
        elif command == "create_model_field":
            remaining_args = _create_model_field_flow(local_apps)
        elif command == "createapp":
            remaining_args = _create_app_flow()
        elif command == "createapi":
            remaining_args = _create_api_flow(local_apps)

        if remaining_args:
            subprocess.run([sys.executable, "mindoff.py", command] + remaining_args)

    parser = subparsers.add_parser(
        "create", help="Guided interactive creator for apps, models, and APIs"
    )
    parser.set_defaults(handler=run)


# -------------------
# 1. Create App
# -------------------
def _create_app_flow():
    apps = input(
        "\n⌨️  App name(s) (space-separated snake_case, e.g. app_one app_two): "
    ).strip()
    return apps.split() if apps else []


# -------------------
# 2. Create Model
# -------------------
def _create_model_flow(local_apps):
    if not local_apps:
        print("No valid apps found in 'apps' directory. Exiting...")
        return []

    app_name = _choose_from_list("Select an app:", local_apps)
    if not app_name:
        print("Invalid app selection. Exiting...")
        return []

    model_name = input("\n⌨️  Model name (PascalCase, e.g. ProductItem): ").strip()
    if not re.match(r"^[A-Z][a-zA-Z0-9]*$", model_name):
        print("Invalid model name. Must be PascalCase (e.g. ProductItem). Exiting...")
        return []

    return [f"{app_name}/{model_name}"]


# -------------------
# 3. Create Model Field
# -------------------
def _create_model_field_flow(local_apps):
    # 1. Choose Model
    print("\n# ------- Mindoff > Create > Model Field ------- #")
    models, model = _choose_a_existing_model(local_apps)
    if not model:
        return []

    # 2. Choose Field Type
    field_types = [
        "foreign_key",
        "char",
        "email",
        "url",
        "slug",
        "integer",
        "big_integer",
        "small_integer",
        "positive_integer",
        "positive_small_integer",
        "float",
        "decimal",
        "date",
        "datetime",
        "time",
        "duration",
        "text",
        "bool",
        "json",
        "auto",
        "big_auto",
        "small_auto",
        "ip_address",
        "uuid",
    ]
    field_type = _choose_from_list("Select field type:", field_types)
    if not field_type:
        print("Invalid field type. Exiting...")
        return []

    # 3. Enter Field Name
    field_name = input("\n⌨️  Field name (snake_case, e.g. to_account): ").strip()
    if not re.match(r"^[a-z][a-z0-9_]*$", field_name):
        print("Invalid field name. Must be snake_case. Exiting...")
        return []
    args = [model, field_name, field_type]

    # 4. Proceed with Field Creation
    if field_type == "foreign_key":
        args = __create_foreign_key_field_flow(args, models)
    elif field_type in ("char", "email", "url", "slug"):
        args = __create_char_field_flow(args)
    elif field_type in (
        "integer",
        "big_integer",
        "small_integer",
        "positive_integer",
        "positive_small_integer",
        "float",
        "decimal",
    ):
        args = __create_numeric_field_flow(args, field_type)

    elif field_type in ("date", "datetime", "time"):
        args = __create_date_field_flow(args)

    elif field_type in ("text", "bool", "json", "duration", "ip_address"):
        args = __create_common_field_flow(args, field_type)

    elif field_type in ("auto", "big_auto", "small_auto"):
        args = __create_auto_field_flow(args)

    elif field_type == "uuid":
        args = __create_uuid_field_flow(args)
    else:
        print("Invalid field type. Exiting...")
        return []
    return args


def __create_foreign_key_field_flow(args, models):
    # 1. Choose Parent
    parent = _choose_from_list(
        "Select Parent Model:",
        models,
    )
    if not parent:
        print("Invalid parent model. Exiting...")
        return []
    args += ["--to", parent]

    # 2. Choose on_delete behavior
    on_delete_choices = [
        "CASCADE",
        "PROTECT",
        "SET_NULL",
        "SET_DEFAULT",
        "DO_NOTHING",
    ]
    on_delete = _choose_from_list(
        "Select on_delete behavior (default: CASCADE):",
        on_delete_choices,
        "(leave blank for default)",
    )
    if on_delete:
        args += ["--on_delete", on_delete]

    # 3. Choose Common Constraints
    args.extend(
        _choose_common_field_constraints(
            [
                "allow_null",
                "allow_blank",
                "is_unique",
                "is_db_index",
                "disable_related_name",
            ],
            is_mandatory_default=True if on_delete == "SET_DEFAULT" else False,
        )
    )

    return args


def __create_char_field_flow(args):
    # 1. Get Max Length
    max_length = prompt_value(
        "Enter Max Length (1-255) (Default: 255): ",
        value_type=int,
        default=255,
        min_val=1,
        max_val=255,
    )
    args += ["--max_length", str(max_length)]

    # 2. Choose Common Constraints
    args.extend(
        _choose_common_field_constraints(
            [
                "allow_null",
                "allow_blank",
                "is_unique",
                "is_db_index",
                "is_choice_field",
            ],
            is_mandatory_default=False,
        )
    )
    return args


def __create_numeric_field_flow(args, field_type):
    if field_type == "decimal":
        # 1. Get Max Digits (mandatory, with default)
        max_digits = prompt_value(
            "Enter max digits (Default: 10): ",
            value_type=int,
            default=10,
            min_val=1,
        )

        # 2. Get Decimal Places (mandatory, with default)
        while True:
            decimal_places = prompt_value(
                "Enter decimal places (Default: 2): ",
                value_type=int,
                default=2,
                min_val=0,
            )

            if decimal_places >= max_digits:
                print("❌ Decimal places must be less than max digits.")
                continue
            break
        args += ["--max_digits", str(max_digits)]
        args += ["--decimal_places", str(decimal_places)]

    # 3. Get Min Value
    min_value = None
    if field_type not in ("positive_integer", "positive_small_integer"):
        min_value = prompt_value(
            "Enter minimum value (Optional): ",
            value_type=float,
            default=None,
        )
    if min_value is not None:
        args += ["--min_value", str(min_value)]

    # 4. Get Max Value
    max_value = None
    while True:
        max_value = prompt_value(
            "Enter maximum value (Optional): ",
            value_type=float,
            default=None,
        )
        if min_value and max_value and max_value < min_value:
            print("❌ Maximum value cannot be less than minimum value.")
            continue
        break
    if max_value is not None:
        args += ["--max_value", str(max_value)]

    # 5. Choose Common Constraints
    args.extend(
        _choose_common_field_constraints(
            [
                "allow_null",
                "is_unique",
                "is_db_index",
                "is_choice_field",
            ],
            is_mandatory_default=False,
        )
    )
    return args


def __create_date_field_flow(args):
    args.extend(
        _choose_common_field_constraints(
            [
                "allow_null",
                "is_unique",
                "is_db_index",
                "is_choice_field",
                "is_auto_now",
                "is_auto_now_add",
            ]
        )
    )
    return args


def __create_auto_field_flow(args):
    args.extend(
        _choose_common_field_constraints(
            [
                "is_db_index",
            ]
        )
    )
    return args


def __create_uuid_field_flow(args):
    args.extend(
        _choose_common_field_constraints(
            [
                "allow_null",
                "is_unique",
                "is_db_index",
            ]
        )
    )

    print(
        "\nℹ️  UUID default options:\n"
        "1. uuid4 (auto-generate)\n"
        "2. Provide a UUID v4 value\n"
        "Leave blank to skip default"
    )
    choice = input("Enter choice (1/2 or blank): ").strip()

    if choice == "1":
        args += ["--default", "uuid4"]
    elif choice == "2":
        value = input("Enter UUID v4 value: ").strip()
        if value:
            args += ["--default", value]

    return args


def __create_common_field_flow(args, field_type):
    if field_type in ("text", "json"):
        args.extend(
            _choose_common_field_constraints(
                [
                    "allow_null",
                    "allow_blank",
                    "is_unique",
                    "is_db_index",
                    "is_choice_field",
                ]
            )
        )
    else:
        args.extend(
            _choose_common_field_constraints(
                [
                    "allow_null",
                    "is_unique",
                    "is_db_index",
                    "is_choice_field",
                ]
            )
        )

    return args


# -------------------
# 4. Create API
# -------------------
def _create_api_flow(local_apps):
    if not local_apps:
        print("No valid apps found in 'apps' directory. Exiting...")
        return []

    app_name = _choose_from_list("Select an app:", local_apps)
    if not app_name:
        print("Invalid app selection. Exiting...")
        return []

    api_name = input("Enter API name (snake_case, e.g. user_profile): ").strip()
    if not re.match(r"^[a-z][a-z0-9_]*$", api_name):
        print("Invalid API name. Must be snake_case (e.g. user_profile). Exiting...")
        return []

    args = [f"{app_name}/{api_name}"]

    urls = input(
        "Enter URL(s) for this API, separated by spaces (e.g., user_profile user/<int:id>/detail).\n"
        "Leave blank to auto create url: "
    ).strip()
    if urls:
        args += ["--url"] + urls.split()

    return args


# -------------------
# Helper Functions
# -------------------
def _get_local_apps():
    return [
        d.name
        for d in apps_folder.iterdir()
        if d.is_dir()
        and (apps_folder / d.name / "__init__.py").exists()
        and (
            (apps_folder / d.name / "apps.py").exists()
            or (apps_folder / d.name / "models.py").exists()
        )
    ]


def _choose_from_list(prompt, items, bracket_suffix=""):
    print(f"\n🔢 {prompt}")
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")
    choice = input(f"Enter choice of 'number' {bracket_suffix}: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        return items[int(choice) - 1]
    elif choice in items:
        return choice
    return None


def _choose_a_existing_model(local_apps):
    models = []
    for app in local_apps:
        models_file = apps_folder / app / "models.py"
        if not models_file.exists():
            continue
        for line in models_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("class ") and "(" in line:
                cls = line.split("class ")[1].split("(")[0]
                models.append(f"{app}/{cls}")
    if not models:
        print("No existing models found. Exiting...")
        return None
    model = _choose_from_list("Select a Model:", models)
    if not model:
        print("Invalid model selection. Exiting...")
        return None
    return models, model


def _choose_common_field_constraints(allowed_keys, is_mandatory_default=False):
    common_field_constraints = (
        ("allow_null", "Allow Null Field"),
        ("allow_blank", "Allow Empty Value"),
        ("is_unique", "Unique Field"),
        ("is_db_index", "Create Database Index"),
        ("is_choice_field", "Choice Field"),
        ("is_auto_now", "Auto Now Field"),
        ("is_auto_now_add", "Auto Now Add Field"),
        ("disable_related_name", "Disable Foreign Key Relation"),
    )
    args: list[str] = []
    filtered_options = [
        (key, label) for key, label in common_field_constraints if key in allowed_keys
    ]

    options = [
        (str(i + 1), key, label) for i, (key, label) in enumerate(filtered_options)
    ]

    if not options:
        return args

    print("\n🔢 Select field constraints and additional behaviors:")
    for number, _, label in options:
        print(f"{number}. {label}")
    choice = input(
        "Enter choice of number(s) (space seperated) (Optional, Leave blank to skip)): "
    ).strip()
    if not choice:
        return args

    selected = set(choice.split())

    for number, key, _ in options:
        if number in selected:
            args.append(f"--{key}")

    if "is_auto_now" in args and "is_auto_now_add" in args:
        print("❌ Cannot use auto_now and auto_now_add together")
        return []

    prompt = (
        "\n⌨️  Default value (required): "
        if is_mandatory_default
        else "\n⌨️  Default value (optional, Leave blank to skip): "
    )
    while True:
        default_input = input(prompt).strip()
        if not default_input:
            if is_mandatory_default:
                print("❌ Default value is required. Please enter a value.")
                continue
            return args

        args += ["--default", default_input]
        break

    return args


def prompt_value(
    label,
    *,
    value_type,  # int | float
    default=None,
    min_val=None,
    max_val=None,
):
    while True:
        raw = input(label).strip()

        if raw == "":
            if default is not None:
                return default
            print("❌ This value is required.")
            continue

        try:
            value = value_type(raw)
        except ValueError:
            print(f"❌ Please enter a valid {value_type.__name__}.")
            continue

        if min_val is not None and value < min_val:
            print(f"❌ Value must be ≥ {min_val}.")
            continue

        if max_val is not None and value > max_val:
            print(f"❌ Value must be ≤ {max_val}.")
            continue

        return value
