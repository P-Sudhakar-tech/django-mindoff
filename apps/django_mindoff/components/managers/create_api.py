import re
from pathlib import Path

from ..helper_kit import mo_helper_kit

TEMPLATE_PATH = Path(__file__).parent / "resources" / "api_class.py"
TEST_TEMPLATE_PATH = Path(__file__).parent / "resources" / "test_api_class.py"


class DjangoApiCreator:
    def __init__(
        self, api_path: str, url_paths: list[str] = None, base_path: Path = None
    ):
        self.api_path = api_path
        self.base_path = Path(base_path) if base_path else Path.cwd() / "apps"
        self.url_paths = url_paths or []
        self.original_app_name = None
        self.raw_api = None
        self.normalized_app_name = None
        self.app = None
        self.api_function_name = None
        self.api_class_name = None

    def _normalize_app_name(self, dotted_path: str) -> str:
        if self.base_path != Path.cwd() / "apps":
            return dotted_path.lower()
        if not dotted_path.startswith("apps."):
            dotted_path = f"apps.{dotted_path}"
        app_names = dotted_path.split(".")
        if len(app_names) != 2:
            raise ValueError(f"Invalid App Name or Path: '{dotted_path}'")
        normalized = [app_names[0]] + [p.lower() for p in app_names[1:]]
        if any(not p for p in normalized):
            raise ValueError(f"Invalid path '{dotted_path}'")
        return ".".join(normalized)

    def _normalize_api_name(self, raw: str):
        if not re.match(r"^[a-z_]+$", raw):
            raise ValueError(
                f"Invalid API name: '{raw}'. Only lowercase letters and underscores allowed."
            )

        snake = raw
        pascal = re.sub(r"(?:^|_)([a-z])", lambda m: m.group(1).upper(), snake)
        class_name = pascal + "APIView"
        return snake, class_name

    def _normalize_url(self, url: str) -> str:
        url = url.strip()
        if url.startswith("/"):
            url = url[1:]
        if not url.endswith("/"):
            url += "/"
        # Validate pattern parameters (e.g., <int:name>)
        if re.search(r"<[^>:]+>", url):
            raise ValueError(
                f"Invalid URL pattern '{url}': use format like <int:id>, <slug:name>"
            )
        if not re.match(r"^[\w\-/<>:]+/$", url):
            raise ValueError(f"Invalid characters in URL pattern: '{url}'")
        return url

    def _parse_input(self):
        try:
            self.original_app_name, self.raw_api = self.api_path.split("/")
        except ValueError:
            raise ValueError("API path must be in format <app_name>/<api_name>")
        self.normalized_app_name = self._normalize_app_name(self.original_app_name)
        self.app = self.normalized_app_name
        words = self.raw_api.split("_")
        self.api_function_name = self.raw_api
        pascal = "".join(w.capitalize() for w in words)
        self.api_class_name = f"{pascal}APIView"
        self.api_human_name = " ".join(w.capitalize() for w in words)

    def _copy_template_and_replace(self):
        app_dir = self.base_path / self.original_app_name
        view_path = app_dir / "views.py"
        if not TEMPLATE_PATH.exists():
            raise FileNotFoundError(f"API template not found at {TEMPLATE_PATH}")

        content = TEMPLATE_PATH.read_text()
        replaced = re.sub(r"class\s+\w+\s*\(", f"class {self.api_class_name}(", content)
        if not replaced or f"class {self.api_class_name}(" not in replaced:
            raise ValueError("Could not replace class name in template.")
        replaced = replaced.replace(
            "{{API_HUMAN_NAME}}",
            self.api_human_name,
        )
        if "{{API_HUMAN_NAME}}" in replaced:
            raise ValueError("Template is missing API_HUMAN_NAME replacement.")
        api_url_name = f"{self.original_app_name}__{self.api_function_name}"
        replaced = replaced.replace(
            "{{API_URL_NAME}}",
            api_url_name,
        )
        import_lines, code_lines = self._extract_imports_and_code(replaced)

        if view_path.exists():
            original = view_path.read_text()
            if f"class {self.api_class_name}(" in original:
                raise FileExistsError(
                    f"API '{self.raw_api}' already exists under app '{self.original_app_name}'"
                )
            existing_lines = set(original.splitlines())
            missing_imports = [
                line for line in import_lines if line not in existing_lines
            ]
            final_lines = original.rstrip().splitlines()
            insert_at = 0
            for i, line in enumerate(final_lines):
                if line.strip() and not (
                    line.strip().startswith("import") or line.strip().startswith("from")
                ):
                    insert_at = i
                    break

            new_view_content = (
                final_lines[:insert_at]
                + missing_imports
                + final_lines[insert_at:]
                + ["", *code_lines, ""]
            )
            view_path.write_text("\n".join(new_view_content))
        else:
            view_path.parent.mkdir(parents=True, exist_ok=True)
            full_content = "\n".join(import_lines + ["", *code_lines, ""])
            view_path.write_text(full_content)

    def _copy_test_template_and_replace(self):
        tests_dir = self.base_path / self.original_app_name / "tests"
        test_path = tests_dir / "test_views.py"
        if not TEST_TEMPLATE_PATH.exists():
            raise FileNotFoundError(f"Test template not found at {TEST_TEMPLATE_PATH}")

        content = TEST_TEMPLATE_PATH.read_text()
        replaced = re.sub(
            r"class\s+\w+\s*\(",
            f"class Test{self.api_class_name}(",
            content,
        )
        if not replaced or f"class Test{self.api_class_name}(" not in replaced:
            raise ValueError("Could not replace test class name in template.")

        api_url_name = f"{self.original_app_name}__{self.api_function_name}"
        replaced = replaced.replace(
            "{{API_URL_NAME}}",
            api_url_name,
        )
        import_lines, code_lines = self._extract_imports_and_code(replaced)

        if test_path.exists():
            original = test_path.read_text()
            if f"class Test{self.api_class_name}(" in original:
                raise FileExistsError(
                    f"Test for API '{self.raw_api}' already exists under app '{self.original_app_name}'"
                )
            existing_lines = set(original.splitlines())
            missing_imports = [
                line for line in import_lines if line not in existing_lines
            ]
            final_lines = original.rstrip().splitlines()
            insert_at = 0
            for i, line in enumerate(final_lines):
                if line.strip() and not (
                    line.strip().startswith("import") or line.strip().startswith("from")
                ):
                    insert_at = i
                    break
            new_test_content = (
                final_lines[:insert_at]
                + missing_imports
                + final_lines[insert_at:]
                + ["", *code_lines, ""]
            )
            test_path.write_text("\n".join(new_test_content))
        else:
            tests_dir.mkdir(parents=True, exist_ok=True)
            full_content = "\n".join(import_lines + ["", *code_lines, ""])
            test_path.write_text(full_content)

    def _extract_imports_and_code(self, content: str):
        import_lines = []
        code_lines = []
        for line in content.strip().splitlines():
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                import_lines.append(line.strip())
            else:
                code_lines.append(line)
        return import_lines, code_lines

    def _update_urls(self):
        urls_path = self.base_path / self.original_app_name / "urls.py"
        if not urls_path.exists():
            raise FileNotFoundError(f"urls.py not found at {urls_path}")

        text = urls_path.read_text()
        existing_patterns = set(re.findall(r"path\(\s*['\"](.+?)['\"]", text))
        existing_names = set(re.findall(r"name=['\"](.+?)['\"]", text))
        existing_names_lower = {name.lower() for name in existing_names}

        if not self.url_paths:
            default_url = f"{self.api_function_name}/"
            self.url_paths = [default_url]

        pattern = re.compile(r"(urlpatterns\s*=\s*\[.*?)(\])", re.DOTALL)
        match = pattern.search(text)
        if not match:
            raise ValueError("Could not find urlpatterns list in urls.py")

        insert_lines = []
        for url in self.url_paths:
            norm_url = self._normalize_url(url)

            if norm_url in existing_patterns:
                raise FileExistsError(
                    f"URL pattern '{norm_url}' already exists in urls.py"
                )
            route_name = self._generate_route_name(
                norm_url, existing_names, existing_names_lower
            )
            insert_lines.append(
                f"    path('{norm_url}', views.{self.api_class_name}.as_view(), name='{route_name}'),"
            )

        new_text = pattern.sub(r"\1" + "\n".join(insert_lines) + r"\n\2", text)
        urls_path.write_text(new_text)

    def _generate_route_name(
        self, url: str, existing_names: set[str], existing_names_lower: set[str]
    ) -> str:
        # ✅ Always use app_name__api_name (ignore url details)
        route_name = f"{self.original_app_name}__{self.api_function_name}"

        if route_name in existing_names:
            raise FileExistsError(f"URL name '{route_name}' already exists in urls.py")
        if route_name.lower() in existing_names_lower:
            print(
                f"[WARNING] Route name '{route_name}' may collide with an existing name if case is ignored."
            )
        return route_name

    @mo_helper_kit.file_guardian
    def run(self):
        self._parse_input()
        self._copy_template_and_replace()
        self._copy_test_template_and_replace()
        self._update_urls()


# ======== CLI HOOK ========
def register_subcommand(subparsers):
    def _create_api(args):
        DjangoApiCreator(api_path=args.api_path, url_paths=args.url).run()

    parser = subparsers.add_parser(
        "createapi", help="Create Django API view class and route"
    )
    parser.add_argument("api_path", help="API path in format <app_name>/<api_name>")
    parser.add_argument(
        "--url",
        action="extend",
        nargs="+",
        help="One or more URL patterns (e.g., 'api/<int:user_id>/')",
    )
    parser.set_defaults(handler=_create_api)
