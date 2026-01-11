import os
import ast
from types import ModuleType
import importlib
from ..helper_kit import mo_helper_kit
import black


class ApiOutlineCreator:
    """
    CLI helper to generate API_OUTLINES for given local apps.
    Writes to <app>/components/__api_outlines__.py
    """

    def __init__(self, app_names: list[str] = None):
        self.app_names = app_names or []

    @mo_helper_kit.file_guardian
    def run(self):
        if not self.app_names:
            self.app_names = self._get_local_apps_from_settings()

        for app_name in self.app_names:
            try:
                module = importlib.import_module(app_name)
                app_path = os.path.dirname(module.__file__)
            except Exception:
                print(f"Skipping '{app_name}': not defined in settings as a local app")
                continue

            outlines = {}
            candidate_files = self._collect_candidate_files(app_path)

            for filepath in candidate_files:
                self._process_file(filepath, outlines)

            output_path = os.path.join(app_path, "components", "__api_outlines__.py")
            if outlines:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                content = (
                    "# AUTO-GENERATED FILE BY DJANGO-MINDOFF. DO NOT EDIT.\n\n"
                    f"API_OUTLINES = {repr(outlines)}\n"
                )
                formatted_content = black.format_file_contents(
                    content, fast=False, mode=black.FileMode()
                )
                with open(output_path, "w") as f:
                    f.write(formatted_content)
                print(f"API Outline generated for app '{app_name}'")
            else:
                if os.path.exists(output_path):
                    os.remove(output_path)
                print(
                    f"Skipping '{app_name}': no valid Django-Mindoff API found in views.py or _views directory"
                )

    # ======== First-level helper ========
    def _get_local_apps_from_settings(self):
        """
        Import the project settings module without initializing Django
        and return apps starting with 'apps.'
        """
        settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings")
        settings_mod = importlib.import_module(settings_module)
        installed_apps = getattr(settings_mod, "INSTALLED_APPS", [])
        return [app for app in installed_apps if app.startswith("apps.")]

    def _collect_candidate_files(self, app_path: str):
        files = []
        views_file = os.path.join(app_path, "views.py")
        if os.path.exists(views_file):
            files.append(views_file)
        views_dir = os.path.join(app_path, "_views")
        if os.path.isdir(views_dir):
            for f in os.listdir(views_dir):
                if f.endswith(".py"):
                    files.append(os.path.join(views_dir, f))
        return files

    def _process_file(self, filepath: str, outlines: dict, visited_files=None):
        if visited_files is None:
            visited_files = set()
        if filepath in visited_files:
            return
        visited_files.add(filepath)

        with open(filepath, "r") as f:
            tree = ast.parse(f.read(), filename=filepath)

        # collect all functions (top-level + inside classes)
        functions = self._collect_functions(tree)

        # collect imports
        imports = self._collect_imports(tree, os.path.dirname(filepath))

        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not self.__is_mindoff_class(node):
                continue

            run_method = next(
                (
                    fn
                    for fn in node.body
                    if isinstance(fn, ast.FunctionDef) and fn.name == "run"
                ),
                None,
            )
            if run_method:
                self.__add_class_milestones(
                    node, run_method, functions, imports, outlines, visited_files
                )

    def _collect_functions(self, tree: ast.AST):
        functions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions[node.name] = node
        return functions

    def _collect_imports(self, tree: ast.AST, base_dir: str):
        imports = {}
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                module_path = node.module.replace(".", "/") + ".py"
                full_path = os.path.join(base_dir, module_path)
                for alias in node.names:
                    imports[alias.asname or alias.name] = full_path
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module_path = alias.name.replace(".", "/") + ".py"
                    full_path = os.path.join(base_dir, module_path)
                    imports[alias.asname or alias.name] = full_path
        return imports

    def __add_class_milestones(
        self, class_node, run_method, functions, imports, outlines, visited_files
    ):
        milestones = self.__extract_progress_from_function(
            run_method, functions, imports, visited_files
        )
        if not milestones:
            milestones = ["start", "end"]

        step = 100 // len(milestones)
        outlines[class_node.name] = [
            {
                "name": m if isinstance(m, str) else m["name"],
                "start": i * step,
                "end": (i + 1) * step if i < len(milestones) - 1 else 100,
            }
            for i, m in enumerate(milestones)
        ]

    def __is_mindoff_class(self, node: ast.ClassDef):
        return any(
            (isinstance(base, ast.Name) and base.id == "MindoffAPIMixin")
            or (isinstance(base, ast.Attribute) and base.attr == "MindoffAPIMixin")
            for base in node.bases
        )

    def __extract_progress_from_function(
        self, fn_node, functions, imports, visited_files, visited=None
    ):
        if visited is None:
            visited = set()
        if fn_node.name in visited:
            return []
        visited.add(fn_node.name)

        milestones = []
        extractor = self.__ProgressExtractor()
        extractor.visit(fn_node)
        milestones.extend(extractor.milestones)

        for fn_name in extractor.called_functions:
            # local function
            if fn_name in functions:
                milestones.extend(
                    self.__extract_progress_from_function(
                        functions[fn_name], functions, imports, visited_files, visited
                    )
                )
            # imported function
            elif fn_name in imports and os.path.exists(imports[fn_name]):
                self._process_file(
                    imports[fn_name], {}, visited_files
                )  # parse external file
                # after parsing, re-call extraction if found
                # (need a shared registry of functions across files)
        return milestones

    class __ProgressExtractor(ast.NodeVisitor):
        def __init__(self):
            self.milestones = []
            self.called_functions = []

        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == "update_progress":
                label, weight = self._extract_label_and_weight(node)
                self.milestones.append({"name": label or "", "weight": weight})
            elif isinstance(node.func, ast.Name):
                self.called_functions.append(node.func.id)
            self.generic_visit(node)

        def _extract_label_and_weight(self, node):
            """Extract label and weight from update_progress call"""
            label = None
            weight = 1
            if node.args and isinstance(node.args[0], ast.Str):
                label = node.args[0].s
            for kw in node.keywords:
                if kw.arg == "label" and isinstance(kw.value, ast.Str):
                    label = kw.value.s
                elif kw.arg == "weight" and isinstance(kw.value, ast.Constant):
                    w = int(kw.value.value)
                    if w < 1 or w > 100:
                        w = 1
                    weight = w
            return label, weight


# ======== CLI HOOK ========
def register_subcommand(subparsers):
    def _create_api_outline(args):
        ApiOutlineCreator(app_names=args.app_names).run()

    parser = subparsers.add_parser(
        "createapioutline", help="Generate API_OUTLINES for local apps"
    )
    parser.add_argument(
        "app_names",
        nargs="*",
        help="Optional: one or more app names (space-separated). Leave blank to run for all local apps",
    )
    parser.set_defaults(handler=_create_api_outline)
