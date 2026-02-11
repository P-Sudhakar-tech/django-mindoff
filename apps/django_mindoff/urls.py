from django.urls import path
from .views import MindoffQueuePollingView, MindoffQueueStreamingView

urlpatterns = [
    path(
        "queue/<uuid:queue_task_uuid>/",
        MindoffQueuePollingView.as_view(),
        name="mo_queue_status_polling",
    ),
    path(
        "queue/<uuid:queue_task_uuid>/stream/",
        MindoffQueueStreamingView.as_view(),
        name="mo_queue_status_streaming",
    ),
]
