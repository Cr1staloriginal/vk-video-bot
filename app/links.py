from urllib.parse import urlparse
import ipaddress
import socket

ALLOWED_SCHEMES = {"http", "https"}

def validate_public_http_url(value: str) -> tuple[bool, str]:
    """Basic URL validation. Network-level egress controls are still required in production."""
    value = (value or "").strip()
    if not value or len(value) > 2048:
        return False, "Пришли одну корректную ссылку длиной до 2048 символов."

    parsed = urlparse(value)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES or not parsed.hostname:
        return False, "Поддерживаются только ссылки http:// и https://."
    if parsed.username or parsed.password:
        return False, "Ссылки со встроенным логином или паролем не поддерживаются."

    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False, "Локальные адреса не поддерживаются."

    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(item[4][0])
                for item in socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
            }
        except (OSError, ValueError):
            return False, "Не удалось проверить адрес сайта. Проверь ссылку и попробуй ещё раз."

    if not addresses or any(
        not addr.is_global or addr.is_multicast or addr.is_reserved
        for addr in addresses
    ):
        return False, "Ссылки на локальные или внутренние сетевые адреса запрещены."

    return True, value
