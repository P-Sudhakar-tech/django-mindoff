from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class MindoffAPIMixin(APIView):
    # Override in subclass to allow only specific methods
    accepted_requests = ["post", "put", "delete", "get"]

    def run(self, request, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement `run()`")

    def dispatch(self, request, *args, **kwargs):
        if request.method.lower() not in [m.lower() for m in self.accepted_requests]:
            return Response(
                {"error": f"Method {request.method} not allowed"},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.run(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.run(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.run(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.run(request, *args, **kwargs)
