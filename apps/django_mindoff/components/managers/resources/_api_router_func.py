from django.http import JsonResponse
from django.views import View


def sample_router_function_name(request, *args, **kwargs):
    VERSION_MAP = {{{VERSION_MAP}}}
    version = kwargs.get("version")
    view_class = VERSION_MAP.get(version)
    if view_class is None:
        return JsonResponse(
            {
                "detail": f"API version '{version}' does not exist for this endpoint.",
                "available_versions": list(VERSION_MAP.keys()),
            },
            status=404,
        )
    return view_class.as_view()(request, *args, **kwargs)
