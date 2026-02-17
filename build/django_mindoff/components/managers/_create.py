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
            if command == "createmodel":
                for model_path in remaining_args:
                    subprocess.run([sys.executable, "mindoff.py", command, model_path])
            else:
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
        model_input = input(
            "\n⌨️  Model name(s) (PascalCase, space-separated, e.g. ProductItem OrderLine): "
        ).strip()
        model_names = model_input.split()
        if model_names and all(
            re.match(r"^[A-Z][a-zA-Z0-9]*$", m) for m in model_names
        ):
            break
        print("❌ Invalid model name(s). Each must be PascalCase (e.g. ProductItem).")

    return [f"{app_name}/{model_name}" for model_name in model_names]


# -------------------
# 3. Create Foreign Key Field
# -------------------
def _create_model_field_flow(local_apps):
    print("\n# ------- Mindoff > Create > Foreign Key Field ------- #")
    models, model = _choose_a_existing_model(local_apps)
    if not model:
        return []

    # Determine existing fields in chosen model for duplicate checking
    app, model_class = model.split("/")
    model_file = apps_folder / app / "models.py"
    model_text = model_file.read_text() if model_file.exists() else ""

    # Field name — blank allowed (auto-generate), but force input if auto name collides
    field_name = input(
        "\n⌨️  Field name (snake_case, leave blank to auto-generate): "
    ).strip()

    if field_name:
        # Validate format
        while not re.match(r"^[a-z][a-z0-9_]*$", field_name) or field_name.endswith(
            "_"
        ):
            print("❌ Invalid field name. Must be snake_case (e.g. to_account).")
            field_name = input("⌨️  Field name: ").strip()
        # Normalise to _ref suffix for duplicate check
        normalised = field_name if field_name.endswith("_ref") else f"{field_name}_ref"
        if re.search(rf"\b{normalised}\s*=", model_text):
            print(
                f"⚠️  Field '{normalised}' already exists in {model_class}. You must provide a different name."
            )
            while True:
                field_name = input("⌨️  Field name: ").strip()
                if (
                    not field_name
                    or not re.match(r"^[a-z][a-z0-9_]*$", field_name)
                    or field_name.endswith("_")
                ):
                    print("❌ Invalid field name.")
                    continue
                normalised = (
                    field_name if field_name.endswith("_ref") else f"{field_name}_ref"
                )
                if re.search(rf"\b{normalised}\s*=", model_text):
                    print(f"❌ '{normalised}' also already exists. Try another name.")
                    continue
                break

    args = [model, field_name, "foreign_key"]
    args = __create_foreign_key_field_flow(args, models)
    return args


def __create_foreign_key_field_flow(args, models):
    while True:
        parent = _choose_from_list("Select Parent Model:", models)
        if parent:
            break
        print("❌ Invalid parent model. Please try again.")
    args += ["--to", parent]
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
