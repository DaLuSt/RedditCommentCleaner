"""
Weekly automated cleanup script for GitHub Actions.

Deletion criteria (either condition triggers deletion):
    1. score < 1  (any age)
    2. score == 1 AND older than 14 days

Credential resolution order:
    1. Environment variables (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
       REDDIT_USERNAME, REDDIT_PASSWORD)
    2. Credentials.txt in the same directory (four lines: client_id,
       client_secret, username, password)

Optional environment variables (Google Drive upload):
    GOOGLE_SERVICE_ACCOUNT_KEY  path to service-account JSON, or the JSON string itself
    GOOGLE_DRIVE_FOLDER_ID      ID of the Drive folder to upload logs into
"""

import os
import time
from datetime import datetime, timezone

import praw
import prawcore

from drive_upload import maybe_upload_logs

_RETRY_WAIT = (5, 15, 45)  # seconds between successive retries


def _with_retry(fn, label="operation"):
    """Call fn(), retrying up to 3 times on rate-limit errors.

    Args:
        fn: Zero-argument callable to invoke.
        label: Human-readable description for log messages.
    """
    for attempt, wait in enumerate(_RETRY_WAIT, start=1):
        try:
            return fn()
        except prawcore.exceptions.TooManyRequests as exc:
            retry_after = getattr(exc, "retry_after", None) or wait
            print(f"  Rate limited on {label}. Waiting {retry_after}s (attempt {attempt}/3)…")
            time.sleep(retry_after)
        except praw.exceptions.APIException:
            raise
    return fn()  # final attempt — let exceptions propagate

AGE_THRESHOLD_DAYS = 14


def _load_credentials():
    """Return (client_id, client_secret, username, password).

    Prefers environment variables; falls back to Credentials.txt.
    """
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    username = os.environ.get("REDDIT_USERNAME")
    password = os.environ.get("REDDIT_PASSWORD")

    if all([client_id, client_secret, username, password]):
        return client_id, client_secret, username, password

    cred_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Credentials.txt")
    if os.path.exists(cred_path):
        with open(cred_path, encoding="utf-8") as f:
            lines = [line.strip() for line in f.readlines()]
        if len(lines) >= 4:
            return lines[0], lines[1], lines[2], lines[3]

    raise RuntimeError(
        "Reddit credentials not found. Set REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / "
        "REDDIT_USERNAME / REDDIT_PASSWORD environment variables, or create Credentials.txt."
    )


def _should_delete(item) -> bool:
    """Return True if item meets either deletion criterion."""
    if item.score < 1:
        return True
    age_days = (datetime.now(timezone.utc) - datetime.fromtimestamp(item.created_utc, tz=timezone.utc)).days
    return item.score == 1 and age_days > AGE_THRESHOLD_DAYS


def main():
    client_id, client_secret, username, password = _load_credentials()
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        user_agent="commentCleaner",
        validate_on_submit=True,
    )

    print(f"Authenticated as: {reddit.user.me()}")
    print(f"Criteria: score < 1  OR  (score == 1 AND older than {AGE_THRESHOLD_DAYS} days)\n")

    # ── Comments ──────────────────────────────────────────────────────────
    comments_deleted = 0
    print("Scanning comments…")
    for comment in reddit.redditor(username).comments.new(limit=None):
        if _should_delete(comment):
            date_str = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            with open("deleted_comments.txt", "a", encoding="utf-8") as f:
                f.write(f"{date_str} | {comment.score} | {comment.body}\n")
            try:
                _with_retry(lambda: comment.edit("."), "comment edit")
                _with_retry(comment.delete, "comment delete")
                comments_deleted += 1
                print(f"  Deleted comment (score={comment.score}) in r/{comment.subreddit}")
            except (praw.exceptions.APIException, prawcore.exceptions.TooManyRequests) as e:
                print(f"  Error deleting comment {comment.id}: {e}")

    # ── Posts ─────────────────────────────────────────────────────────────
    posts_deleted = 0
    print("\nScanning posts…")
    for submission in reddit.redditor(username).submissions.new(limit=None):
        if _should_delete(submission):
            with open("deleted_posts.txt", "a", encoding="utf-8") as f:
                f.write(
                    f"{submission.title}, "
                    f"{datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)}, "
                    f"{submission.score}, "
                    f"{submission.subreddit.display_name}\n"
                )
            try:
                _with_retry(lambda: submission.edit("."), "post edit")
                _with_retry(submission.delete, "post delete")
                posts_deleted += 1
                print(f"  Deleted post '{submission.title}' (score={submission.score}) in r/{submission.subreddit}")
            except (praw.exceptions.APIException, prawcore.exceptions.TooManyRequests) as e:
                print(f"  Error deleting post {submission.id}: {e}")

    print(f"\nDone. Deleted {comments_deleted} comment(s) and {posts_deleted} post(s).")

    # ── Google Drive upload ────────────────────────────────────────────────
    print("\nUploading logs to Google Drive…")
    maybe_upload_logs("deleted_comments.txt", "deleted_posts.txt")


if __name__ == "__main__":
    main()
