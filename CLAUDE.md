# CLAUDE.md — AI Assistant Guide for RedditCommentCleaner

## Project Overview

RedditCommentCleaner is a Python tool that allows Reddit users to bulk-delete their own comments and posts using the [PRAW](https://praw.readthedocs.io/) (Python Reddit API Wrapper) library. Before deletion, each item is edited to `"."` to prevent content-scraping tools from capturing the original text.

It ships in four forms:
- **CLI scripts** — interactive terminal tools (`redditcleaner.cli.comment_cleaner`, `redditcleaner.cli.post_cleaner`)
- **Web app** — browser-based dashboard for filtering and selectively deleting items (`redditcleaner.web.app`)
- **Android app** — native Kotlin app with OAuth PKCE flow (`android/`)
- **CI/CD** — automated weekly GitHub Actions run that deletes items with score < 1 (or score == 1 and older than 14 days)

**Current version:** 1.8.0
**Language:** Python 3 (CLI/web/CI), Kotlin (Android)
**Packaging:** standard `src/` layout, installed via `pyproject.toml` (setuptools). No `requirements.txt` files — dependencies live in `[project.dependencies]` / `[project.optional-dependencies]`.

---

## Repository Structure

```
RedditCommentCleaner/
├── pyproject.toml                 # Package metadata, dependencies, console-script entry points
├── ruff.toml                      # Lint config (E, F, W; line length unenforced)
├── src/
│   └── redditcleaner/
│       ├── __init__.py            # __version__
│       ├── utils.py                # Shared: _with_retry, credentials, reddit init
│       ├── cli/
│       │   ├── comment_cleaner.py  # CLI — comment deletion (3 modes)
│       │   └── post_cleaner.py     # CLI — post/submission deletion
│       ├── ci/
│       │   └── weekly_cleanup.py   # CI script — automated cleanup
│       └── web/
│           ├── app.py              # Flask web application (CSRF-protected)
│           └── templates/
│               ├── index.html      # Login page
│               └── dashboard.html  # Main dashboard UI
├── android/                       # Native Android app (Kotlin + OAuth PKCE)
│   ├── SETUP.md                   # Build and run instructions
│   └── app/src/main/java/com/redditcommentcleaner/
│       ├── auth/                  # LoginActivity, OAuthCallbackActivity
│       ├── api/                   # RedditApiClient, RedditApiService
│       ├── dashboard/             # DashboardActivity, DashboardViewModel
│       └── util/                  # TokenStorage, PkceHelper
├── tests/                         # pytest suite (mirrors src/ layout)
│   ├── conftest.py
│   ├── test_web_app.py
│   └── test_weekly_cleanup.py
├── .github/
│   └── workflows/
│       └── weekly-cleanup.yml     # GitHub Actions — runs redditcleaner.ci.weekly_cleanup
├── .gitignore
├── README.md
└── SECURITY.md
```

Runtime files not tracked in git (`Credentials.txt`, if used) and log files (`deleted_comments.txt`, `deleted_posts.txt`) are covered by `.gitignore`.

### Runtime-generated files (excluded by `.gitignore`)

| File | Created by | Contents |
|---|---|---|
| `deleted_comments.txt` | CLI scripts, web app, CI | JSON lines — one object per deleted comment |
| `deleted_posts.txt` | CLI scripts, web app, CI | JSON lines — one object per deleted post |
| `Credentials.txt` | User | Reddit API credentials (CLI use only) |

---

## Installing

```bash
pip install -e .            # CLI + CI only (praw)
pip install -e ".[web]"     # + Flask web app (flask, flask-wtf)
pip install -e ".[dev]"     # + test/lint tooling (pytest, pytest-mock, ruff, flask, flask-wtf)
```

This registers three console scripts (see `[project.scripts]` in `pyproject.toml`):

| Command | Runs |
|---|---|
| `reddit-clean-comments` | `redditcleaner.cli.comment_cleaner:main` |
| `reddit-clean-posts` | `redditcleaner.cli.post_cleaner:main` |
| `reddit-weekly-cleanup` | `redditcleaner.ci.weekly_cleanup:main` |

Each module is also runnable directly, e.g. `python -m redditcleaner.cli.comment_cleaner`.

---

## Shared Module — `src/redditcleaner/utils.py`

Imported by both CLI scripts and `web/app.py`. It contains:

| Symbol | Purpose |
|--------|---------|
| `_with_retry(fn, label)` | Calls `fn()`, retrying up to 3 times on `TooManyRequests` |
| `get_reddit_credentials()` | Reads `Credentials.txt` or falls back to `input()` prompts; always returns a 4-tuple `(client_id, client_secret, username, password)` |
| `confirm_and_run()` | Asks the user yes/no before running |
| `initialize_reddit(...)` | Creates and verifies a PRAW Reddit instance; catches `APIException`, `OAuthException`, and `ResponseException` |
| `get_days_old(prompt)` | Prompts for an integer age threshold |

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

### `src/redditcleaner/cli/comment_cleaner.py`

Interactive CLI offering three deletion modes:

| Option | Action |
|--------|--------|
| 1 | Delete all comments older than N days |
| 2 | Delete all comments with score ≤ 0 |
| 3 | Delete comments with score ≤ 1, no replies, older than 7 days (calls `comment.refresh()` so `comment.replies` is actually populated) |

Supports `--dry-run` flag to preview deletions without making changes.

**Flow:** load credentials → confirm → authenticate → loop (choose mode → run → report) → quit

### `src/redditcleaner/cli/post_cleaner.py`

Single-pass CLI that deletes all posts older than N days (`edit(".")` then `delete()`, once, with retry — no double-deletion).

Supports `--dry-run` flag.

**Flow:** load credentials → confirm → authenticate → prompt for age → `delete_old_posts`

### `src/redditcleaner/ci/weekly_cleanup.py`

Non-interactive script designed for CI. Reads credentials from environment variables (falling back to `Credentials.txt`) and deletes all comments **and** posts with `score < 1` or `score == 1` AND older than 14 days. Logs each deleted item to `deleted_comments.txt` / `deleted_posts.txt`.

Supports `--dry-run` flag (or `DRY_RUN=1` env var).

---

## Web App (`src/redditcleaner/web/`)

### Running

```bash
pip install -e ".[web]"
python -m redditcleaner.web.app
# Open http://localhost:5000
```

To enable debug mode: `FLASK_DEBUG=1 python -m redditcleaner.web.app`

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

- `LOG_DIR` env var controls where `deleted_comments.txt` / `deleted_posts.txt` are written; defaults to the current working directory.
- Credentials are kept in a Flask session (server-side) and never sent to the browser.
- CSRF protection is provided by **Flask-WTF** (`CSRFProtect`). The login form includes a hidden `csrf_token` field. `/api/items` is `@csrf.exempt` (GET, read-only); `/api/delete` is a state-changing POST and is CSRF-protected — the dashboard's `fetch('/api/delete')` call sends the token in the `X-CSRFToken` header (read from the `<meta name="csrf-token">` tag).
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
2. Installs the package (`pip install -e .`)
3. Runs `python -m redditcleaner.ci.weekly_cleanup` with Reddit credentials from repository secrets
4. Uploads `deleted_comments.txt` and `deleted_posts.txt` as workflow artifacts (retained 90 days)

**Criteria:** deletes all comments and posts where `score < 1` OR (`score == 1` AND older than 14 days).

---

## Running Everything

```bash
# Install (pick the extra you need)
pip install -e ".[dev]"

# Interactive comment cleaner
python -m redditcleaner.cli.comment_cleaner
# or, after install: reddit-clean-comments

# Dry-run preview (no deletions)
python -m redditcleaner.cli.comment_cleaner --dry-run

# Interactive post cleaner
python -m redditcleaner.cli.post_cleaner

# Automated cleanup (CI-style, uses env vars)
REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=... REDDIT_USERNAME=... REDDIT_PASSWORD=... \
  python -m redditcleaner.ci.weekly_cleanup

# Dry-run the CI cleanup
python -m redditcleaner.ci.weekly_cleanup --dry-run

# Web app
pip install -e ".[web]"
python -m redditcleaner.web.app   # then open http://localhost:5000

# Run tests
pip install -e ".[dev]"
pytest tests/

# Lint
ruff check .
```

---

## Development Conventions

- **Python version:** `>=3.9` (see `pyproject.toml`); standard library uses `datetime`, `time`, `os`
- **Style:** `ruff` (see `ruff.toml`) for lint (`E`, `F`, `W`; line length unenforced). Google-style docstrings (`Args:`, `Returns:`, `Notes:`).
- **Test suite:** `tests/` — run with `pytest` (config in `pyproject.toml`'s `[tool.pytest.ini_options]`). Uses `pytest-mock` / `unittest.mock` to mock PRAW objects.
- **CI/CD:** GitHub Actions workflow (`weekly-cleanup.yml`). No other pipelines.
- **Error handling:** Auth failures catch `praw.exceptions.APIException`, `prawcore.exceptions.OAuthException`, and `prawcore.exceptions.ResponseException`. Rate limits retry via `_with_retry()`. Auth failure calls `exit()` in CLI scripts; returns HTTP 401 in the web app.
- **Encoding:** File writes use `encoding="utf-8"` explicitly.
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
