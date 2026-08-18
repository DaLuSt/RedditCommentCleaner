"""Tests for redditcleaner.utils."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import praw
import prawcore
import pytest

from redditcleaner.utils import (
    _with_retry,
    build_deletion_record,
    confirm_and_run,
    edit_and_delete,
    get_days_old,
    get_reddit_credentials,
    initialize_reddit,
)

# ── _with_retry ─────────────────────────────────────────────────────────────

class TestWithRetry:
    def test_returns_result_on_first_success(self):
        fn = MagicMock(return_value="ok")
        assert _with_retry(fn, "op") == "ok"
        fn.assert_called_once()

    def test_retries_then_succeeds(self, monkeypatch):
        monkeypatch.setattr("redditcleaner.utils.time.sleep", lambda _s: None)
        fn = MagicMock(
            side_effect=[
                prawcore.exceptions.TooManyRequests(MagicMock(headers={})),
                "ok",
            ]
        )
        assert _with_retry(fn, "op") == "ok"
        assert fn.call_count == 2

    def test_reraises_api_exception_immediately(self):
        fn = MagicMock(side_effect=praw.exceptions.APIException("ERR", "bad", None))
        with pytest.raises(praw.exceptions.APIException):
            _with_retry(fn, "op")
        fn.assert_called_once()

    def test_propagates_after_exhausting_retries(self, monkeypatch):
        monkeypatch.setattr("redditcleaner.utils.time.sleep", lambda _s: None)
        fn = MagicMock(
            side_effect=prawcore.exceptions.TooManyRequests(MagicMock(headers={}))
        )
        with pytest.raises(prawcore.exceptions.TooManyRequests):
            _with_retry(fn, "op")
        # 3 attempts inside the retry loop + 1 final unguarded attempt
        assert fn.call_count == 4


# ── get_reddit_credentials ───────────────────────────────────────────────────

class TestGetRedditCredentials:
    def test_reads_from_file(self, tmp_path):
        cred_file = tmp_path / "Credentials.txt"
        cred_file.write_text("id\nsecret\nuser\npass\n", encoding="utf-8")
        result = get_reddit_credentials(str(cred_file))
        assert result == ("id", "secret", "user", "pass")

    def test_falls_back_to_prompts_when_file_missing(self, tmp_path):
        missing = tmp_path / "nope.txt"
        with patch("builtins.input", side_effect=["id", "secret", "user", "pass"]):
            result = get_reddit_credentials(str(missing))
        assert result == ("id", "secret", "user", "pass")


# ── confirm_and_run ───────────────────────────────────────────────────────────

class TestConfirmAndRun:
    @pytest.mark.parametrize("answer", ["yes", "Yes", "y", "Y"])
    def test_true_on_affirmative(self, answer):
        with patch("builtins.input", return_value=answer):
            assert confirm_and_run() is True

    @pytest.mark.parametrize("answer", ["no", "n", "nah", ""])
    def test_false_on_anything_else(self, answer):
        with patch("builtins.input", return_value=answer):
            assert confirm_and_run() is False


# ── initialize_reddit ─────────────────────────────────────────────────────────

class TestInitializeReddit:
    def test_returns_authenticated_reddit_on_success(self):
        mock_reddit = MagicMock()
        with patch("redditcleaner.utils.praw.Reddit", return_value=mock_reddit):
            result = initialize_reddit("id", "secret", "user", "pass")
        assert result is mock_reddit
        mock_reddit.user.me.assert_called_once()

    def test_exits_on_auth_failure(self):
        mock_reddit = MagicMock()
        mock_reddit.user.me.side_effect = praw.exceptions.APIException(
            "invalid_grant", "bad creds", None
        )
        with patch("redditcleaner.utils.praw.Reddit", return_value=mock_reddit):
            with pytest.raises(SystemExit):
                initialize_reddit("id", "secret", "user", "pass")


# ── build_deletion_record ─────────────────────────────────────────────────────

def _comment(**overrides):
    defaults = dict(
        created_utc=1700000000.0,
        name="t1_abc",
        subreddit=SimpleNamespace(__str__=lambda self: "python"),
        score=5,
        permalink="/r/python/comments/abc/x/",
        body="hello",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _submission(**overrides):
    defaults = dict(
        created_utc=1700000000.0,
        name="t3_xyz",
        subreddit=SimpleNamespace(__str__=lambda self: "python"),
        score=10,
        title="A title",
        permalink="/r/python/comments/xyz/y/",
        num_comments=3,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestBuildDeletionRecord:
    def test_comment_record_has_expected_keys(self):
        record = build_deletion_record(_comment(), "comment", "cli-mode-1")
        assert set(record.keys()) == {
            "deleted_at", "created_at", "id", "subreddit", "score",
            "permalink", "body", "source",
        }
        assert record["permalink"] == "https://reddit.com/r/python/comments/abc/x/"
        assert record["body"] == "hello"
        assert record["source"] == "cli-mode-1"

    def test_post_record_has_expected_keys(self):
        record = build_deletion_record(_submission(), "post", "ci")
        assert set(record.keys()) == {
            "deleted_at", "created_at", "id", "subreddit", "score",
            "title", "permalink", "num_comments", "source",
        }
        assert record["title"] == "A title"
        assert record["num_comments"] == 3
        assert record["source"] == "ci"


# ── edit_and_delete ────────────────────────────────────────────────────────────

class TestEditAndDelete:
    def test_edits_then_deletes(self, monkeypatch):
        monkeypatch.setattr("redditcleaner.utils.time.sleep", lambda _s: None)
        item = MagicMock()
        edit_and_delete(item, "comment")
        item.edit.assert_called_once_with(".")
        item.delete.assert_called_once()


# ── get_days_old ──────────────────────────────────────────────────────────────

class TestGetDaysOld:
    def test_returns_int_on_valid_input(self):
        with patch("builtins.input", return_value="14"):
            assert get_days_old() == 14

    def test_reprompts_on_invalid_input(self):
        with patch("builtins.input", side_effect=["abc", "7"]):
            assert get_days_old() == 7
