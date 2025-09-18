import os

from django.core.management.base import CommandError

# ======== CONSTANTS =======
EXCLUDED_DIR = ["__pycache__"]


# ======== CLASSES =======
# C1. Recursively adds an __init__.py file to every folder under `path`,
class InitSanitizer:
    def __init__(self, path: str = "src"):
        self.path = path

    def run(self) -> None:
        if not isinstance(self.path, str) or not self.path.strip():
            raise CommandError("Provided path must be a non-empty string.")
        if not os.path.exists(self.path):
            raise CommandError(f"Path does not exist → {self.path}")
        for root, dirs, files in os.walk(self.path):
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIR]
            if "__init__.py" not in files:
                init_path = os.path.join(root, "__init__.py")
                relative_path = os.path.relpath(init_path, self.path)
                with open(init_path, "w", encoding="utf-8") as f:
                    f.write(f"# {os.path.join(self.path, relative_path)}\n")
                print(f"✅ Created: {init_path}")
            else:
                print(f"✔️ Exists:  {os.path.join(root, '__init__.py')}")


# ======== FUNCTIONS =======
# F1. Command Entry Point -- Registers the command into the CLI.
def register_subcommand(subparsers):
    def _sanitize_init(args):
        InitSanitizer(args.path).run()

    parser = subparsers.add_parser(
        "sanitizeinit",
        help="Add __init__.py to all folders recursively under the given path",
    )
    parser.add_argument("path", help="Target root path to initialize packages")
    parser.set_defaults(handler=_sanitize_init)


# ======== SUB-FUNCTIONS =======
