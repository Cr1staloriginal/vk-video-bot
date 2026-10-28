import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

from app.config import (
    VK_TOKEN, VK_GROUP_ID, VK_API_VERSION, MAX_FILE_MB,
    MAX_DURATION_SECONDS, MAX_CONCURRENT_DOWNLOADS, DOWNLOAD_DIR,
)
from app.downloader import inspect_video, download_video, DownloadError, QUALITY_HEIGHTS
from app.keyboards import quality_keyboard, main_keyboard
from app.links import validate_public_http_url
from app.vk_api import VKClient, VKAPIError

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("vk-video-bot")

pending: dict[int, str] = {}
pending_lock = threading.Lock()
active_peers: set[int] = set()
active_lock = threading.Lock()


def _message_parts(event):
    msg = event.obj.message
    if isinstance(msg, dict):
        return int(msg.get("peer_id", 0)), str(msg.get("text", "")).strip()
    return int(getattr(msg, "peer_id", 0)), str(getattr(msg, "text", "")).strip()


def main():
    missing = []
    if not VK_TOKEN:
        missing.append("VK_TOKEN")
    if VK_GROUP_ID <= 0:
        missing.append("VK_GROUP_ID (должен быть числовым ID сообщества)")
    if missing:
        # Never print the token or its contents to logs.
        raise SystemExit(
            "Не найдены или некорректны настройки окружения: " + ", ".join(missing) +
            ". Проверь переменные окружения Bothost; секретные значения не публикуй."
        )

    session = vk_api.VkApi(token=VK_TOKEN, api_version=VK_API_VERSION)
    client = VKClient(session, VK_API_VERSION)
    longpoll = VkBotLongPoll(session, VK_GROUP_ID)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    job_slots = threading.BoundedSemaphore(MAX_CONCURRENT_DOWNLOADS)
    executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS, thread_name_prefix="download")

    def send(peer_id, text, keyboard=None):
        try:
            client.send_message(peer_id, text, keyboard)
        except Exception:
            log.exception("Failed to send message to peer_id=%s", peer_id)

    def process_download(peer_id: int, url: str, quality: str):
        path = None
        try:
            send(peer_id, f"Начинаю загрузку ({quality}). Это может занять некоторое время…")
            path = download_video(
                url, DOWNLOAD_DIR, quality,
                max_filesize_bytes=MAX_FILE_MB * 1024 * 1024,
                max_duration_seconds=MAX_DURATION_SECONDS,
            )
            send(peer_id, "Загрузка завершена. Отправляю файл в VK…")
            client.send_document(peer_id, path, path.name)
        except (DownloadError, VKAPIError) as exc:
            send(peer_id, f"Не получилось обработать видео: {exc}")
        except Exception:
            log.exception("Unexpected download failure for peer_id=%s", peer_id)
            send(peer_id, "Произошла внутренняя ошибка. Попробуй позже.")
        finally:
            if path:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    log.warning("Could not remove temporary file %s", path)
            with active_lock:
                active_peers.discard(peer_id)
            with pending_lock:
                pending.pop(peer_id, None)
            job_slots.release()

    log.info("Starting VK video bot for group %s", VK_GROUP_ID)
    try:
        for event in longpoll.listen():
            if event.type != VkBotEventType.MESSAGE_NEW:
                continue
            peer_id, text = _message_parts(event)
            if not peer_id:
                continue
            lower = text.lower()

            if lower in {"/start", "начать", "старт"}:
                send(
                    peer_id,
                    "Привет! Пришли ссылку на общедоступное видео, которое ты вправе сохранять. "
                    "Я попробую определить доступные форматы и предложу качество.",
                    main_keyboard(),
                )
                continue

            if lower in {"/help", "ℹ️ помощь", "помощь"}:
                send(
                    peer_id,
                    "Как пользоваться:\n1. Отправь ссылку на видео.\n"
                    "2. Выбери 1080p, 720p или 480p.\n"
                    f"3. Лимит: {MAX_FILE_MB} МБ и {MAX_DURATION_SECONDS // 60} минут.\n\n"
                    "Поддержка зависит от сайта. Не отправляй закрытый контент и не обходи ограничения доступа.",
                    main_keyboard(),
                )
                continue

            if lower == "отмена":
                with pending_lock:
                    pending.pop(peer_id, None)
                send(peer_id, "Выбор отменён. Пришли другую ссылку, если нужно.", main_keyboard())
                continue

            with pending_lock:
                url = pending.get(peer_id)

            if text in QUALITY_HEIGHTS and url:
                with active_lock:
                    if peer_id in active_peers:
                        send(peer_id, "У тебя уже выполняется загрузка. Дождись её завершения.")
                        continue
                    if not job_slots.acquire(blocking=False):
                        send(peer_id, "Сейчас все слоты загрузки заняты. Попробуй через минуту.")
                        continue
                    active_peers.add(peer_id)
                executor.submit(process_download, peer_id, url, text)
                continue

            if text.startswith(("http://", "https://")):
                with active_lock:
                    if peer_id in active_peers:
                        send(peer_id, "У тебя уже выполняется загрузка. Дождись её завершения.")
                        continue
                valid, result = validate_public_http_url(text)
                if not valid:
                    send(peer_id, result)
                    continue
                send(peer_id, "Проверяю ссылку и доступные форматы…")
                try:
                    info = inspect_video(result, MAX_DURATION_SECONDS)
                except DownloadError as exc:
                    send(peer_id, str(exc))
                    continue
                with pending_lock:
                    pending[peer_id] = result
                duration = info.get("duration")
                duration_text = f"\nДлительность: {int(duration // 60)} мин {int(duration % 60)} сек" if duration else ""
                send(
                    peer_id,
                    f"Видео найдено: {info['title']}{duration_text}\nВыбери максимальное разрешение:",
                    quality_keyboard(),
                )
                continue

            send(peer_id, "Пришли ссылку http(s) на видео или нажми «ℹ️ Помощь».", main_keyboard())
    except KeyboardInterrupt:
        log.info("Stopping bot…")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    main()
