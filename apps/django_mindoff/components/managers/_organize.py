import subprocess
import sys
from pathlib import Path

apps_folder = Path("apps")


# -------------------
# Main Registration
# -------------------
def register_subcommand(subparsers):
    def run(args):
        print("\n# ------- Mindoff > Organize ------- #")

        local_apps = _get_local_apps()
        if not local_apps:
            print("❌ No valid apps found in 'apps' directory. Exiting...")
            return

        selected_apps = _select_apps(local_apps)
        paths = [str(apps_folder / app) for app in selected_apps]

        _run_organize_steps(paths)

    parser = subparsers.add_parser(
        "organize",
        help="Run all organize steps (init + pyformat)",
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


def _select_apps(local_apps):
    while True:
        print("\n🔢 Select app(s) to organize:")
        for i, app in enumerate(local_apps, 1):
            print(f"{i}. {app}")

        choice = input(
            "Enter choice of 'number' (space-separated, leave blank for ALL): "
        ).strip()

        if not choice:
            return local_apps

        indexes = [
            int(i)
            for i in choice.split()
            if i.isdigit() and 1 <= int(i) <= len(local_apps)
        ]

        if not indexes:
            print("❌ Invalid selection. Please try again.")
            continue

        return [local_apps[i - 1] for i in indexes]


def _run_organize_steps(paths):
    commands = [
        "organizeinit",
        "organizepyformat",
    ]

    for command in commands:
        print(f"\n⚙️  Running {command}...")
        subprocess.run(
            [sys.executable, "mindoff.py", command, *paths],
            check=True,
        )
