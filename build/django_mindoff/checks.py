from django.core.checks import Error, register
from django.urls import get_resolver
from django.urls.resolvers import URLResolver, URLPattern
from django.core.exceptions import ImproperlyConfigured
from django.apps import apps as django_apps
from inspect import isclass
import inspect
import importlib
import pkgutil
import sys

from .components.api_kit import MindoffAPIMixin


@register()
def check_mindoff_api_configs(app_configs, **kwargs):
    errors = []

    for app_config in django_apps.get_app_configs():
        apis_dir = (
            app_config.path and __import__("pathlib").Path(app_config.path) / "apis"
        )
        if not apis_dir or not apis_dir.is_dir():
            continue

        # Walk every .py file under apis/ and import it fresh
        package_name = f"{app_config.name}.apis"
        for finder, module_name, _ in pkgutil.walk_packages(
            path=[str(apis_dir)],
            prefix=f"{package_name}.",
            onerror=lambda name: None,
        ):
            # Force a fresh import — evict any cached version first
            sys.modules.pop(module_name, None)
            try:
                module = importlib.import_module(module_name)
            except Exception:
                continue

            for attr_name in dir(module):
                obj = getattr(module, attr_name, None)
                if (
                    isclass(obj)
                    and issubclass(obj, MindoffAPIMixin)
                    and obj is not MindoffAPIMixin
                ):
                    _validate_view_class(obj, errors)

    return errors


def _validate_view_class(view_class, errors):
    try:
        instance = view_class()
        instance.validate_api_configuration()
    except Exception as exc:
        error_code = getattr(exc, "code", "API_CONFIG_ERR")
        errors.append(
            Error(
                f"API Configuration Error in {view_class.__name__}: {str(exc)}",
                hint="Check validate_api_configuration() in your API class.",
                obj=view_class,
                id=f"django_mindoff.{error_code}",
            )
        )
