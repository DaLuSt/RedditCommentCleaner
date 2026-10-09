"""Tests for redditcleaner.cli.comment_cleaner and redditcleaner.cli.post_cleaner."""

import json
import time
from unittest.mock import MagicMock

import praw

from redditcleaner.cli.comment_cleaner import (
    delete_old_comments,
    remove_comments_with_negative_karma,
    remove_comments_with_one_karma_and_no_replies,
)
from redditcleaner.cli.post_cleaner import delete_old_posts


def _comment(score=0, age_days=0, replies=None, body="hello", subreddit="python", name="t1_abc"):
    comment = MagicMock()
    comment.created_utc = time.time() - age_days * 86400
    comment.score = score
    comment.subreddit = subreddit
    comment.body = body
    comment.name = name
    comment.permalink = f"/r/{subreddit}/comments/{name}/"
    comment.replies = replies if replies is not None else []
    return comment


def _submission(score=0, age_days=0, title="A post", subreddit="python", name="t3_xyz", num_comments=0):
    submission = MagicMock()
    submission.created_utc = time.time() - age_days * 86400
    submission.score = score
    submission.subreddit = subreddit
    submission.title = title
    submission.name = name
    submission.permalink = f"/r/{subreddit}/comments/{name}/"
    submission.num_comments = num_comments
    return submission


def _reddit_with(items, kind):
    """Build a fake praw.Reddit whose redditor(...).<kind>.new() yields *items*."""
    reddit = MagicMock()
    getattr(reddit.redditor.return_value, kind).new.return_value = items
    return reddit


# ── delete_old_comments (mode 1) ───────────────────────────────────────────────

class TestDeleteOldComments:
    def test_deletes_only_comments_older_than_threshold(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        new = _comment(age_days=1)
        old = _comment(age_days=10)
        reddit = _reddit_with([new, old], "comments")  # newest-first, like the real API

        deleted = []
        delete_old_comments(reddit, "user", 5, deleted)

        assert deleted == [old]
        new.edit.assert_not_called()
        old.edit.assert_called_once_with(".")
        old.delete.assert_called_once()

    def test_past_cutoff_deletes_every_subsequent_comment(self, monkeypatch, tmp_path):
        """Once an old-enough comment is seen, later comments skip the age re-check entirely."""
        monkeypatch.chdir(tmp_path)
        old = _comment(age_days=10)
        would_be_too_new = _comment(age_days=1)
        reddit = _reddit_with([old, would_be_too_new], "comments")

        deleted = []
        delete_old_comments(reddit, "user", 5, deleted)

        assert deleted == [old, would_be_too_new]

    def test_dry_run_does_not_edit_or_delete(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        old = _comment(age_days=10)
        reddit = _reddit_with([old], "comments")

        deleted = []
        delete_old_comments(reddit, "user", 5, deleted, dry_run=True)

        assert deleted == [old]
        old.edit.assert_not_called()
        old.delete.assert_not_called()

    def test_writes_json_log_line(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        old = _comment(age_days=10, score=-3)
        reddit = _reddit_with([old], "comments")

        delete_old_comments(reddit, "user", 5, [])

        record = json.loads((tmp_path / "deleted_comments.txt").read_text(encoding="utf-8").strip())
        assert record["source"] == "cli-mode-1"
        assert record["score"] == -3

    def test_continues_after_error_without_appending(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        bad = _comment(age_days=10)
        bad.edit.side_effect = praw.exceptions.APIException("ERR", "bad", None)
        reddit = _reddit_with([bad], "comments")

        deleted = []
        delete_old_comments(reddit, "user", 5, deleted)

        assert deleted == []


# ── remove_comments_with_negative_karma (mode 2) ─────────────────────────────

class TestRemoveCommentsWithNegativeKarma:
    def test_removes_zero_and_negative_score(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        negative = _comment(score=-1)
        zero = _comment(score=0)
        positive = _comment(score=5)
        reddit = _reddit_with([negative, zero, positive], "comments")

        deleted = []
        remove_comments_with_negative_karma(reddit, "user", deleted)

        assert deleted == [negative, zero]
        positive.edit.assert_not_called()


# ── remove_comments_with_one_karma_and_no_replies (mode 3) ───────────────────

class TestRemoveCommentsWithOneKarmaAndNoReplies:
    def test_removes_old_low_score_comment_with_no_replies(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        target = _comment(score=1, age_days=8, replies=[])
        reddit = _reddit_with([target], "comments")

        deleted = []
        remove_comments_with_one_karma_and_no_replies(reddit, "user", deleted)

        assert deleted == [target]
        target.refresh.assert_called_once()

    def test_keeps_comment_with_replies(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        has_replies = _comment(score=1, age_days=8, replies=[MagicMock()])
        reddit = _reddit_with([has_replies], "comments")

        deleted = []
        remove_comments_with_one_karma_and_no_replies(reddit, "user", deleted)

        assert deleted == []

    def test_keeps_comment_too_new(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        too_new = _comment(score=1, age_days=1, replies=[])
        reddit = _reddit_with([too_new], "comments")

        deleted = []
        remove_comments_with_one_karma_and_no_replies(reddit, "user", deleted)

        assert deleted == []

    def test_keeps_high_score_comment(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        high_score = _comment(score=2, age_days=8, replies=[])
        reddit = _reddit_with([high_score], "comments")

        deleted = []
        remove_comments_with_one_karma_and_no_replies(reddit, "user", deleted)

        assert deleted == []


# ── delete_old_posts ──────────────────────────────────────────────────────────

class TestDeleteOldPosts:
    def test_deletes_only_posts_older_than_threshold(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        new = _submission(age_days=1)
        old = _submission(age_days=10)
        reddit = _reddit_with([new, old], "submissions")

        count = delete_old_posts(reddit, "user", 5)

        assert count == 1
        new.edit.assert_not_called()
        old.edit.assert_called_once_with(".")
        old.delete.assert_called_once()

    def test_dry_run_counts_without_deleting(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        old = _submission(age_days=10)
        reddit = _reddit_with([old], "submissions")

        count = delete_old_posts(reddit, "user", 5, dry_run=True)

        assert count == 1
        old.edit.assert_not_called()

    def test_writes_json_log_line(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        old = _submission(age_days=10, title="My Post")
        reddit = _reddit_with([old], "submissions")

        delete_old_posts(reddit, "user", 5)

        record = json.loads((tmp_path / "deleted_posts.txt").read_text(encoding="utf-8").strip())
        assert record["title"] == "My Post"
        assert record["source"] == "cli"

    def test_continues_after_error(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        bad = _submission(age_days=10)
        bad.edit.side_effect = praw.exceptions.APIException("ERR", "bad", None)
        good = _submission(age_days=10)
        reddit = _reddit_with([bad, good], "submissions")

        count = delete_old_posts(reddit, "user", 5)

        assert count == 1
