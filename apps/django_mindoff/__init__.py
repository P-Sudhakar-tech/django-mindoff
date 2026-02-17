default_app_config = "django_mindoff.apps.DjangoMindoffConfig"


def __getattr__(name):
    if name == "mo_api_kit":
        from .components.api_kit import mo_api_kit

        return mo_api_kit
    if name == "mo_crud_kit":
        from .components.crud_kit import mo_crud_kit

        return mo_crud_kit
    if name == "mo_polars_kit":
        from .components.polars_kit import mo_polars_kit

        return mo_polars_kit
    if name == "mo_response_kit":
        from .components.response_kit import mo_response_kit

        return mo_response_kit
    if name == "mo_validation_kit":
        from .components.validation_kit import mo_validation_kit

        return mo_validation_kit
    if name == "mo_tdd_kit":
        from .components.tdd_kit import mo_tdd_kit

        return mo_tdd_kit
    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "mo_api_kit",
    "mo_crud_kit",
    "mo_polars_kit",
    "mo_response_kit",
    "mo_validation_kit",
    "mo_tdd_kit",
]
