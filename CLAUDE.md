# CLAUDE.md — AI Assistant Guide for RedditCommentCleaner

## Project Overview

RedditCommentCleaner is a Python tool that allows Reddit users to bulk-delete their own comments and posts using the [PRAW](https://praw.readthedocs.io/) (Python Reddit API Wrapper) library. Before deletion, each item is edited to `"."` to prevent content-scraping tools from capturing the original text.

It ships in three forms:
- **CLI scripts** — interactive terminal tools (`commentCleaner.py`, `PostCleaner.py`)
- **Web app** — browser-based dashboard for filtering and selectively deleting items (`web/`)
- **CI/CD** — automated weekly GitHub Actions run that deletes all items with score < 1

**Current version:** 1.8
**Language:** Python 3
**Dependencies:** `praw` (CLI/CI), `praw` + `flask` + `google-api-python-client` (web app)

---

## Repository Structure

```
RedditCommentCleaner/
├── commentCleaner.py              # CLI — comment deletion (3 modes)
├── PostCleaner.py                 # CLI — post/submission deletion
├── weekly_cleanup.py              # CI script — automated cleanup (score < 1)
├── web/
│   ├── app.py                     # Flask web application
│   ├── requirements.txt           # flask, praw
│   └── templates/
│       ├── index.html             # Login page
│       └── dashboard.html        # Main dashboard UI
├── .github/
│   └── workflows/
│       └── weekly-cleanup.yml     # GitHub Actions — runs weekly_cleanup.py
├── .gitignore
├── README.md
├── SECURITY.md
└── Credentials.txt                # (NOT in repo) User-supplied credentials
```

### Runtime-generated files (excluded by `.gitignore`)

| File | Created by | Contents |
|---|---|---|
| `deleted_comments.txt` | CLI scripts, web app, CI | `YYYY-MM-DD HH:MM:SS | score | body` |
| `deleted_posts.txt` | CLI scripts, web app, CI | `title, UTC datetime, score, subreddit` |
| `Credentials.txt` | User | Reddit API credentials (CLI use only) |

---

## Dependencies

### CLI scripts (`commentCleaner.py`, `PostCleaner.py`, `weekly_cleanup.py`)
```bash
pip install -r requirements.txt   # praw + google-api-python-client
```

### Web app (`web/`)
```bash
pip install -r web/requirements.txt   # flask + praw + google-api-python-client
```

No `pyproject.toml`, Poetry, or Pipenv files exist.

---

## Credentials

### For CLI scripts — `Credentials.txt`
Must contain exactly four lines (not committed; covered by `.gitignore`):
```
<client_id>
<client_secret>
<username>
<password>
```
If absent, both CLI scripts fall back to interactive `input()` prompts.

### For the web app
Credentials are entered via the login form and stored in a server-side Flask session for the duration of the browser session. They are never written to disk.

### For the web app (local)
Set as environment variables before running Flask:
```bash
export GOOGLE_SERVICE_ACCOUNT_KEY=/path/to/key.json   # or paste raw JSON
export GOOGLE_DRIVE_FOLDER_ID=<folder-id>
python web/app.py
```

### For GitHub Actions
Store as repository secrets (Settings → Secrets and variables → Actions):

| Secret name | Value |
|---|---|
| `REDDIT_CLIENT_ID` | Your script app client ID |
| `REDDIT_CLIENT_SECRET` | Your script app client secret |
| `REDDIT_USERNAME` | Your Reddit username |
| `REDDIT_PASSWORD` | Your Reddit password |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Raw JSON content of service account key *(optional)* |
| `GOOGLE_DRIVE_FOLDER_ID` | Drive folder ID *(optional)* |

---

## Scripts

### `commentCleaner.py`

Interactive CLI offering three deletion modes:

| Option | Action |
|--------|--------|
| 1 | Delete all comments older than N days |
| 2 | Delete all comments with score ≤ 0 |
| 3 | Delete comments with score ≤ 1, no replies, older than 7 days |

**Flow:** load credentials → confirm → authenticate → loop (choose mode → run → report) → quit

### `PostCleaner.py`

Single-pass CLI that deletes all posts older than N days.

**Flow:** load credentials → confirm → authenticate → prompt for age → `delete_old_posts`

### `weekly_cleanup.py`

Non-interactive script designed for CI. Reads credentials from environment variables and deletes all comments **and** posts with `score < 1`. Logs each deleted item to `deleted_comments.txt` / `deleted_posts.txt`.

---

## Web App (`web/`)

### Running

```bash
pip install -r web/requirements.txt
python web/app.py
# Open http://localhost:5000
```

### Routes

| Route | Method | Description |
|---|---|---|
| `/` | GET | Login page (redirects to dashboard if session active) |
| `/login` | POST | Authenticate and store credentials in session |
| `/logout` | GET | Clear session |
| `/dashboard` | GET | Main dashboard UI |
| `/api/items` | GET | JSON: all comments and posts for the authenticated user |
| `/api/delete` | POST | JSON body `{comment_ids, post_ids}` → delete and archive |

### Dashboard features

- **Load Items** — fetches all comments and posts via `/api/items`
- **Filters** — score ≤ N, age ≥ N days; "Select Matching" checks all rows that meet both criteria
- **Manual selection** — individual checkboxes, Select All / None buttons
- **Sortable tables** — click any column header; tabs switch between Comments and Posts
- **Delete Selected** — shows confirmation dialog, then POSTs to `/api/delete`; deleted rows are removed from the UI in-place

### Architecture notes

- `web/app.py` uses `os.path.dirname(__file__)` to locate the repo root, so log files are always written to the repo root regardless of which directory you run Flask from.
- Credentials are kept in a Flask session (server-side) and never sent to the browser.
- All PRAW calls are synchronous. For accounts with thousands of items, the initial `/api/items` request may take 30–60 seconds.

---

## Google Drive Integration

**Module:** `drive_upload.py`

All three entry points (CLI, web app, CI) call `maybe_upload_logs()` after writing deletion logs. The function is a no-op when the env vars are not set, so Drive is fully opt-in.

### Setup (one-time)

1. Open [Google Cloud Console](https://console.cloud.google.com) and create or select a project.
2. Enable the **Google Drive API** (APIs & Services → Library).
3. Create a **Service Account** (IAM & Admin → Service Accounts → Create).
4. On the service account, go to **Keys → Add Key → JSON** and download the file.
5. In Google Drive, create a folder and share it with the service account's email address (grant **Editor** access).
6. Copy the folder ID from the URL: `https://drive.google.com/drive/folders/<FOLDER_ID>`

### Environment variables

| Variable | Value |
|---|---|
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Path to JSON key file **or** the raw JSON string |
| `GOOGLE_DRIVE_FOLDER_ID` | The Drive folder ID |

If both variables are set, logs are uploaded (or updated in-place) after every deletion run. If either is missing, the upload step is silently skipped.

### Behaviour

- `deleted_comments.txt` and `deleted_posts.txt` are uploaded to the configured folder.
- If a file with the same name already exists in that folder it is **updated in-place** (no duplicates).
- The web dashboard shows clickable Drive links for 12 seconds after a successful deletion.

---

## GitHub Actions — Weekly Cleanup

**File:** `.github/workflows/weekly-cleanup.yml`

**Schedule:** Every Sunday at 00:00 UTC (`cron: '0 0 * * 0'`)

**Can also be triggered manually** from the Actions tab via `workflow_dispatch`.

**What it does:**
1. Checks out the repo
2. Installs `praw`
3. Runs `python weekly_cleanup.py` with Reddit credentials from repository secrets
4. Uploads `deleted_comments.txt` and `deleted_posts.txt` as workflow artifacts (retained 90 days)

**Criteria:** deletes all comments and posts where `score < 1` (i.e., 0 or negative).

---

## Known Bugs and Issues

These are pre-existing issues in the original codebase. Do not silently fix them without a deliberate change request.

1. **`PostCleaner.py` — double deletion and invalid method** (`delete_old_posts`, lines 102–116):
   `submission.delete()` is called before `submission.edit(".")`, then a second `try` block re-attempts both on an already-deleted object. `submission.append(submission)` is not a valid PRAW method and raises `AttributeError`. *(Separate PR: `claude/fix-postcleaner-bugs-7Wp79`)*

2. **`get_reddit_credentials` return-value inconsistency** (both CLI files):
   File-read path returns a 4-tuple; interactive fallback returns a 5-tuple with a spurious `validate_on_submit` element. *(Separate PR: `claude/fix-credentials-tuple-7Wp79`)*

3. **`remove_comments_with_one_karma_and_no_replies` — replies never populated:**
   PRAW does not populate `comment.replies` for listing results. Without `comment.refresh()`, the check always sees 0 replies and over-deletes. *(Separate PR: `claude/fix-comment-replies-refresh-7Wp79`)*

---

## Running Everything

```bash
# Interactive comment cleaner
python commentCleaner.py

# Interactive post cleaner
python PostCleaner.py

# Automated cleanup (CI-style, uses env vars)
REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=... REDDIT_USERNAME=... REDDIT_PASSWORD=... \
  python weekly_cleanup.py

# Web app
pip install -r web/requirements.txt
python web/app.py   # then open http://localhost:5000
```

---

## Development Conventions

- **Python version:** Python 3 (no pin; standard library uses `datetime`, `time`, `os`)
- **Style:** No linter config. Google-style docstrings (`Args:`, `Returns:`, `Notes:`).
- **No test suite.** Verify changes manually against a Reddit script-type developer app with a test account.
- **CI/CD:** GitHub Actions workflow added (`weekly-cleanup.yml`). No other pipelines.
- **Error handling:** PRAW API errors caught as `praw.exceptions.APIException`. Auth failure calls `exit()` in CLI scripts; returns HTTP 401 in the web app.
- **Encoding:** All file writes use `encoding="utf-8"` explicitly.
- **`user_agent`:** Hardcoded as `'commentCleaner'` everywhere.

---

## Reddit API Setup

1. Go to `https://www.reddit.com/prefs/apps`
2. Create a **script**-type app
3. Note the `client_id` (under the app name) and `client_secret`

---

## Branch and Contribution Notes

- Default upstream branch: `main`
- Feature branches follow the pattern `claude/<description>-<id>`
- Bug-fix PRs open against `main`; see open PRs for pending fixes
- Vulnerability reports: pull request or email (see `SECURITY.md`)
