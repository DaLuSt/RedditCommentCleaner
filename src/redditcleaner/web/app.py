import json
import os
from datetime import datetime, timezone

import praw
import prawcore
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect

from redditcleaner.utils import build_deletion_record, edit_and_delete

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(24)
csrf = CSRFProtect(app)

# Log files are written to LOG_DIR (defaults to current working directory)
LOG_DIR = os.environ.get("LOG_DIR", os.getcwd())
DELETED_COMMENTS_FILE = os.path.join(LOG_DIR, "deleted_comments.txt")
DELETED_POSTS_FILE = os.path.join(LOG_DIR, "deleted_posts.txt")


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
    except (
        praw.exceptions.APIException,
        prawcore.exceptions.OAuthException,
        prawcore.exceptions.ResponseException,
    ) as e:
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
@csrf.exempt
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
            "created_date": datetime.fromtimestamp(
                c.created_utc, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
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
            "created_date": datetime.fromtimestamp(
                s.created_utc, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
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

    with open(DELETED_COMMENTS_FILE, "a", encoding="utf-8") as cf:
        for cid in comment_ids:
            try:
                comment = reddit.comment(cid)
                cf.write(json.dumps(build_deletion_record(comment, "comment", "web")) + "\n")
                edit_and_delete(comment, "comment")
                deleted_comments += 1
            except (
                praw.exceptions.APIException,
                prawcore.exceptions.PrawcoreException,
            ) as e:
                errors.append(f"Comment {cid}: {e}")

    with open(DELETED_POSTS_FILE, "a", encoding="utf-8") as pf:
        for pid in post_ids:
            try:
                submission = reddit.submission(pid)
                pf.write(json.dumps(build_deletion_record(submission, "post", "web")) + "\n")
                edit_and_delete(submission, "post")
                deleted_posts += 1
            except (
                praw.exceptions.APIException,
                prawcore.exceptions.PrawcoreException,
            ) as e:
                errors.append(f"Post {pid}: {e}")

    return jsonify(
        deleted_comments=deleted_comments,
        deleted_posts=deleted_posts,
        errors=errors,
    )


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5000)
