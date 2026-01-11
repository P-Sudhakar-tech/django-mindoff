import mimetypes
import shutil
from pathlib import Path
from typing import Literal, Optional

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pydub import AudioSegment
import orjson


# Supported modes
OptimizeMode = Literal[
    "lossless",
    "lossy",
    "thumbnail",
    "compress",
    "strip_metadata",
    "resize",
    "normalize",
    "minify",
    "repack",
]


# ========= GATEWAY =========
def optimize_file(
    file_path: Path,
    mode: OptimizeMode,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Optimize a file based on its type and requested mode.
    Falls back to saving the original file if optimization is unsupported.

    :param file_path: Path to the input file.
    :param mode: Optimization strategy (see OptimizeMode).
    :param output_path: Optional path for the optimized file.
    :return: Path to optimized file.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    output_path = output_path or file_path

    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        return _fallback_copy(file_path, output_path)

    if mime_type.startswith("image/"):
        return _optimize_image(file_path, mode, output_path)
    if mime_type == "application/pdf":
        return _optimize_pdf(file_path, mode, output_path)
    if mime_type.startswith("audio/"):
        return _optimize_audio(file_path, mode, output_path)
    if mime_type.startswith("video/"):
        return _optimize_video(file_path, mode, output_path)
    if mime_type in {"text/plain", "application/json", "text/csv"}:
        return _optimize_text(file_path, mode, output_path)
    if mime_type in {"application/zip", "application/x-tar"}:
        return _optimize_archive(file_path, mode, output_path)

    return _fallback_copy(file_path, output_path)


def _fallback_copy(file_path: Path, output_path: Path) -> Path:
    """Default fallback: copy file unchanged."""
    shutil.copy(file_path, output_path)
    return output_path


# ========= IMAGE =========
def _optimize_image(file_path: Path, mode: OptimizeMode, output_path: Path) -> Path:
    with Image.open(file_path) as img:
        if mode == "lossless":
            img.save(output_path, optimize=True)
        elif mode == "lossy":
            img.save(output_path, optimize=True, quality=70)
        elif mode == "thumbnail":
            img.thumbnail((256, 256))
            img.save(output_path)
        elif mode == "strip_metadata":
            data = list(img.getdata())
            new_img = Image.new(img.mode, img.size)
            new_img.putdata(data)
            new_img.save(output_path)
        else:
            return _fallback_copy(file_path, output_path)
    return output_path


# ========= PDF =========
def _optimize_pdf(file_path: Path, mode: OptimizeMode, output_path: Path) -> Path:
    reader = PdfReader(str(file_path))
    writer = PdfWriter()

    if mode in {"compress", "strip_metadata"}:
        for page in reader.pages:
            writer.add_page(page)
        if mode == "strip_metadata":
            writer.add_metadata({})
    else:
        return _fallback_copy(file_path, output_path)

    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


# ========= AUDIO =========
def _optimize_audio(file_path: Path, mode: OptimizeMode, output_path: Path) -> Path:
    audio = AudioSegment.from_file(file_path)

    if mode == "compress":
        audio.export(output_path, format="mp3", bitrate="128k")
    elif mode == "normalize":
        change = audio.max_dBFS - audio.dBFS
        normalized = audio.apply_gain(change)
        normalized.export(output_path, format="mp3")
    elif mode == "strip_metadata":
        audio.export(output_path, tags={})
    else:
        return _fallback_copy(file_path, output_path)

    return output_path


# ========= VIDEO =========
def _optimize_video(file_path: Path, mode: OptimizeMode, output_path: Path) -> Path:
    if mode == "thumbnail":
        from moviepy.editor import VideoFileClip

        clip = VideoFileClip(str(file_path))
        frame = clip.get_frame(1.0)
        img = Image.fromarray(frame)
        img.save(output_path.with_suffix(".jpg"))
        return output_path.with_suffix(".jpg")

    return _fallback_copy(file_path, output_path)


# ========= TEXT / JSON =========
def _optimize_text(file_path: Path, mode: OptimizeMode, output_path: Path) -> Path:
    text = file_path.read_text(encoding="utf-8")

    if mode == "minify":
        minified = " ".join(text.split())
        output_path.write_text(minified, encoding="utf-8")
    elif mode == "compress":
        import gzip

        with gzip.open(output_path.with_suffix(".gz"), "wt", encoding="utf-8") as f:
            f.write(text)
        return output_path.with_suffix(".gz")
    elif mode == "strip_metadata" and file_path.suffix == ".json":
        data = orjson.loads(text)
        output_path.write_text(orjson.dumps(data).decode("utf-8"), encoding="utf-8")
    else:
        return _fallback_copy(file_path, output_path)

    return output_path


# ========= ARCHIVES =========
def _optimize_archive(file_path: Path, mode: OptimizeMode, output_path: Path) -> Path:
    if mode != "repack":
        return _fallback_copy(file_path, output_path)

    suffix = file_path.suffix.lower()
    if suffix == ".zip":
        return __repack_zip(file_path, output_path)
    if suffix == ".7z":
        return __repack_7z(file_path, output_path)
    if suffix in {".rar"}:
        return __repack_rar(file_path, output_path)

    return _fallback_copy(file_path, output_path)


def __repack_zip(file_path: Path, output_path: Path) -> Path:
    import zipfile

    with zipfile.ZipFile(file_path, "r") as zin:
        with zipfile.ZipFile(
            output_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
    return output_path


def __repack_7z(file_path: Path, output_path: Path) -> Path:
    import py7zr

    with py7zr.SevenZipFile(file_path, "r") as zin:
        zin.extractall(path=output_path.parent / "tmp_extract_7z")

    with py7zr.SevenZipFile(output_path, "w") as zout:
        zout.writeall(output_path.parent / "tmp_extract_7z", arcname=".")

    shutil.rmtree(output_path.parent / "tmp_extract_7z", ignore_errors=True)
    return output_path


def __repack_rar(file_path: Path, output_path: Path) -> Path:
    import rarfile

    tmp_extract = output_path.parent / "tmp_extract_rar"
    tmp_extract.mkdir(exist_ok=True)

    with rarfile.RarFile(file_path) as rin:
        rin.extractall(path=tmp_extract)

    # repackage as ZIP (RAR writing not natively supported in Python)
    return __repack_zip(tmp_extract, output_path.with_suffix(".zip"))
