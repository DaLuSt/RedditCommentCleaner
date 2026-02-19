# CLAUDE.md — AI Assistant Guide for RedditCommentCleaner

## Project Overview

RedditCommentCleaner is a small Python CLI tool that allows Reddit users to bulk-delete their own comments and posts using the [PRAW](https://praw.readthedocs.io/) (Python Reddit API Wrapper) library. Before deletion, each item is edited to `"."` to prevent content-scraping tools from capturing the original text.

**Current version:** 1.8
**Language:** Python 3
**Sole external dependency:** `praw`

---

## Repository Structure

```
RedditCommentCleaner/
├── commentCleaner.py   # Main script — comment deletion (3 modes)
├── PostCleaner.py      # Secondary script — post/submission deletion
├── README.md           # User-facing setup and usage guide
├── SECURITY.md         # Security policy and vulnerability reporting
└── Credentials.txt     # (NOT in repo) User-supplied credentials file
```

### Runtime-generated files (not in repo)

| File | Created by | Contents |
|---|---|---|
| `deleted_comments.txt` | `commentCleaner.py` | Timestamp, score, body for each deleted comment |
| `deleted_posts.txt` | `PostCleaner.py` | Title, date, score, subreddit for each deleted post |
| `Credentials.txt` | User | Reddit API credentials (see format below) |

---

## Dependencies

There is no `requirements.txt` or `pyproject.toml`. The single dependency is:

```
praw
```

Install with:
```bash
pip install praw
```

No other package manager files (Poetry, Pipenv, conda) exist in this project.

---

## Credentials File Format

`Credentials.txt` (not committed to the repo) must contain exactly four lines:

```
<client_id>
<client_secret>
<username>
<password>
```

If the file is absent, both scripts fall back to interactive `input()` prompts.

> **Security note:** `Credentials.txt` must never be committed to version control. It is not in `.gitignore` currently — take care not to accidentally stage it.

---

## Scripts

### `commentCleaner.py`

Interactive CLI that offers three deletion modes:

| Option | Action |
|--------|--------|
| 1 | Delete all comments older than N days |
| 2 | Delete all comments with a score ≤ 0 |
| 3 | Delete comments with score ≤ 1, no replies, and older than 7 days |

**Flow:**
1. Load credentials (`get_reddit_credentials`)
2. Ask for confirmation (`confirm_and_run`)
3. Authenticate with Reddit (`initialize_reddit`)
4. Loop: choose action → execute → report count → repeat until option 4 (Quit)

Before each deletion the comment is edited to `"."` via `comment.edit(".")`, then `comment.delete()` is called. This is the standard approach to prevent archiving.

Each deleted comment is appended to `deleted_comments.txt` as:
```
YYYY-MM-DD HH:MM:SS | <score> | <body>
```

### `PostCleaner.py`

Simpler single-pass script that deletes all posts older than N days.

**Flow:**
1. Load credentials
2. Confirm
3. Authenticate
4. Prompt for age threshold
5. Call `delete_old_posts` — iterates all user submissions, deletes those older than the threshold

Each deleted post is recorded in `deleted_posts.txt` as:
```
<title>, <UTC datetime>, <score>, <subreddit>
```

---

## Known Bugs and Issues

These are pre-existing issues in the codebase. Do not silently fix them without a deliberate change request, as they may affect expected behavior:

1. **`PostCleaner.py` — double deletion and wrong append (`delete_old_posts`, line 102–116):**
   A submission is deleted with `submission.delete()` at line 104, then the `try` block at lines 111–116 attempts `submission.edit(".")` and `submission.delete()` again on an already-deleted object. Line 113 calls `submission.append(submission)` which is not a valid `Submission` method and will raise `AttributeError` at runtime.

2. **`get_reddit_credentials` return-value inconsistency (both files):**
   When credentials are read from the file, the function returns a 4-tuple. When falling back to interactive input, it returns a 5-tuple (with `validate_on_submit`). The `main()` functions unpack only 4 values, so the interactive fallback path silently discards the extra value. The `validate_on_submit=True` line inside the function body is a dead assignment and has no effect.

3. **`remove_comments_with_one_karma_and_no_replies` — replies not loaded:**
   `comment.replies` on a `Comment` object returned by `.comments.new()` is not automatically populated by PRAW. Without calling `comment.refresh()` first, `len(comment.replies)` will always be `0`, causing this mode to over-delete.

---

## Running the Scripts

```bash
# Comment cleaner (interactive menu)
python commentCleaner.py

# Post cleaner
python PostCleaner.py
```

Both scripts are synchronous, blocking, and designed for interactive terminal use. They do not accept command-line arguments.

---

## Development Conventions

- **Python version:** Python 3 (no version pin specified; standard library only uses `datetime`, `time`)
- **Style:** No linter configuration exists. Code uses Google-style docstrings with `Args:`, `Returns:`, and `Notes:` sections.
- **No test suite:** There are no unit or integration tests. Any changes should be manually verified against a Reddit developer app (script type) with a test account.
- **No CI/CD:** No GitHub Actions or other pipeline configuration is present.
- **Error handling:** API errors are caught as `praw.exceptions.APIException`. Authentication failure calls `exit()` directly.
- **Encoding:** `deleted_posts.txt` is opened with `encoding="utf-8"`. `deleted_comments.txt` uses default system encoding — be consistent and prefer explicit `encoding="utf-8"` in new code.

---

## Reddit API Setup Requirements

1. Go to `https://www.reddit.com/prefs/apps`
2. Create a **script**-type app
3. Note the `client_id` (shown under the app name) and `client_secret`
4. The `user_agent` is hardcoded as `'commentCleaner'` in both scripts

---

## Branch and Contribution Notes

- The default upstream branch is `main` (tracked as `origin/main`)
- Feature branches follow the pattern `claude/<description>-<id>`
- No pull request template or contributing guide exists; open issues or PRs on GitHub for changes
- Vulnerability reports should be submitted as pull requests or via email (see `SECURITY.md`)
