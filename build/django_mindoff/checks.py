from django.core.checks import Error, register
from django.urls import get_resolver
from django.urls.resolvers import URLResolver, URLPattern
from django.core.exceptions import ImproperlyConfigured
from inspect import isclass
from .components.api_kit import MindoffAPIMixin


@register()
def check_mindoff_api_configs(app_configs, **kwargs):
    errors = []
    resolver = get_resolver()
    try:
        url_patterns = resolver.url_patterns
        flat_patterns = _flatten_patterns(url_patterns)
    except Exception:
        # If URLs aren't ready yet, skip this check to avoid circularity
        return []

    for pattern in flat_patterns:
        callback = getattr(pattern, "callback", None)
        if not callback:
            continue

        view_class = getattr(callback, "view_class", None)
        if isclass(view_class) and issubclass(view_class, MindoffAPIMixin):
            try:
                instance = view_class()
                instance.validate_api_configuration()
            except Exception as exc:
                errors.append(
                    Error(
                        f"API Configuration Error in {view_class.__name__}: {str(exc)}",
                        hint="Check the validate_api_configuration method in your view.",
                        obj=view_class,
                        id=f"django_mindoff.{exc.code}",
                    )
                )
    return errors


def _flatten_patterns(patterns):
    flat = []
    for pattern in patterns:
        if isinstance(pattern, URLResolver):
            try:
                flat.extend(_flatten_patterns(pattern.url_patterns))
            except (ImportError, ImproperlyConfigured):
                continue
        elif isinstance(pattern, URLPattern):
            flat.append(pattern)
    return flat
