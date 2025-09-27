import os
import uuid
from datetime import datetime, timedelta
from django.conf import settings

TEMP_UPLOAD_DIR = getattr(
    settings, "TEMP_UPLOAD_DIR", os.path.join(settings.BASE_DIR, "temp_uploads")
)
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)


class TempFileHandler:
    def __init__(self, expiry_minutes=30):
        self.expiry_minutes = expiry_minutes

    def save(self, file_obj, pattern="{uuid}_{original_name}", streaming="auto"):
        """
        Save file to TEMP_UPLOAD_DIR with metadata (.meta file storing created_at).
        Supports auto filename generation.
        """
        filename = pattern.format(
            uuid=str(uuid.uuid4().hex), original_name=file_obj.name
        )
        temp_path = os.path.join(TEMP_UPLOAD_DIR, filename)

        # streaming or normal write
        with open(temp_path, "wb+") as dest:
            for chunk in file_obj.chunks():
                dest.write(chunk)

        # write meta (expiry timestamp)
        meta_path = temp_path + ".meta"
        with open(meta_path, "w") as meta_file:
            meta_file.write(datetime.utcnow().isoformat())

        return temp_path

    def get_expiry(self, temp_path):
        meta_path = temp_path + ".meta"
        if not os.path.exists(meta_path):
            return None
        with open(meta_path, "r") as f:
            created_at = datetime.fromisoformat(f.read().strip())
        return created_at + timedelta(minutes=self.expiry_minutes)

    @staticmethod
    def cleanup_expired(expiry_minutes=30):
        """
        Deletes expired files from TEMP_UPLOAD_DIR.
        """
        now = datetime.utcnow()
        for f in os.listdir(TEMP_UPLOAD_DIR):
            if f.endswith(".meta"):
                continue
            temp_path = os.path.join(TEMP_UPLOAD_DIR, f)
            meta_path = temp_path + ".meta"
            if os.path.exists(meta_path):
                with open(meta_path, "r") as m:
                    created_at = datetime.fromisoformat(m.read().strip())
                expiry = created_at + timedelta(minutes=expiry_minutes)
                if now > expiry:
                    try:
                        os.remove(temp_path)
                        os.remove(meta_path)
                    except Exception:
                        pass
