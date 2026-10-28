from unittest.mock import patch
from app.links import validate_public_http_url

def test_rejects_empty():
    assert validate_public_http_url("")[0] is False

def test_rejects_file_scheme():
    assert validate_public_http_url("file:///etc/passwd")[0] is False

def test_rejects_localhost():
    assert validate_public_http_url("http://localhost/video.mp4")[0] is False

def test_rejects_credentials():
    assert validate_public_http_url("https://user:pass@example.com/video.mp4")[0] is False

def test_rejects_private_ip():
    ok, _ = validate_public_http_url("http://127.0.0.1/video.mp4")
    assert ok is False

def test_accepts_public_domain_when_dns_is_public():
    fake = [(None, None, None, None, ("93.184.216.34", 0))]
    with patch("app.links.socket.getaddrinfo", return_value=fake):
        ok, value = validate_public_http_url("https://example.com/video.mp4")
    assert ok is True
    assert value == "https://example.com/video.mp4"
