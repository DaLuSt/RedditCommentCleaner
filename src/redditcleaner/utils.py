"""Shared utilities for RedditCommentCleaner CLI scripts."""

import time
from datetime import datetime, timezone

import praw
import prawcore

_RETRY_WAIT = (5, 15, 45)


def _with_retry(fn, label="operation"):
    """Call fn(), retrying up to 3 times on rate-limit errors."""
    for attempt, wait in enumerate(_RETRY_WAIT, start=1):
        try:
            return fn()
        except prawcore.exceptions.TooManyRequests as exc:
            retry_after = getattr(exc, "retry_after", None) or wait
            print(f"  Rate limited on {label}. Waiting {retry_after}s (attempt {attempt}/3)…")
            time.sleep(retry_after)
        except praw.exceptions.APIException:
            raise
    return fn()


def get_reddit_credentials(credentials_file="Credentials.txt"):
    """Load credentials from file or fall back to interactive prompts.

    Args:
        credentials_file (str): Path to the file containing Reddit credentials.

    Returns:
        tuple: (client_id, client_secret, username, password)
    """
    try:
        with open(credentials_file, encoding="utf-8") as f:
            client_id = f.readline().strip()
            client_secret = f.readline().strip()
            username = f.readline().strip()
            password = f.readline().strip()
            return client_id, client_secret, username, password
    except FileNotFoundError:
        print("Error: Could not find the credentials file.")

    client_id = input("Enter your Reddit client ID: ")
    client_secret = input("Enter your Reddit client secret: ")
    username = input("Enter your Reddit username: ")
    password = input("Enter your Reddit password: ")
    return client_id, client_secret, username, password


def confirm_and_run():
    """Ask the user for confirmation to run the script.

    Returns:
        bool: True if the user confirms, False otherwise.
    """
    confirmation = input("Do you want to run the script? (yes/no): ")
    return confirmation.lower() in ("yes", "y")


def initialize_reddit(client_id, client_secret, username, password):
    """Initialize and return an authenticated Reddit instance.

    Args:
        client_id (str): Reddit client ID.
        client_secret (str): Reddit client secret.
        username (str): Reddit username.
        password (str): Reddit password.

    Returns:
        praw.Reddit: An authenticated Reddit instance.
    """
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent="commentCleaner",
            validate_on_submit=True,
        )
        reddit.user.me()
        print("Authenticated successfully.")
        return reddit
    except (
        praw.exceptions.APIException,
        prawcore.exceptions.OAuthException,
        prawcore.exceptions.ResponseException,
    ):
        print("Error: Could not authenticate with the provided credentials.")
        exit()


def build_deletion_record(item, item_type, source):
    """Serialize a deleted comment or submission into a JSON-loggable dict.

    Args:
        item: A PRAW Comment (item_type="comment") or Submission (item_type="post").
        item_type (str): "comment" or "post".
        source (str): Tag identifying which script/mode performed the deletion.

    Returns:
        dict: Ready to be passed to json.dumps().
    """
    record = {
        "deleted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_at": datetime.fromtimestamp(item.created_utc, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "id": item.name,
        "subreddit": str(item.subreddit),
        "score": item.score,
    }
    if item_type == "post":
        record["title"] = item.title
        record["permalink"] = f"https://reddit.com{item.permalink}"
        record["num_comments"] = item.num_comments
    else:
        record["permalink"] = f"https://reddit.com{item.permalink}"
        record["body"] = item.body
    record["source"] = source
    return record


def edit_and_delete(item, label):
    """Edit *item* to "." then delete it, retrying on rate limits.

    Args:
        item: A PRAW Comment or Submission.
        label (str): "comment" or "post" — used in retry log messages.
    """
    _with_retry(lambda: item.edit("."), f"{label} edit")
    _with_retry(item.delete, f"{label} delete")


def get_days_old(prompt="Enter how old (in days) the items should be: "):
    """Prompt the user for an age limit in days.

    Args:
        prompt (str): Custom prompt text.

    Returns:
        int: The number of days.
    """
    while True:
        days_old = input(prompt)
        try:
            return int(days_old)
        except ValueError:
            print("Error: Please enter a number.")
