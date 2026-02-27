import json
import os
import sys
from datetime import datetime

import praw
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(24)

# Log files are kept at the repo root, not inside web/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Allow importing drive_upload from the repo root
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from drive_upload import maybe_upload_logs  # noqa: E402
DELETED_COMMENTS_FILE = os.path.join(BASE_DIR, "deleted_comments.txt")
DELETED_POSTS_FILE = os.path.join(BASE_DIR, "deleted_posts.txt")


def make_reddit():
    return praw.Reddit(
        client_id=session["client_id"],
        client_secret=session["client_secret"],
        username=session["username"],
        password=session["password"],
        user_agent="commentCleaner",
        validate_on_submit=True,
    )


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    creds = {
        "client_id": request.form.get("client_id", "").strip(),
        "client_secret": request.form.get("client_secret", "").strip(),
        "username": request.form.get("username", "").strip(),
        "password": request.form.get("password", "").strip(),
    }
    try:
        reddit = praw.Reddit(
            **creds,
            user_agent="commentCleaner",
            validate_on_submit=True,
        )
        reddit.user.me()
        session.update(creds)
        return redirect(url_for("dashboard"))
    except Exception as e:
        return render_template("index.html", error=f"Authentication failed: {e}")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("index"))
    return render_template("dashboard.html", username=session["username"])


@app.route("/api/items")
def api_items():
    if "username" not in session:
        return jsonify(error="Not authenticated"), 401

    reddit = make_reddit()
    username = session["username"]

    comments = []
    for c in reddit.redditor(username).comments.new(limit=None):
        comments.append({
            "id": c.id,
            "type": "comment",
            "body": c.body[:300],
            "score": c.score,
            "subreddit": str(c.subreddit),
            "created_utc": int(c.created_utc),
            "created_date": datetime.utcfromtimestamp(c.created_utc).strftime("%Y-%m-%d"),
            "permalink": "https://reddit.com" + c.permalink,
        })

    posts = []
    for s in reddit.redditor(username).submissions.new(limit=None):
        posts.append({
            "id": s.id,
            "type": "post",
            "title": s.title,
            "score": s.score,
            "subreddit": str(s.subreddit),
            "created_utc": int(s.created_utc),
            "created_date": datetime.utcfromtimestamp(s.created_utc).strftime("%Y-%m-%d"),
            "num_comments": s.num_comments,
            "permalink": "https://reddit.com" + s.permalink,
        })

    return jsonify(comments=comments, posts=posts)


@app.route("/api/delete", methods=["POST"])
def api_delete():
    if "username" not in session:
        return jsonify(error="Not authenticated"), 401

    data = request.get_json()
    comment_ids = data.get("comment_ids", [])
    post_ids = data.get("post_ids", [])

    reddit = make_reddit()
    deleted_comments = 0
    deleted_posts = 0
    errors = []

    for cid in comment_ids:
        try:
            comment = reddit.comment(cid)
            with open(DELETED_COMMENTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "deleted_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "created_at": datetime.utcfromtimestamp(comment.created_utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "id": comment.name,
                    "subreddit": str(comment.subreddit),
                    "score": comment.score,
                    "permalink": f"https://reddit.com{comment.permalink}",
                    "body": comment.body,
                    "source": "web",
                }) + "\n")
            comment.edit(".")
            comment.delete()
            deleted_comments += 1
        except Exception as e:
            errors.append(f"Comment {cid}: {e}")

    for pid in post_ids:
        try:
            submission = reddit.submission(pid)
            with open(DELETED_POSTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "deleted_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "created_at": datetime.utcfromtimestamp(submission.created_utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "id": submission.name,
                    "subreddit": submission.subreddit.display_name,
                    "score": submission.score,
                    "title": submission.title,
                    "permalink": f"https://reddit.com{submission.permalink}",
                    "num_comments": submission.num_comments,
                    "source": "web",
                }) + "\n")
            submission.edit(".")
            submission.delete()
            deleted_posts += 1
        except Exception as e:
            errors.append(f"Post {pid}: {e}")

    drive_links = maybe_upload_logs(DELETED_COMMENTS_FILE, DELETED_POSTS_FILE)

    return jsonify(
        deleted_comments=deleted_comments,
        deleted_posts=deleted_posts,
        errors=errors,
        drive_links=drive_links,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
