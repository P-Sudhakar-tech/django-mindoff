from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


class SampleRouterClassName:
    VERSION_MAP = {{{VERSION_MAP}}}

    def __call__(self, request, *args, **kwargs):
        version = kwargs.get("version") or 1
        view_class = self.VERSION_MAP.get(version)

        if view_class is None:
            return JsonResponse(
                {
                    "detail": f"API version '{version}' does not exist for this endpoint.",
                    "available_versions": list(self.VERSION_MAP.keys()),
                },
                status=404,
            )

        use_cache = getattr(settings, "MINDOFF_USE_VIEW_CACHE", False)
        if not use_cache:
            return view_class.as_view()(request, *args, **kwargs)
        if not hasattr(self, "_view_cache"):
            self._view_cache = {}
        if version not in self._view_cache:
            self._view_cache[version] = view_class.as_view()
        return self._view_cache[version](request, *args, **kwargs)


sample_router_function_name = csrf_exempt(SampleRouterClassName())
