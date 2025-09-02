import inspect
import traceback
import os
from pathlib import Path
from django.conf import settings
from types import SimpleNamespace
from _helper_kit import file_guardian


def get_exact_traceback(skip: int | None = None) -> str:
    stack = inspect.stack()
    project_dirs = getattr(settings, "VALIDATION_TRACEBACK_DIRS", ["apps", "config"])
    project_dirs = [os.path.abspath(str(Path(d))) for d in project_dirs]
    valid_frames = []
    for frame_info in stack:
        filename = os.path.abspath(frame_info.filename)
        if any(filename.startswith(proj_dir + os.sep) for proj_dir in project_dirs):
            valid_frames.append(frame_info)

    if not valid_frames:
        return "No project frame found in traceback."

    if skip is None:
        summaries = [
            traceback.extract_stack(frame_info.frame, limit=1)[0]
            for frame_info in valid_frames
        ]
        return "".join(traceback.format_list(summaries))
    else:
        idx = min(skip, len(valid_frames) - 1)
        chosen_frame = valid_frames[idx]
        tb_summary = traceback.extract_stack(chosen_frame.frame, limit=1)
        return "".join(traceback.format_list(tb_summary))


mo_helper_kit = SimpleNamespace(
    get_exact_traceback=get_exact_traceback,
    file_guardian=file_guardian.file_guardian,
)
