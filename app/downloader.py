from pathlib import Path
import yt_dlp

QUALITY_HEIGHTS = {"1080p": 1080, "720p": 720, "480p": 480}

class DownloadError(Exception):
    pass

def inspect_video(url: str, max_duration_seconds: int) -> dict:
    opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "skip_download": True, "socket_timeout": 20, "retries": 1,
        "extractor_retries": 1, "enable_file_urls": False,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise DownloadError("Не удалось получить информацию о видео. Возможно, источник не поддерживается.") from exc
    if not info:
        raise DownloadError("Источник не вернул информацию о видео.")
    duration = info.get("duration")
    if duration and duration > max_duration_seconds:
        raise DownloadError(f"Видео длиннее лимита ({max_duration_seconds // 60} минут).")
    return {
        "id": str(info.get("id") or "video"),
        "title": str(info.get("title") or "video")[:180],
        "duration": duration,
        "extractor": info.get("extractor_key") or info.get("extractor") or "unknown",
        "formats": info.get("formats") or [],
    }

def download_video(url: str, output_dir: Path, quality_label: str,
                   max_filesize_bytes: int, max_duration_seconds: int) -> Path:
    if quality_label not in QUALITY_HEIGHTS:
        raise DownloadError("Неизвестное качество.")
    height = QUALITY_HEIGHTS[quality_label]
    output_dir.mkdir(parents=True, exist_ok=True)
    options = {
        "format": f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best",
        "outtmpl": str(output_dir / "%(id)s.%(ext)s"),
        "noplaylist": True, "max_filesize": max_filesize_bytes,
        "socket_timeout": 20, "retries": 1, "fragment_retries": 1,
        "restrictfilenames": True, "quiet": True, "no_warnings": True,
        "enable_file_urls": False, "merge_output_format": "mp4",
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration")
            if duration and duration > max_duration_seconds:
                raise DownloadError(f"Видео длиннее лимита ({max_duration_seconds // 60} минут).")
            result = ydl.extract_info(url, download=True)
            expected = Path(ydl.prepare_filename(result))
        candidates = [expected]
        if result.get("id"):
            candidates.extend(output_dir.glob(f"{result['id']}.*"))
        file_path = next((p for p in candidates if p.exists() and p.is_file()), None)
        if not file_path:
            raise DownloadError("Загрузка завершилась, но файл не найден.")
        if file_path.stat().st_size > max_filesize_bytes:
            file_path.unlink(missing_ok=True)
            raise DownloadError("Файл превышает допустимый размер.")
        if file_path.stat().st_size == 0:
            file_path.unlink(missing_ok=True)
            raise DownloadError("Источник вернул пустой файл.")
        return file_path
    except DownloadError:
        raise
    except Exception as exc:
        message = str(exc).lower()
        if "max-filesize" in message or "file is larger" in message or "filesize" in message:
            raise DownloadError("Видео слишком большое для отправки через бота.") from exc
        raise DownloadError("Не удалось скачать видео. Проверь источник или попробуй другое качество.") from exc
