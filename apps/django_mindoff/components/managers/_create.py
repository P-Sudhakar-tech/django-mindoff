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
            "3": ("api", "createapi"),
        }

        print("\n🔢 Select what you want to create:")
        for num, (name, _) in options.items():
            print(f"{num}. {name}")

        choice = input("\nEnter choice of number/name: ").strip()
        if choice not in options and choice not in [v[0] for v in options.values()]:
            print("❌ Invalid choice. Exiting...")
            return

        command = (
            options.get(choice, (None, None))[1]
            or [c for _, c in options.values() if _ == choice][0]
        )

        local_apps = _get_local_apps()
        remaining_args = []

        if command == "createmodel":
            remaining_args = _create_model_flow(local_apps)
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


def _choose_from_list(prompt, items):
    print(prompt)
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")
    choice = input("Enter choice of number/name: ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(items):
        return items[int(choice) - 1]
    elif choice in items:
        return choice
    return None


def _collect_existing_models(local_apps):
    all_models = []
    for app in local_apps:
        models_file = apps_folder / app / "models.py"
        if models_file.exists():
            for line in models_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("class ") and "(" in line:
                    cls_name = line.split("class ")[1].split("(")[0].strip()
                    all_models.append(f"{app}/{cls_name}")
    return all_models


def _create_model_flow(local_apps):
    if not local_apps:
        print("❌ No valid apps found in 'apps' directory. Exiting...")
        return []

    app_name = _choose_from_list("\n🔢 Select an app:", local_apps)
    if not app_name:
        print("❌ Invalid app selection. Exiting...")
        return []

    model_name = input("Enter model name (PascalCase, e.g. ProductItem): ").strip()
    if not re.match(r"^[A-Z][a-zA-Z0-9]*$", model_name):
        print(
            "❌ Invalid model name. Must be PascalCase (e.g. ProductItem). Exiting..."
        )
        return []

    args = [f"{app_name}/{model_name}"]

    add_fk = input("Do you want to add foreign key(s)? [Y/n]: ").strip().lower()
    if add_fk in ("y", "yes", ""):
        parents = _select_foreign_keys(local_apps)
        if parents:
            args += ["--parents"] + parents

    return args


def _select_foreign_keys(local_apps):
    all_models = _collect_existing_models(local_apps)
    if not all_models:
        print("⚠️ No existing models found for foreign key(s). Skipping...")
        return []

    print("\n🔢 Select parent model(s) for foreign key(s):")
    for i, m in enumerate(all_models, 1):
        print(f"{i}. {m}")

    fk_choice = input("Enter choice of number(s)/name(s) (space separated): ").strip()
    parents = []
    if fk_choice:
        for item in fk_choice.split():
            if item.isdigit() and 1 <= int(item) <= len(all_models):
                parents.append(all_models[int(item) - 1])
            elif item in all_models:
                parents.append(item)
            else:
                print(f"⚠️ Skipping invalid parent: {item}")
    return parents


def _create_app_flow():
    apps = input(
        "Enter app name(s) (space-separated snake_case, e.g. app_one app_two): "
    ).strip()
    return apps.split() if apps else []


def _create_api_flow(local_apps):
    if not local_apps:
        print("❌ No valid apps found in 'apps' directory. Exiting...")
        return []

    app_name = _choose_from_list("\nAvailable apps:", local_apps)
    if not app_name:
        print("❌ Invalid app selection. Exiting...")
        return []

    api_name = input("Enter API name (snake_case, e.g. user_profile): ").strip()
    if not re.match(r"^[a-z][a-z0-9_]*$", api_name):
        print("❌ Invalid API name. Must be snake_case (e.g. user_profile). Exiting...")
        return []

    args = [f"{app_name}/{api_name}"]

    urls = input(
        "Enter URL(s) for this API, separated by spaces (e.g., /user_profile /user/<int:id>/detail).\n"
        "Leave blank to auto create url: "
    ).strip()
    if urls:
        args += ["--url"] + urls.split()
    return args
