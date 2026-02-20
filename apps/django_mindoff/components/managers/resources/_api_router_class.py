from django.http import JsonResponse


class SampleRouterClassName:
    """
    Version router for the {{API_HUMAN_NAME}} API.

    Maps the ``version`` URL kwarg to the appropriate versioned APIView class.
    Registered in urls.py as an instance: ``SampleRouterClassName()``.

    To add a new version, insert an entry into VERSION_MAP:
        2: CreateInventoryV2APIView,
    """

    VERSION_MAP = {{{VERSION_MAP}}}

    def __call__(self, request, *args, **kwargs):
        version = kwargs.get("version")
        view_class = self.VERSION_MAP.get(version)

        if view_class is None:
            return JsonResponse(
                {
                    "detail": f"API version '{version}' does not exist for this endpoint.",
                    "available_versions": list(self.VERSION_MAP.keys()),
                },
                status=404,
            )

        return view_class.as_view()(request, *args, **kwargs)


sample_router_function_name = SampleRouterClassName()
