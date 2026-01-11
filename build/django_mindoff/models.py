from django.contrib.auth import get_user_model
from django.db import models
from django.conf import settings
import uuid


class TimeStampModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserTrailModel(models.Model):
    created_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_created",
    )
    updated_by = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(class)s_updated",
    )

    class Meta:
        abstract = True


class SoftDeleteModel(TimeStampModel, UserTrailModel):
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


# class MindoffPolling(models.Model):
#     id = models.UUIDField(
#         primary_key=True, default=uuid.uuid4, editable=False, db_column="polling_id"
#     )
#     cookie_identifier = models.CharField(max_length=255, blank=True)
#     status = models.CharField(max_length=50, default="pending")

#     class Meta:
#         db_table = "tbl_mindoff_polling"

#     def __str__(self):
#         return f"{self.task_id} - {self.status}"
