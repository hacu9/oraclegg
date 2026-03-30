"""Auto-updater for OracleGG.

Checks GitHub releases for new versions on startup.
Downloads and extracts the update, preserving user config.
"""

import json
import logging
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

VERSION = "0.3.0"
GITHUB_REPO = "cabello986/oraclegg"
UPDATE_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# Files to preserve during update (user data)
PRESERVE = {".env", "data"}


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent


def get_current_version() -> str:
    return VERSION


async def check_for_update() -> dict | None:
    """Check GitHub releases for a newer version.

    Returns release info dict if update available, None otherwise.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(UPDATE_URL, timeout=5, follow_redirects=True)
            if resp.status_code != 200:
                return None

            release = resp.json()
            latest_version = release.get("tag_name", "").lstrip("v")

            if not latest_version:
                return None

            if latest_version > VERSION:
                # Find the zip asset
                asset_url = None
                for asset in release.get("assets", []):
                    if asset["name"].endswith(".zip"):
                        asset_url = asset["browser_download_url"]
                        break

                return {
                    "version": latest_version,
                    "current": VERSION,
                    "url": asset_url,
                    "notes": release.get("body", ""),
                    "name": release.get("name", f"v{latest_version}"),
                }

            return None
    except Exception as e:
        logger.debug(f"Update check failed: {e}")
        return None


async def download_and_apply_update(download_url: str) -> bool:
    """Download update zip and apply it, preserving user config.

    Returns True if update was applied (app should restart).
    """
    app_dir = get_app_dir()

    try:
        # Download to temp file
        logger.info(f"Downloading update from {download_url}")
        async with httpx.AsyncClient() as client:
            resp = await client.get(download_url, timeout=120, follow_redirects=True)
            if resp.status_code != 200:
                logger.error(f"Download failed: {resp.status_code}")
                return False

        # Save to temp
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp.write(resp.content)
        tmp.close()

        # Backup preserved files
        backups = {}
        for name in PRESERVE:
            src = app_dir / name
            if src.exists():
                backup_path = Path(tempfile.mkdtemp()) / name
                if src.is_dir():
                    shutil.copytree(src, backup_path)
                else:
                    shutil.copy2(src, backup_path)
                backups[name] = backup_path

        # Extract update
        with zipfile.ZipFile(tmp.name, "r") as zf:
            # Find the root folder in the zip
            names = zf.namelist()
            root = names[0].split("/")[0] if "/" in names[0] else ""

            for member in zf.namelist():
                # Strip the root folder prefix
                if root:
                    rel = member[len(root) + 1:]
                else:
                    rel = member

                if not rel or rel in PRESERVE:
                    continue

                target = app_dir / rel
                if member.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())

        # Restore preserved files
        for name, backup_path in backups.items():
            dst = app_dir / name
            if backup_path.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(backup_path, dst)
            else:
                shutil.copy2(backup_path, dst)

        # Cleanup
        os.unlink(tmp.name)

        logger.info("Update applied successfully")
        return True

    except Exception as e:
        logger.error(f"Update failed: {e}")
        return False
