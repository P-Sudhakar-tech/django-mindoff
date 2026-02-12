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
            "3": ("foreign-key", "create_model_field"),
            "4": ("api", "createapi"),
        }
        while True:
            print("\n# ------- Mindoff > Create ------- #")
            print("🔢 What would you like to create ?")
            for num, (name, _) in options.items():
                print(f"{num}. {name}")

            choice = input("Enter choice of number: ").strip()

            if choice in options or choice in [v[0] for v in options.values()]:
                break
            print("❌ Invalid choice. Please try again.")

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
        print("No valid apps found in 'apps' directory. Exiting.")
        return []

    while True:
        app_name = _choose_from_list("Select an app:", local_apps)
        if app_name:
            break
        print("❌ Invalid app selection. Please try again.")

    while True:
        model_name = input("\n⌨️  Model name (PascalCase, e.g. ProductItem): ").strip()
        if re.match(r"^[A-Z][a-zA-Z0-9]*$", model_name):
            break
        print("❌ Invalid model name. Must be PascalCase (e.g. ProductItem).")

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

    # 2. Enter Field Name
    while True:
        field_name = input("\n⌨️  Field name (snake_case, e.g. to_account): ").strip()
        if re.match(r"^[a-z][a-z0-9_]*$", field_name):
            break
        print("❌ Invalid field name. Must be snake_case.")
    args = [model, field_name, "foreign_key"]

    # 3. Proceed with Field Creation
    args = __create_foreign_key_field_flow(args, models)

    return args


def __create_foreign_key_field_flow(args, models):
    # 1. Choose Parent
    while True:
        parent = _choose_from_list("Select Parent Model:", models)
        if parent:
            break
        print("❌ Invalid parent model. Please try again.")
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
    return args


# -------------------
# 4. Create API
# -------------------
def _create_api_flow(local_apps):
    if not local_apps:
        print("No valid apps found in 'apps' directory. Exiting.")
        return []

    while True:
        app_name = _choose_from_list("Select an app:", local_apps)
        if app_name:
            break
        print("❌ Invalid app selection. Please try again.")

    while True:
        api_name = input("Enter API name (snake_case, e.g. user_profile): ").strip()
        if re.match(r"^[a-z][a-z0-9_]*$", api_name):
            break
        print("❌ Invalid API name. Must be snake_case.")

    args = [f"{app_name}/{api_name}"]

    urls = input(
        "Enter URL(s) for this API, separated by spaces "
        "(e.g., user_profile user/<int:id>/detail).\n"
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
        print("No existing models found. Exiting.")
        return None
    while True:
        model = _choose_from_list("Select a Model:", models)
        if model:
            return models, model
        print("❌ Invalid model selection. Please try again.")
