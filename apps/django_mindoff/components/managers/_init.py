import os
import re
import shutil
import subprocess
from pathlib import Path

from ..helper_kit import mo_helper_kit


# ======== CLASSES =======
class DjangoProjectCreator:
    def __init__(self, dry_run: bool = False, apps_dir_name="apps", venv_name=".venv"):
        self.project_root = Path.cwd()
        self.dry_run = dry_run
        self.apps_dir_name = apps_dir_name
        self.app_dir_path = self.project_root / apps_dir_name
        self.config_dir = self.project_root / "config"
        self.settings_path = self.config_dir / "settings.py"
        self.urls_path = self.config_dir / "urls.py"
        self.venv_name = venv_name
        self.py_cmd = self.project_root / venv_name / "Scripts" / "python"
        self.pip_cmd = self.project_root / venv_name / "Scripts" / "pip"
        self.django_admin_cmd = (
            self.project_root / venv_name / "Scripts" / "django-admin"
        )

    @mo_helper_kit.file_guardian
    def run(self):
        os.chdir(self.project_root)
        print("\n📝 Dry Run Mode:" if self.dry_run else "\n⚙️ Running Project Setup")
        actions = self._plan_actions()
        if self.dry_run:
            for act in actions:
                print(f"  • {act}")
            print("\n✅ Dry run complete. No files modified.")
            return
        self._create_venv()
        self._install_packages()
        self._initialize_django_project()
        self._update_settings()
        self._create_env_file()
        self._update_urls()
        self._create_extra_folders()
        self._write_supporting_files()
        self._initialize_git()
        print("✅ Django project setup complete.")

    def _plan_actions(self):
        actions = [
            f"Create virtual environment in {self.venv_name}",
            "Install: django, djangorestframework, python-decouple, pytest, pytest-django",
        ]
        optional = self._prompt_optional_dependencies()
        if optional:
            actions.append(f"Install optional packages: {', '.join(optional)}")
        actions.extend(
            [
                "Run django-admin startproject config .",
                f"Run manage.py startapp {self.apps_dir_name}",
                "Modify settings.py",
                "Create .env with secret key",
                "Update urls.py",
                "Write templates",
                "Write pytest.ini",
                "Write .gitignore",
                "Initialize Git repository",
            ]
        )
        self.optional_packages = optional
        return actions

    def _prompt_optional_dependencies(self):
        optional = []
        # Sample if required -- if input("Install polars? (y/n): ").lower() == "y":
        #     Sample if required -- optional.extend(["polars", "numpy"])
        return optional

    def _create_venv(self):
        print(f"🔧 Creating virtual environment: {self.venv_name}")
        if not os.path.exists(self.venv_name):
            subprocess.run(["python", "-m", "venv", self.venv_name], check=True)
        else:
            print("✅ Virtual environment exists, skipping creation.")

    def _install_packages(self):
        print("📦 Installing base dependencies...")
        subprocess.run(
            [
                self.pip_cmd,
                "install",
                "django",
                "djangorestframework",
                "python-decouple",
                "pytest",
                "pytest-django",
                "model-bakery",
                "Faker",
                "polars",
                "pandas",
                "numpy",
                "tqdm",
                "autoflake",
                "isort",
                "black",
                "rarfile",
                "py7zr",
                "moviepy",
            ],
            check=True,
        )
        if self.optional_packages:
            print(
                f"📦 Installing optional packages: {', '.join(self.optional_packages)}"
            )
            subprocess.run(
                [self.pip_cmd, "install", *self.optional_packages], check=True
            )
        # Currently Experimental from local, Will be replaced with actual package
        local_package_path = str(Path(__file__).resolve().parent.parent.parent.parent)
        subprocess.run([self.pip_cmd, "install", "-e", local_package_path], check=True)

    def _initialize_django_project(self):
        print("🚀 Starting Django project...")
        subprocess.run(
            [self.django_admin_cmd, "startproject", "config", "."], check=True
        )

    def _update_settings(self):
        print("🛠 Updating settings.py...")
        content = self.settings_path.read_text()
        lines, secret_key = [], ""
        insert_pos = {}
        lines, secret_key, insert_pos = self._extract_secret_and_debug_info(
            content, lines, secret_key, insert_pos
        )
        if "from decouple import config" not in content:
            for i, line in enumerate(lines):
                if "from pathlib import Path" in line:
                    lines.insert(i + 1, "from decouple import config")
                    break
        if "SECRET_KEY" in insert_pos:
            lines.insert(
                insert_pos["SECRET_KEY"], "SECRET_KEY = config('DJANGO_SECRET_KEY')"
            )
        if "DEBUG" in insert_pos:
            lines.insert(
                insert_pos["DEBUG"], "DEBUG = config('DEBUG', cast=bool, default=True)"
            )
        updated = "\n".join(lines)
        updated = self._append_to_list(updated, "INSTALLED_APPS", "rest_framework")
        if "TEMPLATES = [" in updated:
            updated = re.sub(
                r"('DIRS':\s*)\[\s*\]",
                r"\1[os.path.join(BASE_DIR, 'templates')]",
                updated,
            )
            if "import os" not in updated:
                updated = updated.replace(
                    "from pathlib import Path", "import os\nfrom pathlib import Path"
                )

        self.settings_path.write_text(updated)
        self.secret_key = secret_key
        print("✅ settings.py updated.")

    def _extract_secret_and_debug_info(self, content, lines, secret_key, insert_pos):
        for idx, line in enumerate(content.splitlines()):
            if line.strip().startswith("SECRET_KEY"):
                secret_key = line.split("=", 1)[1].strip()
                insert_pos["SECRET_KEY"] = idx
                continue
            if line.strip().startswith("DEBUG"):
                insert_pos["DEBUG"] = idx
                continue
            lines.append(line)
        return lines, secret_key, insert_pos

    def _create_env_file(self):
        print("🔐 Writing .env file...")
        Path(".env").write_text(f"DJANGO_SECRET_KEY={self.secret_key}\nDEBUG=True\n")

    def _update_urls(self):
        print("🌐 Updating urls.py...")
        content = self.urls_path.read_text()
        content = re.sub(r'^\s*"""(?:.|\n)*?"""', "", content).lstrip()
        if "from django.urls import" in content and "include" not in content:
            content = content.replace(
                "from django.urls import ", "from django.urls import include, "
            )
        elif "from django.urls import" not in content:
            content = "from django.urls import path, include\n" + content
        if "from django.views.generic.base import TemplateView" not in content:
            content = "from django.views.generic.base import TemplateView\n" + content
        if "path('', TemplateView.as_view(" not in content:
            content = content.replace(
                "urlpatterns = [",
                "urlpatterns = [\n    path('', TemplateView.as_view(template_name='index.html')),",
            )
        self.urls_path.write_text(content)

    def _create_extra_folders(self):
        print("🧩 Creating apps folder")
        self.app_dir_path.mkdir(exist_ok=True)
        print("🧩 Writing template files")
        templates_src = Path(__file__).parent / "resources" / "html"
        templates_dst = self.project_root / "templates"
        templates_dst.mkdir(exist_ok=True)
        for html_file in templates_src.glob("*.html"):
            shutil.copy(html_file, templates_dst / html_file.name)

    def _write_supporting_files(self):
        print("🧩 Writing mindoff.py CLI runner")
        source = Path(__file__).parent / "resources" / "mindoff.py"
        target = self.project_root / "mindoff.py"
        shutil.copy(source, target)

        print("🧩 Writing pytest.ini")
        source = Path(__file__).parent / "resources" / "pytest.ini"
        target = self.project_root / "pytest.ini"
        shutil.copy(source, target)

        print("🧩 Writing .gitignore")
        source = Path(__file__).parent / "resources" / ".gitignore"
        target = self.project_root / ".gitignore"
        shutil.copy(source, target)

    def _initialize_git(self):
        print("📘 Initializing Git...")
        Path("README.md").touch()
        subprocess.run(["git", "init"])
        subprocess.run(["git", "add", "."])
        subprocess.run(["git", "commit", "-m", "Initial commit"])

    def _append_to_list(self, text, list_name, value):
        lines = text.splitlines()
        new_lines = []
        inside_list = False
        for line in lines:
            new_lines.append(line)
            if line.strip().startswith(f"{list_name} = ["):
                inside_list = True
            elif inside_list and line.strip().endswith("]"):
                indent = " " * (len(line) - len(line.lstrip()) + 4)
                new_lines.insert(-1, f"{indent}'{value}',")
                inside_list = False
        return "\n".join(new_lines)


# ======== FUNCTIONS =======
def register_subcommand(subparsers):
    def _create_project(args):
        DjangoProjectCreator(dry_run=args.dry_run).run()

    parser = subparsers.add_parser("init", help="Initialize a new Django Project.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions without making any changes",
    )
    parser.set_defaults(handler=_create_project)
