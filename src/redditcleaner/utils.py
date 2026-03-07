"""Shared utilities for RedditCommentCleaner CLI scripts."""

import time

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
        with open(credentials_file, "r") as f:
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
