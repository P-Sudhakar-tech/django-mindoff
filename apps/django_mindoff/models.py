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


class MOQueue(models.Model):
    mo_queue_id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = models.UUIDField()
    idempotency_key = models.CharField(max_length=64, unique=True)

    status = models.CharField(max_length=20)
    api_url = models.TextField()

    request = models.JSONField()
    response = models.JSONField(null=True, blank=True)
    error = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tbl_mo_queue"
        indexes = [
            models.Index(fields=["user_id", "status"]),
        ]
