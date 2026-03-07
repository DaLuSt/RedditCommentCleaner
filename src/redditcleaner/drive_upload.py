"""
Google Drive upload helper for RedditCommentCleaner.

Uploads deletion log files (deleted_comments.txt, deleted_posts.txt) to a
Google Drive folder using a service account.  If an existing file with the
same name is already present in the folder it is updated in-place rather
than creating a duplicate.

The module is opt-in: if the required environment variables are not set,
`maybe_upload_logs()` silently returns an empty list so all existing
functionality continues to work without any Drive configuration.

Setup
-----
1. Go to https://console.cloud.google.com and create (or select) a project.
2. Enable the **Google Drive API** for that project.
3. Create a **Service Account** (IAM & Admin → Service Accounts → Create).
4. Generate a JSON key for the service account and download it.
5. Share your target Google Drive folder with the service account's email
   address (give it **Editor** access).
6. Copy the folder ID from the Drive URL:
       https://drive.google.com/drive/folders/<FOLDER_ID>

Environment variables
---------------------
GOOGLE_SERVICE_ACCOUNT_KEY
    Either the path to the downloaded JSON key file, or the raw JSON content
    of the key (useful for CI where storing a file is inconvenient).

GOOGLE_DRIVE_FOLDER_ID
    The ID of the Drive folder to upload files into.
"""

import json
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

_SCOPES = ["https://www.googleapis.com/auth/drive"]


def _get_service():
    """Build and return an authenticated Drive API service."""
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", "")
    if not raw:
        raise EnvironmentError("GOOGLE_SERVICE_ACCOUNT_KEY is not set")

    # Accept either a file path or inline JSON
    if os.path.isfile(raw):
        with open(raw, encoding="utf-8") as fh:
            key_data = json.load(fh)
    else:
        key_data = json.loads(raw)

    creds = service_account.Credentials.from_service_account_info(key_data, scopes=_SCOPES)
    return build("drive", "v3", credentials=creds)


def _check_folder(service, folder_id: str) -> None:
    """Verify the Drive folder is accessible; raise a clear error if not."""
    from googleapiclient.errors import HttpError  # lazy — avoids top-level import failure in envs without the package

    try:
        service.files().get(fileId=folder_id, fields="id").execute()
    except HttpError as exc:
        if exc.resp.status == 404:
            raise RuntimeError(
                f"Google Drive folder '{folder_id}' was not found or is not "
                "accessible by the service account. "
                "Share the folder with the service account email address "
                "(Editor access) and try again."
            ) from exc
        raise


def upload_logs(folder_id: str, *file_paths: str, date_suffix: str = None) -> list:
    """
    Upload one or more files to a Google Drive folder.

    When *date_suffix* is provided (e.g. ``"2026-02-27"``) the base filename is
    extended before upload so that each week's file is stored separately::

        deleted_comments.txt  →  deleted_comments_2026-02-27.txt

    Dated uploads are always created as new files (no in-place update).

    Without *date_suffix* the original filename is used and an existing file
    with that name is updated in-place rather than creating a duplicate.

    Args:
        folder_id: Google Drive folder ID to upload into.
        *file_paths: Absolute or relative paths of local files to upload.
        date_suffix: Optional ``YYYY-MM-DD`` string appended to each filename.

    Returns:
        list of dicts with keys 'name' and 'url' for each uploaded file.
    """
    service = _get_service()
    _check_folder(service, folder_id)
    results = []

    for path in file_paths:
        if not os.path.exists(path):
            continue

        base = os.path.basename(path)
        if date_suffix:
            stem, ext = os.path.splitext(base)
            name = f"{stem}_{date_suffix}{ext}"
        else:
            name = base

        media = MediaFileUpload(path, mimetype="text/plain", resumable=False)

        if date_suffix:
            # Dated files are unique — always create a new file.
            file_meta = service.files().create(
                body={"name": name, "parents": [folder_id]},
                media_body=media,
                fields="id",
            ).execute()
            file_id = file_meta["id"]
        else:
            # Undated files: update in-place to avoid duplicates.
            existing = service.files().list(
                q=f"name='{name}' and '{folder_id}' in parents and trashed=false",
                fields="files(id)",
            ).execute().get("files", [])

            if existing:
                file_id = existing[0]["id"]
                service.files().update(fileId=file_id, media_body=media).execute()
            else:
                file_meta = service.files().create(
                    body={"name": name, "parents": [folder_id]},
                    media_body=media,
                    fields="id",
                ).execute()
                file_id = file_meta["id"]

        url = f"https://drive.google.com/file/d/{file_id}/view"
        results.append({"name": name, "url": url})
        print(f"  Uploaded {name} → {url}")

    return results


def maybe_upload_logs(*file_paths: str, date_suffix: str = None) -> list:
    """
    Upload logs to Drive when credentials are configured; silently skip otherwise.

    Args:
        *file_paths: Paths of log files to upload.
        date_suffix: Optional ``YYYY-MM-DD`` string passed to :func:`upload_logs`.
            When provided, files are stored with a date-stamped name so each
            run's logs are preserved as a separate file in Drive.

    Returns:
        List of dicts with 'name' and 'url', or empty list if Drive is not
        configured or the upload fails.
    """
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID", "")
    if not folder_id or not os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY", ""):
        print("Google Drive upload skipped: GOOGLE_SERVICE_ACCOUNT_KEY or GOOGLE_DRIVE_FOLDER_ID not set.")
        return []
    try:
        return upload_logs(folder_id, *file_paths, date_suffix=date_suffix)
    except Exception as exc:
        print(f"Google Drive upload skipped: {exc}")
        return []
