import praw
import prawcore
import time
from datetime import datetime

from drive_upload import maybe_upload_logs

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
    """
    Prompt the user to input Reddit client credentials.

    Args:
        credentials_file (str): Path to the file containing Reddit client credentials.

    Returns:
        tuple: A tuple containing client_id, client_secret, username, and password.
    """
    try:
        with open(credentials_file, 'r') as f:
            client_id = f.readline().strip()
            client_secret = f.readline().strip()
            username = f.readline().strip()
            password = f.readline().strip()
            return client_id, client_secret, username, password
    except FileNotFoundError:
        print("Error: Could not find the credentials file.")

    # If file reading fails or file is not found, prompt the user to input credentials manually
    client_id = input("Enter your Reddit client ID: ")
    client_secret = input("Enter your Reddit client secret: ")
    username = input("Enter your Reddit username: ")
    password = input("Enter your Reddit password: ")

    return client_id, client_secret, username, password

def confirm_and_run():
    """
    Ask the user for confirmation to run the script.

    Returns:
        bool: True if the user confirms, False otherwise.
    """
    confirmation = input("Do you want to run the script? (yes/no): ")
    return confirmation.lower() == 'yes' or confirmation.lower() == 'y'

def initialize_reddit(client_id, client_secret, username, password):
    """
    Initialize the Reddit instance with user credentials.

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
            user_agent='commentCleaner',
            validate_on_submit=True 
        )
        reddit.user.me()
        print("Authenticated successfully.")
        return reddit
    except praw.exceptions.APIException:
        print("Error: Could not authenticate with the provided credentials.")
        exit()
        
        
def get_days_old():
    """
    Prompt the user to input the age limit for comments.

    Returns:
        int: The number of days for the age limit.
    """
    while True:
        days_old = input("Enter how old (in days) the post should be: ")
        try:
            days_old = int(days_old)
            return days_old
        except ValueError:
            print("Error: Please enter a number.")


def delete_old_posts(reddit, username, days_old, posts_deleted):
    """
    Delete posts older than a specified number of days.

    Args:
        reddit (praw.Reddit): An authenticated Reddit instance.
        username (str): Reddit username.
        days_old (int): The age limit for posts.
        posts_deleted (int): The number of posts deleted.
    """
    for submission in reddit.redditor(username).submissions.new(limit=None):
        if submission.created_utc < (time.time() - (days_old * 86400)):
            # save post title, date, karma, and subreddit deleted to a file with utf-8 encoding
            with open("deleted_posts.txt", "a", encoding="utf-8") as f:
                f.write(f"{submission.title}, {datetime.utcfromtimestamp(submission.created_utc)}, {submission.score}, {submission.subreddit.display_name}\n")
            try:
                _with_retry(lambda: submission.edit("."), "post edit")
                _with_retry(submission.delete, "post delete")
                posts_deleted += 1
                print(f"Deleted post: {submission.title}")
            except (praw.exceptions.APIException, prawcore.exceptions.TooManyRequests) as e:
                print(f"Error removing post: {e}")

    print(f"Deleted {posts_deleted} posts.")

        
def main():
    client_id, client_secret, username, password = get_reddit_credentials()

    if not confirm_and_run():
        print("Script aborted.")
        return

    reddit = initialize_reddit(client_id, client_secret, username, password)
    days_old = get_days_old()
    posts_deleted = 0
    delete_old_posts(reddit, username, days_old, posts_deleted)
    maybe_upload_logs("deleted_posts.txt")


if __name__ == "__main__":
    main()