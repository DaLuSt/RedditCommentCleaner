"""Tests for weekly_cleanup.py — _should_delete and _load_credentials."""

import os
import sys
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

# Ensure repo root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from weekly_cleanup import AGE_THRESHOLD_DAYS, _load_credentials, _should_delete


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item(score: int, age_days: int) -> SimpleNamespace:
    """Build a fake PRAW item with the given score and age."""
    now_utc = datetime.now(timezone.utc)
    created_utc = now_utc.timestamp() - age_days * 86400
    return SimpleNamespace(score=score, created_utc=created_utc)


# ── _should_delete ────────────────────────────────────────────────────────────

class TestShouldDelete:
    def test_score_zero_is_deleted(self):
        assert _should_delete(_item(score=0, age_days=0)) is True

    def test_score_negative_is_deleted(self):
        assert _should_delete(_item(score=-5, age_days=0)) is True

    def test_score_one_old_enough_is_deleted(self):
        assert _should_delete(_item(score=1, age_days=AGE_THRESHOLD_DAYS + 1)) is True

    def test_score_one_too_new_is_kept(self):
        assert _should_delete(_item(score=1, age_days=AGE_THRESHOLD_DAYS - 1)) is False

    def test_score_one_exactly_threshold_is_kept(self):
        # boundary: age == threshold (not strictly greater) → keep
        assert _should_delete(_item(score=1, age_days=AGE_THRESHOLD_DAYS)) is False

    def test_score_two_is_always_kept(self):
        assert _should_delete(_item(score=2, age_days=365)) is False

    def test_high_score_old_is_kept(self):
        assert _should_delete(_item(score=100, age_days=1000)) is False


# ── _load_credentials ─────────────────────────────────────────────────────────

class TestLoadCredentials:
    _ENV_VARS = {
        "REDDIT_CLIENT_ID":     "id123",
        "REDDIT_CLIENT_SECRET": "secret456",
        "REDDIT_USERNAME":      "testuser",
        "REDDIT_PASSWORD":      "hunter2",
    }

    def test_reads_from_env_vars(self):
        with patch.dict(os.environ, self._ENV_VARS, clear=False):
            result = _load_credentials()
        assert result == ("id123", "secret456", "testuser", "hunter2")

    def test_reads_from_credentials_file(self, tmp_path, monkeypatch):
        cred_file = tmp_path / "Credentials.txt"
        cred_file.write_text("fileid\nfilesecret\nfileuser\nfilepass\n", encoding="utf-8")

        # Clear env vars so file fallback is triggered
        monkeypatch.delenv("REDDIT_CLIENT_ID",     raising=False)
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("REDDIT_USERNAME",       raising=False)
        monkeypatch.delenv("REDDIT_PASSWORD",       raising=False)

        with patch("weekly_cleanup.os.path.join", return_value=str(cred_file)), \
             patch("weekly_cleanup.os.path.exists", return_value=True):
            result = _load_credentials()

        assert result == ("fileid", "filesecret", "fileuser", "filepass")

    def test_raises_when_nothing_configured(self, monkeypatch):
        monkeypatch.delenv("REDDIT_CLIENT_ID",     raising=False)
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("REDDIT_USERNAME",       raising=False)
        monkeypatch.delenv("REDDIT_PASSWORD",       raising=False)

        with patch("weekly_cleanup.os.path.exists", return_value=False):
            with pytest.raises(RuntimeError, match="Reddit credentials not found"):
                _load_credentials()

    def test_partial_env_vars_falls_through_to_file(self, tmp_path, monkeypatch):
        """Only some env vars set → should not use env, must fall back to file."""
        monkeypatch.setenv("REDDIT_CLIENT_ID", "partial")
        monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("REDDIT_USERNAME",       raising=False)
        monkeypatch.delenv("REDDIT_PASSWORD",       raising=False)

        cred_file = tmp_path / "Credentials.txt"
        cred_file.write_text("a\nb\nc\nd\n", encoding="utf-8")

        with patch("weekly_cleanup.os.path.join", return_value=str(cred_file)), \
             patch("weekly_cleanup.os.path.exists", return_value=True):
            result = _load_credentials()

        assert result == ("a", "b", "c", "d")
