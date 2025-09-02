import shutil
from pathlib import Path
from typing import List
from apps.django_mindoff.components.helper_kit import mo_helper_kit


# ======== CLASSES =======
# Add Classes here
class DjangoProjectDeleter:
    def __init__(self, dry_run: bool = False, delete_all: bool = False):
        self.project_root = Path.cwd()
        self.default_exclude = {".git", ".venv", ".gitignore", "README.md", ".env.bak"}
        self.exclude_files = {"automate.py", "run_env.sh", "run_env.bat"}
        self.project_artifacts = [
            "config",
            "apps",
            "templates",
            ".env",
            ".gitignore",
            "pytest.ini",
            "db.sqlite3",
            "manage.py",
            "mindoff.py",
            "README.md",
            ".venv",
            ".git",
        ]
        self.dry_run = dry_run
        self.delete_all = delete_all
        self.deleted: List[Path] = []
        self.skipped: List[Path] = []
        self.to_delete: List[Path] = []

    def _identify_targets(self):
        for item in self.project_artifacts:
            path = self.project_root / item
            if not path.exists():
                continue
            if not self.delete_all and path.name in self.default_exclude:
                self.skipped.append(path)
                continue
            if path.name in self.exclude_files:
                self.skipped.append(path)
                continue
            self.to_delete.append(path)

    def _print_dry_run(self):
        print("\n🚫 Dry Run Mode — Planned Deletions:")
        for path in self.to_delete:
            print(f"  • {path.relative_to(self.project_root)}")
        print("\n✅ Dry run complete. No files deleted.")

    def _confirm_deletion(self) -> bool:
        print("\n⚠️ The following will be deleted:")
        for path in self.to_delete:
            print(f"  • {path.relative_to(self.project_root)}")
        confirm = input(
            "\nAre you sure you want to proceed? This cannot be undone. (y/n): "
        ).lower()
        return confirm == "y"

    def _perform_deletion(self):
        for path in self.to_delete:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                self.deleted.append(path)
            except Exception as e:
                print(f"⚠️ Failed to delete {path}: {e}")

    def _report_summary(self):
        if self.deleted:
            print("\n✅ Deleted:")
            for p in self.deleted:
                print(f"  • {p.relative_to(self.project_root)}")
        if self.skipped:
            print("\n⏭️ Skipped:")
            for p in self.skipped:
                print(f"  • {p.relative_to(self.project_root)}")

    @mo_helper_kit.file_guardian
    def run(self):
        print("\n🗑️ Starting project cleanup...")
        self._identify_targets()

        if self.dry_run:
            self._print_dry_run()
            return

        if not self._confirm_deletion():
            print("❌ Aborted by user.")
            return

        self._perform_deletion()
        self._report_summary()


# ======== FUNCTIONS =======
# Add Functions here
# F1. Command Entry Point -- Registers the command into the CLI.
def register_subcommand(subparsers):
    def _delete_project(args):
        DjangoProjectDeleter(dry_run=args.dry_run, delete_all=args.all).run()

    parser = subparsers.add_parser(
        "deleteproject", help="Deletes the Current Django Project."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions without making any changes",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Delete all project artificates related to mindoff",
    )
    parser.set_defaults(handler=_delete_project)
