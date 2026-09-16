import pytest
from relay.utils import get_public_url
from relay.config import settings

def test_get_public_url_no_trailing_slash(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://example.com")
    url = get_public_url("ABC123")
    assert url == "https://example.com/t/ABC123/"

def test_get_public_url_with_trailing_slash(monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_BASE_URL", "https://example.com/")
    url = get_public_url("ABC123")
    assert url == "https://example.com/t/ABC123/"
