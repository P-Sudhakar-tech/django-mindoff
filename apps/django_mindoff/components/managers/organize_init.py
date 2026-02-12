import os
from django.core.management.base import CommandError

# ======== CONSTANTS =======
EXCLUDED_DIR = ["__pycache__"]


# ======== CLASSES =======
class Initorganizer:
    """Recursively adds an __init__.py file to every folder under given paths."""

    def __init__(self, paths: list[str]):
        self.paths = paths

    def run(self) -> None:
        if not self.paths:
            raise CommandError("No paths provided.")

        for path in self.paths:
            if not isinstance(path, str) or not path.strip():
                raise CommandError("Provided path must be a non-empty string.")
            if not os.path.exists(path):
                raise CommandError(f"Path does not exist → {path}")

            print(f"\nProcessing path: {path}")
            created_files = 0
            for root, dirs, files in os.walk(path):
                # Exclude unwanted directories
                dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR]

                init_path = os.path.join(root, "__init__.py")
                if "__init__.py" not in files:
                    relative_path = os.path.relpath(init_path, path)
                    with open(init_path, "w", encoding="utf-8") as f:
                        f.write(f"# {os.path.join(path, relative_path)}\n")
                    print(f"[OK] Created: {init_path}")
                    created_files += 1
                else:
                    print(f"[ACTION] Exists:  {init_path}, skipping.")

            if created_files == 0:
                print("[OK] No new __init__.py files needed.")


# ======== FUNCTIONS =======
def register_subcommand(subparsers):
    def _organize_init(args):
        Initorganizer(args.paths).run()

    parser = subparsers.add_parser(
        "organizeinit",
        help="Add __init__.py to all folders recursively under the given path(s)",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Target root path(s) to initialize packages",
    )
    parser.set_defaults(handler=_organize_init)
