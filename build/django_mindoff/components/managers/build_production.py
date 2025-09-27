import shutil
from pathlib import Path

from ..helper_kit import mo_helper_kit


class DjangoAppPackager:
    REQUIRED_FILES = ["pyproject.toml", "README.md", "LICENSE"]

    def __init__(self):
        self.project_root = Path.cwd()
        self.apps_dir = self.project_root / "apps"
        self.build_dir = self.project_root / "build"

    def _validate_required_files(self) -> bool:
        """Ensure required files exist at root level."""
        missing = [
            f for f in self.REQUIRED_FILES if not (self.project_root / f).exists()
        ]
        if missing:
            print(f"❌ Missing required file(s): {', '.join(missing)}")
            return False
        return True

    def _prepare_build_dir(self):
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir()

    def _copy_required_files(self):
        for f in self.REQUIRED_FILES:
            shutil.copy2(self.project_root / f, self.build_dir / f)

    def _get_eligible_apps(self) -> list[str]:
        """Pick apps with apps.py only."""
        return [
            d.name
            for d in self.apps_dir.iterdir()
            if d.is_dir() and (d / "apps.py").exists()
        ]

    def _copy_apps(self, eligible_apps: list[str]):
        for app_name in eligible_apps:
            src = self.apps_dir / app_name
            dest = self.build_dir / app_name
            shutil.copytree(src, dest)
            print(f"📦 Copied app: {app_name}")

    @mo_helper_kit.file_guardian
    def run(self):
        if not self._validate_required_files():
            return
        self._prepare_build_dir()
        self._copy_required_files()

        eligible_apps = self._get_eligible_apps()
        if not eligible_apps:
            print("⚠️ No eligible apps found.")
            return

        self._copy_apps(eligible_apps)
        print(f"✅ Build completed at {self.build_dir}")


# ======== FUNCTIONS =======
def register_subcommand(subparsers):
    def _build_package(args):
        try:
            DjangoAppPackager().run()
        except Exception as e:
            print(f"❌ Error during build: {e}")

    parser = subparsers.add_parser(
        "build",
        help="Build project for production or package it as pip-style package",
    )
    parser.add_argument(
        "--package",
        action="store_true",
        help="Build project as pip-style package into build/ folder.",
    )
    parser.set_defaults(handler=_build_package)
