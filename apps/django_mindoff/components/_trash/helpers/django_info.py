import os
import inspect
from django.apps import apps


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
