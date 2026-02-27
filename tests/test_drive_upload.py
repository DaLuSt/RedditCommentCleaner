"""Tests for drive_upload.maybe_upload_logs."""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drive_upload import maybe_upload_logs


class TestMaybeUploadLogs:
    def test_skips_when_no_key_env_var(self, monkeypatch):
        monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID",     raising=False)
        result = maybe_upload_logs("some_file.txt")
        assert result == []

    def test_skips_when_no_folder_id(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_KEY", '{"type": "service_account"}')
        monkeypatch.delenv("GOOGLE_DRIVE_FOLDER_ID", raising=False)
        result = maybe_upload_logs("some_file.txt")
        assert result == []

    def test_skips_when_key_set_but_folder_missing(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_KEY", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID", "")
        result = maybe_upload_logs("some_file.txt")
        assert result == []

    def test_returns_empty_list_on_upload_exception(self, monkeypatch):
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_KEY", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID",     "folder123")
        with patch("drive_upload.upload_logs", side_effect=Exception("Network error")):
            result = maybe_upload_logs("some_file.txt")
        assert result == []

    def test_calls_upload_logs_when_credentials_present(self, monkeypatch, tmp_path):
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_KEY", '{"type": "service_account"}')
        monkeypatch.setenv("GOOGLE_DRIVE_FOLDER_ID",     "folder123")
        fake_result = [{"name": "deleted_comments.txt", "url": "https://drive.google.com/file/d/abc/view"}]
        with patch("drive_upload.upload_logs", return_value=fake_result) as mock_upload:
            result = maybe_upload_logs("deleted_comments.txt")
        mock_upload.assert_called_once_with("folder123", "deleted_comments.txt")
        assert result == fake_result
