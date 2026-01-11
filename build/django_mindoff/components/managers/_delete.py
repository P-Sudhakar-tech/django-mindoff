import os
import sys
import subprocess


# -------------------
# Helper Function
# -------------------
def _delete_apps_via_subprocess():
    """Handle interactive app deletion and call subprocess."""
    apps_dir = os.path.join(os.getcwd(), "apps")
    if not os.path.exists(apps_dir):
        print("No 'apps' directory found. Exiting...")
        return

    app_names = [
        d
        for d in os.listdir(apps_dir)
        if os.path.isdir(os.path.join(apps_dir, d))
        and os.path.exists(os.path.join(apps_dir, d, "__init__.py"))
    ]

    if not app_names:
        print("No valid apps found in 'apps' directory. Exiting...")
        return

    print("\nSelect app(s) to delete:")
    for idx, app in enumerate(app_names, start=1):
        print(f"{idx}. {app}")

    raw_choices = (
        input("\nEnter choice of number(s) (space separated): ").strip().split()
    )
    chosen_apps = []
    for c in raw_choices:
        if c.isdigit() and 1 <= int(c) <= len(app_names):
            chosen_apps.append(app_names[int(c) - 1])
        elif c in app_names:
            chosen_apps.append(c)
        else:
            print(f"Invalid choice: {c}. Exiting...")

    if not chosen_apps:
        print("No valid apps selected. Exiting...")
        return

    subprocess.run([sys.executable, "mindoff.py", "deleteapp"] + chosen_apps)


# -------------------
# Main Registration
# -------------------
def register_subcommand(subparsers):
    def run(args):
        options = {
            "1": ("app", "deleteapp"),
        }
        print("\n# ------- Mindoff > Delete ------- #")
        print("What would you like to delete ?")
        for num, (label, _) in options.items():
            print(f"{num}. {label}")

        choice = input("\nEnter choice of number: ").strip().lower()

        # Resolve choice inline (no extra sub-function)
        command = None
        if choice in options:
            command = options[choice][1]
        else:
            match = [cmd for _, (lbl, cmd) in options.items() if lbl == choice]
            if match:
                command = match[0]

        if not command:
            print("Invalid choice. Exiting...")
            return

        if command == "deleteapp":
            _delete_apps_via_subprocess()

    parser = subparsers.add_parser("delete", help="Guided interactive removal")
    parser.set_defaults(handler=run)
