"""
Weekly automated cleanup script for GitHub Actions.

Reads credentials from environment variables and deletes all comments
and posts with a score < 1, archiving each to a log file first.

Required environment variables:
    REDDIT_CLIENT_ID
    REDDIT_CLIENT_SECRET
    REDDIT_USERNAME
    REDDIT_PASSWORD

Optional environment variables (Google Drive upload):
    GOOGLE_SERVICE_ACCOUNT_KEY  path to service-account JSON, or the JSON string itself
    GOOGLE_DRIVE_FOLDER_ID      ID of the Drive folder to upload logs into
"""

import os
from datetime import datetime

import praw

from drive_upload import maybe_upload_logs


def main():
    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
        user_agent="commentCleaner",
        validate_on_submit=True,
    )

    username = os.environ["REDDIT_USERNAME"]
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

    # ── Google Drive upload ────────────────────────────────────────────────
    print("\nUploading logs to Google Drive…")
    maybe_upload_logs("deleted_comments.txt", "deleted_posts.txt")


if __name__ == "__main__":
    main()
