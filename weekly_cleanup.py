"""
Weekly automated cleanup script for GitHub Actions.

Reads credentials from environment variables and deletes all comments
and posts with a score < 1, archiving each to a log file first.

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
from datetime import datetime

import praw


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
            lines = [l.strip() for l in f.readlines()]
        if len(lines) >= 4:
            return lines[0], lines[1], lines[2], lines[3]

    raise RuntimeError(
        "Reddit credentials not found. Set REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET / "
        "REDDIT_USERNAME / REDDIT_PASSWORD environment variables, or create Credentials.txt."
    )


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
    print(f"Criteria: score < 1\n")

    # ── Comments ──────────────────────────────────────────────────────────
    comments_deleted = 0
    print("Scanning comments…")
    for comment in reddit.redditor(username).comments.new(limit=None):
        if comment.score < 1:
            date_str = datetime.utcfromtimestamp(comment.created_utc).strftime("%Y-%m-%d %H:%M:%S")
            with open("deleted_comments.txt", "a", encoding="utf-8") as f:
                f.write(f"{date_str} | {comment.score} | {comment.body}\n")
            try:
                comment.edit(".")
                comment.delete()
                comments_deleted += 1
                print(f"  Deleted comment ({comment.score}) in r/{comment.subreddit}")
            except praw.exceptions.APIException as e:
                print(f"  Error deleting comment {comment.id}: {e}")

    # ── Posts ─────────────────────────────────────────────────────────────
    posts_deleted = 0
    print("\nScanning posts…")
    for submission in reddit.redditor(username).submissions.new(limit=None):
        if submission.score < 1:
            with open("deleted_posts.txt", "a", encoding="utf-8") as f:
                f.write(
                    f"{submission.title}, "
                    f"{datetime.utcfromtimestamp(submission.created_utc)}, "
                    f"{submission.score}, "
                    f"{submission.subreddit.display_name}\n"
                )
            try:
                submission.edit(".")
                submission.delete()
                posts_deleted += 1
                print(f"  Deleted post '{submission.title}' ({submission.score}) in r/{submission.subreddit}")
            except praw.exceptions.APIException as e:
                print(f"  Error deleting post {submission.id}: {e}")

    print(f"\nDone. Deleted {comments_deleted} comment(s) and {posts_deleted} post(s).")


if __name__ == "__main__":
    main()
