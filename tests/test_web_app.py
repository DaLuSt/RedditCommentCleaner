"""Tests for the Flask web application (web/app.py)."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Ensure repo root on path so drive_upload is importable from web/app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# web/app.py does sys.path manipulation itself, but we need the module importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web"))

from app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def authed_client(client):
    """A test client with a valid-looking session."""
    with flask_app.test_request_context():
        with client.session_transaction() as sess:
            sess["username"]      = "testuser"
            sess["client_id"]     = "cid"
            sess["client_secret"] = "csecret"
            sess["password"]      = "pw"
    return client


# ── / (index) ─────────────────────────────────────────────────────────────────

class TestIndex:
    def test_shows_login_page_without_session(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_redirects_to_dashboard_with_session(self, authed_client):
        resp = authed_client.get("/")
        assert resp.status_code == 302
        assert "/dashboard" in resp.headers["Location"]


# ── /logout ───────────────────────────────────────────────────────────────────

class TestLogout:
    def test_clears_session_and_redirects(self, authed_client):
        resp = authed_client.get("/logout")
        assert resp.status_code == 302
        # After logout the session should be gone → / shows login again
        resp2 = authed_client.get("/")
        assert resp2.status_code == 200

    def test_logout_without_session_still_redirects(self, client):
        resp = client.get("/logout")
        assert resp.status_code == 302


# ── /dashboard ────────────────────────────────────────────────────────────────

class TestDashboard:
    def test_redirects_to_index_without_session(self, client):
        resp = client.get("/dashboard")
        assert resp.status_code == 302
        assert "/" in resp.headers["Location"]

    def test_accessible_with_session(self, authed_client):
        resp = authed_client.get("/dashboard")
        assert resp.status_code == 200


# ── /api/items ────────────────────────────────────────────────────────────────

class TestApiItems:
    def test_returns_401_without_session(self, client):
        resp = client.get("/api/items")
        assert resp.status_code == 401
        assert resp.get_json()["error"] == "Not authenticated"

    def test_returns_items_with_session(self, authed_client):
        mock_comment = MagicMock()
        mock_comment.id          = "abc"
        mock_comment.body        = "hello world"
        mock_comment.score       = 5
        mock_comment.subreddit   = MagicMock(__str__=lambda s: "python")
        mock_comment.created_utc = 1700000000.0
        mock_comment.permalink   = "/r/python/comments/abc/hello"

        mock_reddit = MagicMock()
        mock_reddit.redditor.return_value.comments.new.return_value  = [mock_comment]
        mock_reddit.redditor.return_value.submissions.new.return_value = []

        with patch("app.praw.Reddit", return_value=mock_reddit):
            resp = authed_client.get("/api/items")

        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["comments"]) == 1
        assert data["comments"][0]["id"] == "abc"
        assert data["posts"] == []


# ── /api/delete ───────────────────────────────────────────────────────────────

class TestApiDelete:
    def test_returns_401_without_session(self, client):
        resp = client.post("/api/delete", json={"comment_ids": [], "post_ids": []})
        assert resp.status_code == 401

    def test_deletes_comment(self, authed_client, tmp_path, monkeypatch):
        monkeypatch.setattr("app.DELETED_COMMENTS_FILE", str(tmp_path / "deleted_comments.txt"))
        monkeypatch.setattr("app.DELETED_POSTS_FILE",    str(tmp_path / "deleted_posts.txt"))

        mock_comment = MagicMock()
        mock_comment.created_utc = 1700000000.0
        mock_comment.score       = -1
        mock_comment.name        = "t1_abc123"
        mock_comment.subreddit   = "testsubreddit"
        mock_comment.permalink   = "/r/testsubreddit/comments/abc/test/abc123/"
        mock_comment.body        = "bad comment"

        mock_reddit = MagicMock()
        mock_reddit.comment.return_value = mock_comment

        with patch("app.praw.Reddit", return_value=mock_reddit), \
             patch("app.maybe_upload_logs", return_value=[]):
            resp = authed_client.post("/api/delete", json={"comment_ids": ["abc"], "post_ids": []})

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["deleted_comments"] == 1
        assert data["deleted_posts"]    == 0
        mock_comment.edit.assert_called_once_with(".")
        mock_comment.delete.assert_called_once()
