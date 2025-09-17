from django.apps import AppConfig

from apps.django_mindoff.components.response_kit import load_responses_csv


class DjangoMindoffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.django_mindoff"

    def ready(self):
        load_responses_csv()
