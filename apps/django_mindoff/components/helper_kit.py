import importlib
import inspect
import os
import re
import traceback
from pathlib import Path
from types import SimpleNamespace

from django.apps import apps
from django.conf import settings

from ._helper_kit import file_guardian
import sys
from django.urls import get_resolver

# ------------------------
# String Manipulation Helpers
# ------------------------


def safe_print(msg: str):
    encoding = sys.stdout.encoding or "utf-8"
    try:
        # Try printing as-is
        print(msg)
    except UnicodeEncodeError:
        # Fallback: replace unsupported chars with ASCII equivalents
        cleaned = msg.encode(encoding, "replace").decode(encoding)
        print(cleaned)


def pascal_to_snake(name: str) -> str:
    """Convert PascalCase to snake_case."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def get_app_module_path(app_name: str) -> str:
    def _impl(app_name: str) -> str:
        for path in settings.INSTALLED_APPS:
            if path.rsplit(".", 1)[-1] == app_name:
                try:
                    importlib.import_module(path)
                    return path
                except ImportError:
                    continue
        raise ValueError(f"App '{app_name}' not found in INSTALLED_APPS.")

    return _impl(app_name)


def get_current_app_name():
    """Try to detect the Django app name from the calling file path."""
    caller_file = inspect.stack()[2].filename
    caller_file = os.path.abspath(caller_file)

    for app_config in apps.get_app_configs():
        if os.path.commonpath(
            [caller_file, os.path.abspath(app_config.path)]
        ) == os.path.abspath(app_config.path):
            return app_config.label

    raise ValueError("No app name could be resolved from current file location.")


def get_exact_traceback(skip: int | None = None) -> str:
    stack = inspect.stack()
    project_dirs = getattr(settings, "VALIDATION_TRACEBACK_DIRS", ["apps", "config"])
    project_dirs = [os.path.abspath(str(Path(d))) for d in project_dirs]
    valid_frames = []
    for frame_info in stack:
        filename = os.path.abspath(frame_info.filename)
        if any(filename.startswith(proj_dir + os.sep) for proj_dir in project_dirs):
            valid_frames.append(frame_info)

    if not valid_frames:
        return "No project frame found in traceback."

    if skip is None:
        summaries = [
            traceback.extract_stack(frame_info.frame, limit=1)[0]
            for frame_info in valid_frames
        ]
        return "".join(traceback.format_list(summaries))
    else:
        idx = min(skip, len(valid_frames) - 1)
        chosen_frame = valid_frames[idx]
        tb_summary = traceback.extract_stack(chosen_frame.frame, limit=1)
        return "".join(traceback.format_list(tb_summary))


def get_api_class_from_url_name(url_name: str):
    resolver = get_resolver()
    for pattern in resolver.url_patterns:
        if getattr(pattern, "name", None) == url_name:
            callback = pattern.callback
            # Class-based view
            if hasattr(callback, "view_class"):
                return callback.view_class
            # Function-based view (unsupported for Mindoff)
            raise TypeError(f"URL '{url_name}' is not a class-based view")
    raise LookupError(f"No URL found with name '{url_name}'")


mo_helper_kit = SimpleNamespace(
    safe_print=safe_print,
    pascal_to_snake=pascal_to_snake,
    get_current_app_name=get_current_app_name,
    get_exact_traceback=get_exact_traceback,
    file_guardian=file_guardian.file_guardian,
    get_api_class_from_url_name=get_api_class_from_url_name,
)
