import subprocess
import sys
from pathlib import Path

from tqdm import tqdm


class DjangoCodeOrganizer:
    def __init__(self, targets=None, dry_run=False):
        self.targets = targets or []
        self.dry_run = dry_run
        self.altered_files: list[Path] = []

    def run(self):
        files = self._resolve_files()

        if not files:
            print("No Python files found to organize.")
            return

        for f in tqdm(files, desc="Organizing files", unit="file"):
            if self.dry_run:
                self.altered_files.append(f)
            else:
                if self._organize_file(f):
                    self.altered_files.append(f)

        if self.dry_run:
            print("\n[DRY RUN] Files that would be altered:")
        else:
            print("\nFiles altered:")

        for f in self.altered_files:
            print(f" - {f}")

    def _resolve_files(self):
        """Resolve dotted paths (apps/files) into actual .py files"""
        if not self.targets:
            return list(Path.cwd().rglob("*.py"))

        files: list[Path] = []
        for target in self.targets:
            resolved = self._resolve_target(target)
            if resolved:
                files.extend(resolved)
            else:
                print(f"⚠️ No match found for {target}")
        return files

    def _resolve_target(self, target: str) -> list[Path] | None:
        """Resolve a single dotted path into one or more .py files"""
        path = target.replace(".", "/")
        candidates = [Path.cwd() / path, Path.cwd() / "apps" / path]

        for base in candidates:
            py_file = base.with_suffix(".py")
            folder = base if base.is_dir() else None

            if py_file.exists() and folder:
                raise ValueError(
                    f"⚠️ Ambiguous target '{target}': both '{py_file.name}' and '{folder.name}/' exist in {base.parent}"
                )
            if folder:
                return list(folder.rglob("*.py"))
            if py_file.exists():
                return [py_file]

        return None

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
        DjangoCodeOrganizer(targets=args.targets, dry_run=args.dry_run).run()

    parser = subparsers.add_parser(
        "sanitizeimport",
        help="Organize Python code (imports, ordering, formatting).",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help=(
            "Target apps/folders/files using dotted path. Examples:\n"
            "  blog → all files in blog app\n"
            "  blog.models → blog/models.py\n"
            "  blog.utils → blog/utils.py or blog/utils/ (error if both exist)\n"
            "  blog.utils.file1 → blog/utils/file1.py\n"
            "If empty, runs for all apps."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show which files would be altered, do not modify.",
    )
    parser.set_defaults(handler=_organize)
