import secrets
from pathlib import Path
import requests

class VKAPIError(RuntimeError):
    pass

class VKClient:
    def __init__(self, session, api_version: str):
        self.session = session
        self.api = session.get_api()
        self.api_version = api_version

    def send_message(self, peer_id: int, text: str, keyboard: str | None = None):
        params = {"peer_id": peer_id, "message": text, "random_id": secrets.randbelow(2**31)}
        if keyboard:
            params["keyboard"] = keyboard
        try:
            return self.api.messages.send(**params)
        except Exception as exc:
            raise VKAPIError("VK не смог отправить сообщение.") from exc

    def send_document(self, peer_id: int, file_path: Path, title: str):
        """Upload as a message document using docs.getMessagesUploadServer + docs.save."""
        try:
            server = self.api.docs.getMessagesUploadServer(peer_id=peer_id, type="doc")
            upload_url = server.get("upload_url")
            if not upload_url:
                raise VKAPIError("VK не вернул адрес загрузки документа.")
            with file_path.open("rb") as handle:
                response = requests.post(
                    upload_url,
                    files={"file": (file_path.name, handle, "application/octet-stream")},
                    timeout=(15, 180),
                )
            response.raise_for_status()
            payload = response.json()
            file_token = payload.get("file")
            if not file_token:
                raise VKAPIError("Сервер загрузки VK не принял файл.")
            saved = self.api.docs.save(file=file_token, title=title[:180])
            doc = saved.get("doc") if isinstance(saved, dict) else None
            if not doc:
                raise VKAPIError("VK не сохранил загруженный документ.")
            owner_id = doc.get("owner_id")
            doc_id = doc.get("id")
            access_key = doc.get("access_key")
            if owner_id is None or doc_id is None:
                raise VKAPIError("VK вернул неполные данные документа.")
            attachment = f"doc{owner_id}_{doc_id}"
            if access_key:
                attachment += f"_{access_key}"
            self.api.messages.send(
                peer_id=peer_id, message="Готово! Видео прикреплено к сообщению.",
                attachment=attachment, random_id=secrets.randbelow(2**31),
            )
            return doc
        except VKAPIError:
            raise
        except Exception as exc:
            raise VKAPIError("VK отклонил загрузку или отправку файла. Проверь лимиты и права токена.") from exc
