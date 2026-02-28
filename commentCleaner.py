import argparse
import json
import time
from datetime import datetime, timedelta, timezone

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


def delete_old_comments(reddit, username, days_old, comments_deleted, *, dry_run=False):
    """
    Delete comments older than a specified number of days.

    Args:
        reddit (praw.Reddit): Authenticated Reddit instance.
        username (str): Reddit username.
        days_old (int): Age limit for comments (in days).
        comments_deleted (list): A list to store deleted comments.
        dry_run (bool): If True, log matches but do not delete.

    Notes:
        Since comments.new() is sorted newest-first, once a comment that meets
        the age threshold is encountered every subsequent comment does too.
        A ``past_cutoff`` flag skips redundant age checks after that transition.
    """
    threshold_secs = days_old * 24 * 60 * 60
    now = time.time()
    past_cutoff = False

    with open("deleted_comments.txt", "a", encoding="utf-8") as log_file:
        for n, comment in enumerate(
            reddit.redditor(username).comments.new(limit=None), 1
        ):
            print(f"\r  Scanning… {n} comment(s) fetched", end="", flush=True)

            if not past_cutoff:
                if now - comment.created_utc <= threshold_secs:
                    continue  # too new; older comments follow later in the stream
                past_cutoff = True  # all subsequent comments are also old enough

            if dry_run:
                print(
                    f"\n  [DRY RUN] Would delete (score={comment.score})"
                    f" in r/{comment.subreddit}: {comment.body[:60]!r}"
                )
                comments_deleted.append(comment)
                continue

            log_file.write(
                json.dumps({
                    "deleted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "created_at": datetime.fromtimestamp(
                        comment.created_utc, tz=timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "id": comment.name,
                    "subreddit": str(comment.subreddit),
                    "score": comment.score,
                    "permalink": f"https://reddit.com{comment.permalink}",
                    "body": comment.body,
                    "source": "cli-mode-1",
                }) + "\n"
            )
            try:
                _with_retry(lambda: comment.edit("."), "comment edit")
                _with_retry(comment.delete, "comment delete")
                comments_deleted.append(comment)
            except (praw.exceptions.APIException, prawcore.exceptions.TooManyRequests) as e:
                print(f"\n  Error deleting comment: {e}")

    print()  # newline after the progress counter


def remove_comments_with_negative_karma(reddit, username, comments_deleted, *, dry_run=False):
    """
    Remove comments with negative karma.

    Args:
        reddit (praw.Reddit): Authenticated Reddit instance.
        username (str): Reddit username.
        comments_deleted (list): A list to store deleted comments.
        dry_run (bool): If True, log matches but do not delete.

    Notes:
        This function will remove comments with a negative karma score.
    """
    with open("deleted_comments.txt", "a", encoding="utf-8") as log_file:
        for n, comment in enumerate(
            reddit.redditor(username).comments.new(limit=None), 1
        ):
            print(f"\r  Scanning… {n} comment(s) fetched", end="", flush=True)

            if comment.score > 0:
                continue

            if dry_run:
                print(
                    f"\n  [DRY RUN] Would delete (score={comment.score})"
                    f" in r/{comment.subreddit}: {comment.body[:60]!r}"
                )
                comments_deleted.append(comment)
                continue

            log_file.write(
                json.dumps({
                    "deleted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "created_at": datetime.fromtimestamp(
                        comment.created_utc, tz=timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "id": comment.name,
                    "subreddit": str(comment.subreddit),
                    "score": comment.score,
                    "permalink": f"https://reddit.com{comment.permalink}",
                    "body": comment.body,
                    "source": "cli-mode-2",
                }) + "\n"
            )
            try:
                _with_retry(lambda: comment.edit("."), "comment edit")
                _with_retry(comment.delete, "comment delete")
                comments_deleted.append(comment)
            except (praw.exceptions.APIException, prawcore.exceptions.TooManyRequests) as e:
                print(f"\n  Error removing comment: {e}")

    print()


def remove_comments_with_one_karma_and_no_replies(
    reddit, username, comments_deleted, *, dry_run=False
):
    """
    Remove comments with one karma, no replies, and are at least a week old.

    Args:
        reddit (praw.Reddit): Authenticated Reddit instance.
        username (str): Reddit username.
        comments_deleted (list): A list to store deleted comments.
        dry_run (bool): If True, log matches but do not delete.

    Notes:
        comment.refresh() is called so that comment.replies is populated;
        PRAW does not fill it for listing results without an explicit refresh.
    """
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    with open("deleted_comments.txt", "a", encoding="utf-8") as log_file:
        for n, comment in enumerate(
            reddit.redditor(username).comments.new(limit=None), 1
        ):
            print(f"\r  Scanning… {n} comment(s) fetched", end="", flush=True)

            # comment.replies is not populated by default; refresh() fetches the full thread
            comment.refresh()
            created = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc)
            if not (comment.score <= 1 and len(comment.replies) == 0 and created < one_week_ago):
                continue

            if dry_run:
                print(
                    f"\n  [DRY RUN] Would delete (score={comment.score})"
                    f" in r/{comment.subreddit}: {comment.body[:60]!r}"
                )
                comments_deleted.append(comment)
                continue

            log_file.write(
                json.dumps({
                    "deleted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "id": comment.name,
                    "subreddit": str(comment.subreddit),
                    "score": comment.score,
                    "permalink": f"https://reddit.com{comment.permalink}",
                    "body": comment.body,
                    "source": "cli-mode-3",
                }) + "\n"
            )
            try:
                _with_retry(lambda: comment.edit("."), "comment edit")
                _with_retry(comment.delete, "comment delete")
                comments_deleted.append(comment)
            except (praw.exceptions.APIException, prawcore.exceptions.TooManyRequests) as e:
                print(f"\n  Error removing comment: {e}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Interactive Reddit comment cleaner")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which comments would be deleted without making any changes",
    )
    args = parser.parse_args()

    client_id, client_secret, username, password = get_reddit_credentials()

    if not confirm_and_run():
        print("Script aborted.")
        return

    reddit = initialize_reddit(client_id, client_secret, username, password)

    comments_deleted = []

    while True:
        action = input(
            "Choose an action"
            " (1 - Delete old comments,"
            " 2 - Remove comments with negative karma,"
            " 3 - Remove comments with 1 karma and no replies,"
            " 4 - Quit): "
        )

        if action == "1":
            days_old = get_days_old("Enter how old (in days) the comments should be: ")
            print(f"Working (Deleting comments older than {days_old} day(s))…")
            delete_old_comments(
                reddit, username, days_old, comments_deleted, dry_run=args.dry_run
            )
        elif action == "2":
            print("Working (Removing comments with negative karma)…")
            remove_comments_with_negative_karma(
                reddit, username, comments_deleted, dry_run=args.dry_run
            )
        elif action == "3":
            print("Working (Removing comments with 1 karma and no replies)…")
            remove_comments_with_one_karma_and_no_replies(
                reddit, username, comments_deleted, dry_run=args.dry_run
            )
        elif action == "4":
            break
        else:
            print("Invalid choice. Please select a valid option.")
            continue

        time.sleep(1)

        if comments_deleted:
            label = "would delete" if args.dry_run else "deleted"
            print(f"The script {label} {len(comments_deleted)} comment(s).")
            if not args.dry_run:
                maybe_upload_logs("deleted_comments.txt")
            comments_deleted = []
        else:
            print("There were no comments to delete.")


if __name__ == "__main__":
    main()
