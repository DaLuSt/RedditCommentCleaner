"""
Backfill Google Drive with all historical GitHub Actions deletion-log artifacts.

Downloads every artifact whose name starts with ``deletion-logs-`` from the
weekly-cleanup workflow, extracts the log files, and uploads them to the
configured Google Drive folder using dated filenames so history is preserved.

Usage
-----
    python scripts/backfill_drive_upload.py

Requirements
------------
- ``gh`` CLI installed and authenticated (``gh auth status``)
- ``GOOGLE_SERVICE_ACCOUNT_KEY`` env var (JSON key path or inline JSON)
- ``GOOGLE_DRIVE_FOLDER_ID`` env var (ID of the RedditCleanupLogs Drive folder)
- Python packages: google-api-python-client, google-auth, google-auth-httplib2
  (already in requirements.txt)
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile

# Allow importing drive_upload from the repo root when run from any directory.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from drive_upload import upload_logs  # noqa: E402


def _gh_api(path: str) -> dict:
    """Call ``gh api <path>`` and return parsed JSON."""
    result = subprocess.run(
        ["gh", "api", "--paginate", path],
        capture_output=True,
        text=True,
        check=True,
    )
    # gh --paginate returns multiple JSON objects; wrap in a list if needed.
    raw = result.stdout.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Paginated output: multiple top-level JSON objects concatenated.
        combined: list = []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict) and "artifacts" in obj:
                combined.extend(obj["artifacts"])
            elif isinstance(obj, list):
                combined.extend(obj)
        return {"artifacts": combined}


def _download_artifact_zip(artifact_id: int) -> bytes:
    """Download an artifact zip and return its raw bytes via the gh CLI."""
    result = subprocess.run(
        ["gh", "api", f"repos/DaLuSt/RedditCommentCleaner/actions/artifacts/{artifact_id}/zip"],
        capture_output=True,
        check=True,
    )
    return result.stdout


def main():
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
    key = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", "")
    if not folder_id or not key:
        print("Error: GOOGLE_DRIVE_FOLDER_ID and GOOGLE_SERVICE_ACCOUNT_KEY must be set.")
        sys.exit(1)

    print("Fetching artifact list from GitHub…")
    data = _gh_api("repos/DaLuSt/RedditCommentCleaner/actions/artifacts")
    artifacts = data.get("artifacts", [])

    # Filter to deletion-log artifacts and sort oldest-first.
    log_artifacts = sorted(
        [a for a in artifacts if a["name"].startswith("deletion-logs-")],
        key=lambda a: a["created_at"],
    )

    if not log_artifacts:
        print("No deletion-log artifacts found — nothing to upload.")
        return

    print(f"Found {len(log_artifacts)} artifact(s). Uploading to Drive…\n")

    uploaded_total = 0
    for artifact in log_artifacts:
        date = artifact["created_at"][:10]  # YYYY-MM-DD
        art_id = artifact["id"]
        art_name = artifact["name"]
        print(f"  [{date}] {art_name} (id={art_id})")

        zip_bytes = _download_artifact_zip(art_id)
        if not zip_bytes:
            print("    Skipped: empty download.")
            continue

        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                zf.extractall(tmp)

            paths = []
            for fname in ("deleted_comments.txt", "deleted_posts.txt"):
                fpath = os.path.join(tmp, fname)
                if os.path.exists(fpath):
                    paths.append(fpath)

            if not paths:
                print("    Skipped: no log files in archive.")
                continue

            results = upload_logs(folder_id, *paths, date_suffix=date)
            uploaded_total += len(results)

    print(f"\nDone. Uploaded {uploaded_total} file(s) to Google Drive.")


if __name__ == "__main__":
    main()
