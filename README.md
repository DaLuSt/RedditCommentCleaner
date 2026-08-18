# RedditCommentCleaner v1.8

Bulk-delete your Reddit comments and posts. Each item is edited to `"."` before deletion to prevent content-scraping tools from capturing the original text.

Available in four forms:

| Mode | Description |
|------|-------------|
| **CLI** | Interactive terminal scripts (`commentCleaner.py`, `PostCleaner.py`) |
| **Web app** | Browser dashboard — filter, select, and delete items visually |
| **Android** | Native Kotlin app with OAuth PKCE flow (`android/`) |
| **CI/CD** | Automated weekly GitHub Actions run (score < 1, or score == 1 + older than 14 days) |

---

## Requirements

- Python 3
- `praw` (CLI / CI):  `pip install praw`
- `flask` + `praw` (web app):  `pip install -r web/requirements.txt`

---

## Reddit API setup

1. Go to <https://www.reddit.com/prefs/apps>
2. Click **Create application** → select **script**
3. Fill in a name, description, and any URL (e.g. this repo) for the redirect fields
4. Click **Create app** — note the **client ID** (under the app name) and **client secret**

![Reddit app credentials](https://user-images.githubusercontent.com/130249301/234361938-e09c0f87-e6b8-4b6b-9916-593b4bbcf35d.png)

---

## CLI scripts

Both scripts accept a `--dry-run` flag to preview which items would be deleted without making any changes:

```bash
python commentCleaner.py --dry-run
python PostCleaner.py --dry-run
```

### `commentCleaner.py` — delete comments

```bash
python commentCleaner.py
```

If `Credentials.txt` is present in the same directory it is read automatically; otherwise you are prompted. The file must contain exactly four lines:

```
<client_id>
<client_secret>
<username>
<password>
```

**Deletion modes:**

| Option | Criteria |
|--------|----------|
| 1 | All comments older than N days |
| 2 | All comments with score ≤ 0 |
| 3 | Score ≤ 1, no replies, older than 7 days |

Each deleted comment is appended to `deleted_comments.txt` (`YYYY-MM-DD HH:MM:SS | score | body`).

---

### `PostCleaner.py` — delete posts

```bash
python PostCleaner.py
```

Same credential handling as above. Prompts for an age threshold and deletes all posts older than that many days. Logs to `deleted_posts.txt`.

---

## Web app

```bash
pip install -r web/requirements.txt
python web/app.py
# Open http://localhost:5000
```

1. Log in with your Reddit API credentials (never written to disk)
2. Click **Load Items** to fetch all your comments and posts
3. Use the **filter panel** (score ≤ N, age ≥ N days) or tick items manually
4. Click **Delete Selected** — deleted rows disappear from the table in-place

Logs are written to `deleted_comments.txt` / `deleted_posts.txt` in the repo root.

---

## Android app

A native Kotlin app that mirrors the web app. Uses Reddit's **OAuth 2.0 PKCE** flow (no client secret needed).

See [`android/SETUP.md`](android/SETUP.md) for full build and run instructions.

**Quick start:**
1. Register an **installed app** at <https://www.reddit.com/prefs/apps> with redirect URI `redditcommentcleaner://auth`
2. Add your client ID to `android/local.properties` (never committed): `reddit.client_id=YOUR_ID`
3. Build: `cd android && ./gradlew assembleDebug`

**Play Store release:** see [`android/SETUP.md`](android/SETUP.md) for signing config, ProGuard, and the privacy policy requirement.

---

## Weekly automated cleanup (GitHub Actions)

The workflow at `.github/workflows/weekly-cleanup.yml` runs every **Sunday at 00:00 UTC** and can also be triggered manually from the **Actions** tab.

**Deletion criteria (either condition triggers deletion):**
- `score < 1` (any age)
- `score == 1` AND older than 14 days

### Setup

Add these secrets in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `REDDIT_CLIENT_ID` | Your script app client ID |
| `REDDIT_CLIENT_SECRET` | Your script app client secret |
| `REDDIT_USERNAME` | Your Reddit username |
| `REDDIT_PASSWORD` | Your Reddit password |

### Running locally

`weekly_cleanup.py` also reads from `Credentials.txt` as a fallback when env vars are absent, so you can run it locally the same way as the other CLI scripts:

```bash
python weekly_cleanup.py
```

---

## Output files

| File | Created by | Format |
|------|-----------|--------|
| `deleted_comments.txt` | all scripts | JSON lines — one object per deleted comment |
| `deleted_posts.txt` | all scripts | JSON lines — one object per deleted post |

Both files are excluded from git (`.gitignore`) and uploaded as GitHub Actions artifacts (retained 90 days).
