import subprocess
import sys


def register_subcommand(subparsers):
    def _organize_dealer(args):
        options = {
            "1": ("Add __init__.py", "organizeinit"),
            "2": ("Format .py files", "organizepyformat"),
        }

        print("\n🔢 Select what you want to organize:")
        for num, (name, _) in options.items():
            print(f"{num}. {name}")

        choice = input("\nEnter choice number/name: ").strip()
        if choice not in options and choice not in [v[0] for v in options.values()]:
            print("❌ Invalid choice. Exiting...")
            return

        if choice in options:
            _, command = options[choice]
        else:
            command = [c for _, c in options.values() if _ == choice][0]

        # -------------------
        # GET PATHS FROM USER
        # -------------------
        if command in ("organizepyformat", "organizeinit"):
            prompt_text = (
                "Enter file or directory path(s) (space separated, eg. apps/app_one apps/app_two).\n"
                "Path(s): "
            )
            paths = input(prompt_text).strip()
            if not paths:
                print("❌ No path(s) provided. Exiting...")
                return
            remaining_args = paths.split()

        # -------------------
        # RUN SUBCOMMAND
        # -------------------
        subprocess.run([sys.executable, "mindoff.py", command] + remaining_args)

    parser = subparsers.add_parser("organize", help="Guided interactive organizer")
    parser.set_defaults(handler=_organize_dealer)
