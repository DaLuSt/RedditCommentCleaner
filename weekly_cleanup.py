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

Optional environment variables:
    GOOGLE_SERVICE_ACCOUNT_KEY  path to service-account JSON, or the JSON string itself
    GOOGLE_DRIVE_FOLDER_ID      ID of the Drive folder to upload logs into
    DRY_RUN                     set to "1" to preview deletions without making changes

Usage:
    python weekly_cleanup.py             # normal run
    python weekly_cleanup.py --dry-run   # preview only, nothing deleted
"""

import argparse
import os
from datetime import datetime, timezone

import praw

from drive_upload import maybe_upload_logs

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


def main(dry_run: bool = False):
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
    print(f"Criteria: score < 1  OR  (score == 1 AND older than {AGE_THRESHOLD_DAYS} days)")
    if dry_run:
        print("DRY RUN — no items will be edited or deleted\n")
    else:
        print()

    # ── Comments ──────────────────────────────────────────────────────────
    comments_deleted = 0
    print("Scanning comments…")
    for comment in reddit.redditor(username).comments.new(limit=None):
        if _should_delete(comment):
            created_at = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            deleted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if dry_run:
                print(f"  [DRY RUN] Would delete comment (score={comment.score}) in r/{comment.subreddit}: {comment.body[:80]!r}")
            else:
                with open("deleted_comments.txt", "a", encoding="utf-8") as f:
                    f.write(f"{deleted_at} | {created_at} | {comment.score} | ci | {comment.body}\n")
                try:
                    comment.edit(".")
                    comment.delete()
                    comments_deleted += 1
                    print(f"  Deleted comment (score={comment.score}) in r/{comment.subreddit}")
                except praw.exceptions.APIException as e:
                    print(f"  Error deleting comment {comment.id}: {e}")

    # ── Posts ─────────────────────────────────────────────────────────────
    posts_deleted = 0
    print("\nScanning posts…")
    for submission in reddit.redditor(username).submissions.new(limit=None):
        if _should_delete(submission):
            if dry_run:
                print(f"  [DRY RUN] Would delete post '{submission.title}' (score={submission.score}) in r/{submission.subreddit}")
            else:
                created_at = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                deleted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                with open("deleted_posts.txt", "a", encoding="utf-8") as f:
                    f.write(
                        f"{submission.title}, "
                        f"{created_at}, "
                        f"{deleted_at}, "
                        f"{submission.score}, "
                        f"{submission.subreddit.display_name}, "
                        f"ci\n"
                    )
                try:
                    submission.edit(".")
                    submission.delete()
                    posts_deleted += 1
                    print(f"  Deleted post '{submission.title}' (score={submission.score}) in r/{submission.subreddit}")
                except praw.exceptions.APIException as e:
                    print(f"  Error deleting post {submission.id}: {e}")

    if dry_run:
        print("\nDry run complete — nothing was deleted.")
    else:
        print(f"\nDone. Deleted {comments_deleted} comment(s) and {posts_deleted} post(s).")
        print("\nUploading logs to Google Drive…")
        maybe_upload_logs("deleted_comments.txt", "deleted_posts.txt")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly Reddit comment/post cleanup")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DRY_RUN", "0") == "1",
        help="Preview which items would be deleted without making any changes",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
