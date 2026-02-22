default_app_config = "django_mindoff.apps.DjangoMindoffConfig"
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("django-mindoff")
except PackageNotFoundError:
    __version__ = "unknown"
