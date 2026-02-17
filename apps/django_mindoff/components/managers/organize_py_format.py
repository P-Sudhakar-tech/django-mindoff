import subprocess
import sys
from pathlib import Path
from tqdm import tqdm
from ..helper_kit import mo_helper_kit


class DjangoCodeOrganizer:
    def __init__(self, targets=None):
        self.targets = targets or []
        self.altered_files: list[Path] = []

    @mo_helper_kit.file_guardian
    def run(self):
        files = self._resolve_files()

        if not files:
            print("[ERROR] No Python files found to organize.")
            return

        self._preview_files(files)

        confirm = (
            input(
                "\n❗Proceed with organizing these files? \n "
                "Do this only if all development works are completed in the path (y/N): "
            )
            .strip()
            .lower()
        )
        if confirm != "y":
            print("[ERROR] Aborted.")
            return

        for f in tqdm(files, desc="Organizing files", unit="file"):
            if self._organize_file(f):
                self.altered_files.append(f)

        print("\nFiles altered:")
        for f in self.altered_files:
            print(f" - {f}")

    def _resolve_files(self):
        """Resolve folder paths into all .py files inside."""
        files: list[Path] = []
        for target in self.targets:
            path = Path(target)
            if path.is_dir():
                files.extend(list(path.rglob("*.py")))
            elif path.is_file() and path.suffix == ".py":
                files.append(path)
            else:
                print(f"[ERROR] No valid Python file or folder found at {target}")
        return files

    def _preview_files(self, files: list[Path]):
        """Show files to be altered with progressive display if >10."""
        n = len(files)
        preview_count = 10
        print(f"\n[ACTION] {n} Python files will be organized:")

        for f in files[:preview_count]:
            print(f" - {f}")

        if n > preview_count:
            remaining = n - preview_count
            print(f"   ({remaining} more...)")
            view_more = input("View all files? (y/N): ").strip().lower()
            if view_more == "y":
                for f in files[preview_count:]:
                    print(f" - {f}")

    def _organize_file(self, filepath: Path) -> bool:
        """Run autoflake, isort, and black. Return True if file was changed."""
        before = filepath.read_text(encoding="utf-8")

        # 1. Remove unused imports
        subprocess.run(
            [
                sys.executable,
                "-m",
                "autoflake",
                "--in-place",
                "--remove-all-unused-imports",
                "--remove-unused-variables",
                str(filepath),
            ],
            check=True,
        )

        # 2. Organize imports
        subprocess.run(
            [sys.executable, "-m", "isort", "--overwrite-in-place", str(filepath)],
            check=True,
        )

        # 3. Format with black
        subprocess.run(
            [sys.executable, "-m", "black", str(filepath)],
            check=True,
        )

        after = filepath.read_text(encoding="utf-8")
        return before != after


def register_subcommand(subparsers):
    def _organize(args):
        DjangoCodeOrganizer(targets=args.targets).run()

    parser = subparsers.add_parser(
        "organizepyformat",
        help="Organize Python code (imports, ordering, formatting).",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help=(
            "Target folder(s) or file(s) to organize. Examples:\n"
            "  apps/app_one → all Python files inside app_one\n"
            "  apps/app_two/utils.py → single file\n"
            "If empty, runs for all Python files in current directory."
        ),
    )
    parser.set_defaults(handler=_organize)
