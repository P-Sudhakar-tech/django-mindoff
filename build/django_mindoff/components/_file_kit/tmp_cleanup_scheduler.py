from apscheduler.schedulers.background import BackgroundScheduler
from .storage import TempFileHandler
from django.conf import settings

scheduler = BackgroundScheduler()


def start_auto_cleanup():
    """
    Automatically runs cleanup if enabled in settings
    """
    if getattr(settings, "ENABLE_TEMP_UPLOAD_CLEANUP", True):
        expiry_minutes = getattr(settings, "TEMP_FILE_EXPIRY_MINUTES", 30)
        scheduler.add_job(
            lambda: TempFileHandler.cleanup_expired(expiry_minutes),
            "interval",
            minutes=5,
        )
        scheduler.start()
