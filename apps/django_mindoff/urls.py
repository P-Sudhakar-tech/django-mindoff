from django.urls import path
from .views import QueueStatusView, QueueStatusStreamView

urlpatterns = [
    path(
        "queue/<uuid:queue_task_uuid>/", QueueStatusView.as_view(), name="queue-status"
    ),
    path(
        "queue/<uuid:queue_task_uuid>/stream/",
        QueueStatusStreamView.as_view(),
        name="queue-status-stream",
    ),
]
