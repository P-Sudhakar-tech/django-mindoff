from django_mindoff.components.helpers.api_class_mixin import MindoffAPIMixin
from rest_framework.response import Response


class MindOffSampleAPI(MindoffAPIMixin):
    accepted_requests = ["get", "post", "put", "delete"]

    def run(self, request, *args, **kwargs):
        return Response(
            {
                "method": request.method,
                "data": (
                    request.data if request.method != "GET" else request.query_params
                ),
            }
        )
