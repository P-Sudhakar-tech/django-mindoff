from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .storage import TempFileHandler
from .validators import (
    validate_file_type,
    validate_file_size,
    run_custom_validation,
    security_scan,
    check_password_protected,
)
from .optimizers import optimize_file
import os
import shutil
from django.conf import settings
from .storage import TEMP_UPLOAD_DIR


class MindoffUploadAPIMixin:
    parser_classes = (MultiPartParser, FormParser)

    # --- Configurable options ---
    allowed_file_types = None
    max_file_size = None
    max_files = 5
    filename_pattern = "{uuid}_{original_name}"
    custom_validation = None
    streaming = "auto"
    enable_security_scan = True
    allow_password_protected = False
    enable_optimization = False
    optimization_strategy = "high_quality"
    temp_file_expiry_minutes = 30

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"error": "No files provided."}, status=status.HTTP_400_BAD_REQUEST
            )
        if len(files) > self.max_files:
            return Response(
                {"error": f"Max {self.max_files} files allowed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        temp_handler = TempFileHandler(expiry_minutes=self.temp_file_expiry_minutes)
        temp_handler.cleanup_expired()  # auto cleanup on access

        uploaded_files = []
        for file_obj in files:
            if self.allowed_file_types:
                validate_file_type(file_obj, self.allowed_file_types)
            if self.max_file_size:
                validate_file_size(file_obj, self.max_file_size)
            if self.custom_validation:
                run_custom_validation(file_obj, self.custom_validation)

            temp_path = temp_handler.save(
                file_obj, pattern=self.filename_pattern, streaming=self.streaming
            )

            if self.enable_security_scan:
                security_scan(temp_path)
            if not self.allow_password_protected:
                check_password_protected(temp_path)
            if self.enable_optimization:
                optimize_file(temp_path, strategy=self.optimization_strategy)

            uploaded_files.append(
                {
                    "temp_path": temp_path,
                    "original_name": file_obj.name,
                    "expiry": temp_handler.get_expiry(temp_path),
                }
            )

        return Response(
            {"uploaded_files": uploaded_files}, status=status.HTTP_201_CREATED
        )


def move_from_tmp_to_static(file_list, target_folder):
    """
    Move files from temp folder to static/media target folder
    Returns list of moved paths or raises error if file expired/not found
    """
    final_paths = []
    base_dir = os.path.join(settings.STATIC_ROOT, target_folder)
    os.makedirs(base_dir, exist_ok=True)

    for f in file_list:
        temp_path = f if os.path.isabs(f) else os.path.join(TEMP_UPLOAD_DIR, f)
        if not os.path.exists(temp_path):
            raise FileNotFoundError(f"File not found or expired: {f}")
        final_path = os.path.join(base_dir, os.path.basename(temp_path))
        shutil.move(temp_path, final_path)
        final_paths.append(final_path)
    return final_paths


def delete_file(file_name, folder="temp"):
    """
    Delete file from temp or static folder
    """
    base_dir = TEMP_UPLOAD_DIR if folder == "temp" else settings.STATIC_ROOT
    file_path = os.path.join(base_dir, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
        meta_path = file_path + ".meta"
        if os.path.exists(meta_path):
            os.remove(meta_path)
        return True
    return False


def list_files(folder="temp"):
    """
    List all files in temp or static folder
    """
    base_dir = TEMP_UPLOAD_DIR if folder == "temp" else settings.STATIC_ROOT
    if not os.path.exists(base_dir):
        return []
    return [f for f in os.listdir(base_dir) if not f.endswith(".meta")]
