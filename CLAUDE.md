# CLAUDE.md — AI Assistant Guide for RedditCommentCleaner

## Project Overview

RedditCommentCleaner is a Python tool that allows Reddit users to bulk-delete their own comments and posts using the [PRAW](https://praw.readthedocs.io/) (Python Reddit API Wrapper) library. Before deletion, each item is edited to `"."` to prevent content-scraping tools from capturing the original text.

It ships in four forms:
- **CLI scripts** — interactive terminal tools (`commentCleaner.py`, `PostCleaner.py`)
- **Web app** — browser-based dashboard for filtering and selectively deleting items (`web/`)
- **Android app** — native Kotlin app with OAuth PKCE flow (`android/`)
- **CI/CD** — automated weekly GitHub Actions run that deletes all items with score < 1

**Current version:** 1.8
**Language:** Python 3 (CLI/web/CI), Kotlin (Android)
**Dependencies:** `praw` (CLI/CI), `praw` + `flask` + `flask-wtf` (web app)

---

## Repository Structure

```
RedditCommentCleaner/
├── commentCleaner.py              # CLI — comment deletion (3 modes)
├── PostCleaner.py                 # CLI — post/submission deletion
├── weekly_cleanup.py              # CI script — automated cleanup (score < 1)
├── utils.py                       # Shared: _with_retry, credentials, reddit init
├── drive_upload.py                # Optional Google Drive log upload helper
├── requirements.txt               # CLI/CI deps: praw, google-api-python-client
├── web/
│   ├── app.py                     # Flask web application (CSRF-protected)
│   ├── requirements.txt           # flask, flask-wtf, praw, google-api-*
│   └── templates/
│       ├── index.html             # Login page
│       └── dashboard.html         # Main dashboard UI
├── android/                       # Native Android app (Kotlin + OAuth PKCE)
│   ├── SETUP.md                   # Build and run instructions
│   └── app/src/main/java/com/redditcommentcleaner/
│       ├── auth/                  # LoginActivity, OAuthCallbackActivity
│       ├── api/                   # RedditApiClient, RedditApiService
│       ├── dashboard/             # DashboardActivity, DashboardViewModel
│       └── util/                  # TokenStorage, PkceHelper
├── scripts/
│   └── backfill_drive_upload.py   # Upload all historical GitHub Actions artifacts to Drive
├── tests/
│   └── requirements.txt           # pytest, pytest-mock, flask, praw
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
| `deleted_comments.txt` | CLI scripts, web app, CI | JSON lines — one object per deleted comment |
| `deleted_posts.txt` | CLI scripts, web app, CI | JSON lines — one object per deleted post |
| `Credentials.txt` | User | Reddit API credentials (CLI use only) |

---

## Dependencies

### CLI scripts (`commentCleaner.py`, `PostCleaner.py`, `weekly_cleanup.py`)
```bash
pip install -r requirements.txt   # praw + google-api-python-client (Drive is optional)
```

### Web app (`web/`)
```bash
pip install -r web/requirements.txt   # flask, flask-wtf, praw, google-api-*
```

### Tests
```bash
pip install -r tests/requirements.txt   # pytest, pytest-mock, flask, praw
```

No `pyproject.toml`, Poetry, or Pipenv files exist.

---

## Shared Module — `utils.py`

`utils.py` (repo root) is imported by both CLI scripts and `web/app.py`. It contains:

| Symbol | Purpose |
|--------|---------|
| `_with_retry(fn, label)` | Calls `fn()`, retrying up to 3 times on `TooManyRequests` |
| `get_reddit_credentials()` | Reads `Credentials.txt` or falls back to `input()` prompts |
| `confirm_and_run()` | Asks the user yes/no before running |
| `initialize_reddit(...)` | Creates and verifies a PRAW Reddit instance; catches `OAuthException` and `ResponseException` in addition to `APIException` |
| `get_days_old(prompt)` | Prompts for an integer age threshold |

`web/app.py` adds `BASE_DIR` to `sys.path` before importing `utils` (the same mechanism used for `drive_upload`).

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

### For GitHub Actions
Store as repository secrets (Settings → Secrets and variables → Actions):

| Secret name | Value |
|---|---|
| `REDDIT_CLIENT_ID` | Your script app client ID |
| `REDDIT_CLIENT_SECRET` | Your script app client secret |
| `REDDIT_USERNAME` | Your Reddit username |
| `REDDIT_PASSWORD` | Your Reddit password |

---

## Scripts

### `commentCleaner.py`

Interactive CLI offering three deletion modes:

| Option | Action |
|--------|--------|
| 1 | Delete all comments older than N days |
| 2 | Delete all comments with score ≤ 0 |
| 3 | Delete comments with score ≤ 1, no replies, older than 7 days |

Supports `--dry-run` flag to preview deletions without making changes.

**Flow:** load credentials → confirm → authenticate → loop (choose mode → run → report) → quit

### `PostCleaner.py`

Single-pass CLI that deletes all posts older than N days.

Supports `--dry-run` flag.

**Flow:** load credentials → confirm → authenticate → prompt for age → `delete_old_posts`

### `weekly_cleanup.py`

Non-interactive script designed for CI. Reads credentials from environment variables and deletes all comments **and** posts with `score < 1` or `score == 1` AND older than 14 days. Logs each deleted item to `deleted_comments.txt` / `deleted_posts.txt`.

Supports `--dry-run` flag (or `DRY_RUN=1` env var).

### `scripts/backfill_drive_upload.py`

One-off utility that downloads every historical `deletion-logs-*` artifact from the GitHub Actions workflow and uploads them to Google Drive with dated filenames. Requires the `gh` CLI authenticated and the `GOOGLE_SERVICE_ACCOUNT_KEY` / `GOOGLE_DRIVE_FOLDER_ID` env vars.

```bash
python scripts/backfill_drive_upload.py
```

---

## Web App (`web/`)

### Running

```bash
pip install -r web/requirements.txt
python web/app.py
# Open http://localhost:5000
```

To enable debug mode: `FLASK_DEBUG=1 python web/app.py`

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
- CSRF protection is provided by **Flask-WTF** (`CSRFProtect`). The login form includes a hidden `csrf_token` field; the dashboard's `fetch('/api/delete')` call sends the token in the `X-CSRFToken` header (read from the `<meta name="csrf-token">` tag).
- All PRAW calls are synchronous. For accounts with thousands of items, the initial `/api/items` request may take 30–60 seconds.

---

## Android App (`android/`)

A native Kotlin app that mirrors the web app's functionality. See `android/SETUP.md` for full build instructions.

Key characteristics:
- Uses **OAuth PKCE** (installed-app flow) — no client secret needed
- Tokens stored in **EncryptedSharedPreferences**
- Edit → delete performed for each item before removal (same scraping prevention as the Python tools)
- Requires registering an **installed app** at `https://www.reddit.com/prefs/apps` (redirect URI: `redditcommentcleaner://auth`)

---

## GitHub Actions — Weekly Cleanup

**File:** `.github/workflows/weekly-cleanup.yml`

**Schedule:** Every Sunday at 00:00 UTC (`cron: '0 0 * * 0'`)

**Can also be triggered manually** from the Actions tab via `workflow_dispatch`.

**What it does:**
1. Checks out the repo
2. Installs dependencies from `requirements.txt`
3. Runs `python weekly_cleanup.py` with Reddit credentials from repository secrets
4. Uploads `deleted_comments.txt` and `deleted_posts.txt` as workflow artifacts (retained 90 days)

**Criteria:** deletes all comments and posts where `score < 1` OR (`score == 1` AND older than 14 days).

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

# Dry-run preview (no deletions)
python commentCleaner.py --dry-run

# Interactive post cleaner
python PostCleaner.py

# Automated cleanup (CI-style, uses env vars)
REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=... REDDIT_USERNAME=... REDDIT_PASSWORD=... \
  python weekly_cleanup.py

# Dry-run the CI cleanup
python weekly_cleanup.py --dry-run

# Web app
pip install -r web/requirements.txt
python web/app.py   # then open http://localhost:5000

# Run tests
pip install -r tests/requirements.txt
pytest tests/
```

---

## Development Conventions

- **Python version:** Python 3 (no pin; standard library uses `datetime`, `time`, `os`)
- **Style:** No linter config. Google-style docstrings (`Args:`, `Returns:`, `Notes:`).
- **Test suite:** `tests/` — run with `pytest`. Uses `pytest-mock` to mock PRAW objects.
- **CI/CD:** GitHub Actions workflow added (`weekly-cleanup.yml`). No other pipelines.
- **Error handling:** Auth failures catch `praw.exceptions.APIException`, `prawcore.exceptions.OAuthException`, and `prawcore.exceptions.ResponseException`. Rate limits retry via `_with_retry()`. Auth failure calls `exit()` in CLI scripts; returns HTTP 401 in the web app.
- **Encoding:** All file writes use `encoding="utf-8"` explicitly.
- **Datetimes:** All timestamps use `datetime.now(timezone.utc)` and `datetime.fromtimestamp(..., tz=timezone.utc)` — never the deprecated `utcnow()` / `utcfromtimestamp()`.
- **`user_agent`:** Hardcoded as `'commentCleaner'` everywhere.

---

## Reddit API Setup

1. Go to `https://www.reddit.com/prefs/apps`
2. Create a **script**-type app (for CLI/web/CI)
3. Create an **installed app** (for Android — redirect URI: `redditcommentcleaner://auth`)
4. Note the `client_id` (under the app name) and `client_secret`

---

## Branch and Contribution Notes

- Default upstream branch: `main`
- Feature branches follow the pattern `claude/<description>-<id>`
- Bug-fix PRs open against `main`; see open PRs for pending fixes
- Vulnerability reports: pull request or email (see `SECURITY.md`)
