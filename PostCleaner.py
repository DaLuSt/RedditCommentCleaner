import argparse
import json
import time
from datetime import datetime, timezone

import praw
import prawcore

from drive_upload import maybe_upload_logs
from utils import (
    _with_retry,
    confirm_and_run,
    get_days_old,
    get_reddit_credentials,
    initialize_reddit,
)


def delete_old_posts(reddit, username, days_old, *, dry_run=False):
    """
    Delete posts older than a specified number of days.

    Args:
        reddit (praw.Reddit): An authenticated Reddit instance.
        username (str): Reddit username.
        days_old (int): The age limit for posts.
        dry_run (bool): If True, log matches but do not delete.

    Returns:
        int: The number of posts successfully deleted (or matched in dry-run).
    """
    threshold = time.time() - days_old * 86400
    posts_deleted = 0

    with open("deleted_posts.txt", "a", encoding="utf-8") as log_file:
        for n, submission in enumerate(
            reddit.redditor(username).submissions.new(limit=None), 1
        ):
            print(f"\r  Scanning… {n} post(s) fetched", end="", flush=True)

            if submission.created_utc >= threshold:
                continue  # too new

            if dry_run:
                print(
                    f"\n  [DRY RUN] Would delete '{submission.title}'"
                    f" (score={submission.score}) in r/{submission.subreddit}"
                )
                posts_deleted += 1
                continue

            log_file.write(
                json.dumps({
                    "deleted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "created_at": datetime.fromtimestamp(
                        submission.created_utc, tz=timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "id": submission.name,
                    "subreddit": submission.subreddit.display_name,
                    "score": submission.score,
                    "title": submission.title,
                    "permalink": f"https://reddit.com{submission.permalink}",
                    "num_comments": submission.num_comments,
                    "source": "cli",
                }) + "\n"
            )
            try:
                _with_retry(lambda: submission.edit("."), "post edit")
                _with_retry(submission.delete, "post delete")
                posts_deleted += 1
                print(f"\n  Deleted post: {submission.title}")
            except (praw.exceptions.APIException, prawcore.exceptions.TooManyRequests) as e:
                print(f"\n  Error removing post: {e}")

    print()  # newline after the progress counter
    label = "would delete" if dry_run else "Deleted"
    print(f"{label} {posts_deleted} post(s).")
    return posts_deleted


def main():
    parser = argparse.ArgumentParser(description="Interactive Reddit post cleaner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which posts would be deleted without making any changes",
    )
    args = parser.parse_args()

    client_id, client_secret, username, password = get_reddit_credentials()

    if not confirm_and_run():
        print("Script aborted.")
        return

    reddit = initialize_reddit(client_id, client_secret, username, password)
    days_old = get_days_old("Enter how old (in days) the posts should be: ")
    delete_old_posts(reddit, username, days_old, dry_run=args.dry_run)
    if not args.dry_run:
        maybe_upload_logs("deleted_posts.txt")


if __name__ == "__main__":
    main()
