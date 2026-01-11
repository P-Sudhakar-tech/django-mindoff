import os
from django.core.exceptions import ValidationError


def validate_file_type(file_obj, allowed_types):
    content_type = getattr(file_obj, "content_type", None)
    if content_type not in allowed_types:
        raise ValidationError(f"File type {content_type} not allowed.")


def validate_file_size(file_obj, max_size_bytes):
    if file_obj.size > max_size_bytes:
        raise ValidationError(
            f"File size {file_obj.size} exceeds {max_size_bytes} bytes."
        )


def run_custom_validation(file_obj, validation_func):
    """
    Developer-supplied custom validation.
    """
    validation_func(file_obj)


def security_scan(file_path):
    """
    Stub for antivirus / integrity checks.
    Integrate ClamAV or other tools here.
    """
    # Example placeholder
    if os.path.getsize(file_path) == 0:
        raise ValidationError("Empty or corrupted file detected.")


def check_password_protected(file_path):
    """
    Stub for detecting password-protected files (e.g., PDF, ZIP).
    Extend with libraries like PyPDF2, zipfile, etc.
    """
    # Example placeholder (developer can override properly)
    if file_path.endswith(".pdf") and "protected" in file_path:
        raise ValidationError("Password-protected files not allowed.")
