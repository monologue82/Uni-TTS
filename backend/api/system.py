import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent

GITHUB_REPO = "monologue82/Uni-TTS"
VERSION_FILE = BASE_DIR / "pyproject.toml"


def _get_local_version() -> str:
    text = VERSION_FILE.read_text(encoding="utf-8")
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def _parse_version(v: str) -> tuple:
    parts = re.findall(r"\d+", v)
    return tuple(int(p) for p in parts[:3])


async def _fetch_latest_release() -> dict:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers={"Accept": "application/vnd.github.v3+json"})
        resp.raise_for_status()
        return resp.json()


@router.get("/check-update")
async def check_update():
    local_ver = _get_local_version()
    try:
        release = await _fetch_latest_release()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"has_update": False, "local_version": local_ver, "message": "没有找到发布版本"}
        return {"error": f"GitHub API 错误: {e.response.status_code}"}
    except Exception as e:
        return {"error": f"检查更新失败: {str(e)}"}

    remote_tag = release.get("tag_name", "")
    remote_ver = remote_tag.lstrip("vV")
    release_name = release.get("name", remote_tag)
    release_body = release.get("body", "")
    published_at = release.get("published_at", "")

    # Find zipball or source asset
    zip_url = release.get("zipball_url", "")
    tar_url = release.get("tarball_url", "")

    # Check for uploaded assets (preferred)
    assets = release.get("assets", [])
    asset_url = ""
    asset_name = ""
    asset_size = 0
    for a in assets:
        if a["name"].endswith(".zip"):
            asset_url = a["browser_download_url"]
            asset_name = a["name"]
            asset_size = a["size"]
            break

    has_update = _parse_version(remote_ver) > _parse_version(local_ver)

    return {
        "has_update": has_update,
        "local_version": local_ver,
        "remote_version": remote_ver,
        "release_name": release_name,
        "release_body": release_body[:2000],
        "published_at": published_at,
        "download_url": asset_url or zip_url,
        "download_name": asset_name or f"Uni-TTS-{remote_ver}.zip",
        "download_size": asset_size,
        "is_asset": bool(asset_url),
    }


class UpdateRequest(BaseModel):
    download_url: str
    version: str


@router.post("/do-update")
async def do_update(req: UpdateRequest):
    """Download, extract, and restart."""
    local_ver = _get_local_version()
    if _parse_version(req.version) <= _parse_version(local_ver):
        return {"error": "本地版本已是最新，无需更新"}

    backup_dir = BASE_DIR / ".update_backup"
    try:
        # 1. Download to temp
        tmp_dir = Path(tempfile.mkdtemp(prefix="uni_tts_update_"))
        zip_path = tmp_dir / "update.zip"

        async with httpx.AsyncClient(timeout=300, follow_redirects=True) as client:
            resp = await client.get(req.download_url)
            resp.raise_for_status()
            zip_path.write_bytes(resp.content)

        # 2. Extract
        extract_dir = tmp_dir / "extracted"
        extract_dir.mkdir()
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            zf.extractall(str(extract_dir))

        # GitHub zipball has a single root folder like "monologue82-uni-tts-xxxxx"
        entries = list(extract_dir.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            source_dir = entries[0]
        else:
            source_dir = extract_dir

        # 3. Backup current files (skip large dirs)
        backup_dir.mkdir(exist_ok=True)
        skip_dirs = {"engines", "venvs", "models", "outputs", "temp", "data",
                     "node_modules", ".venv", ".git", ".modelscope_cache",
                     "__pycache__", ".update_backup", "frontend"}

        for item in BASE_DIR.iterdir():
            if item.name in skip_dirs or item.name.startswith("."):
                continue
            dest = backup_dir / item.name
            if item.is_file():
                shutil.copy2(str(item), str(dest))
            elif item.is_dir():
                if dest.exists():
                    shutil.rmtree(str(dest))
                shutil.copytree(str(item), str(dest))

        # 4. Copy new files (skip same dirs)
        for item in source_dir.iterdir():
            if item.name in skip_dirs or item.name.startswith("."):
                continue
            dest = BASE_DIR / item.name
            if item.is_file():
                shutil.copy2(str(item), str(dest))
            elif item.is_dir():
                if dest.exists():
                    shutil.rmtree(str(dest))
                shutil.copytree(str(item), str(dest))

        # 5. Copy frontend dist if present in update
        frontend_dist_src = source_dir / "frontend" / "dist"
        if frontend_dist_src.exists():
            frontend_dist_dst = BASE_DIR / "frontend" / "dist"
            if frontend_dist_dst.exists():
                shutil.rmtree(str(frontend_dist_dst))
            shutil.copytree(str(frontend_dist_src), str(frontend_dist_dst))

        # 6. Cleanup
        shutil.rmtree(str(tmp_dir), ignore_errors=True)
        if backup_dir.exists():
            shutil.rmtree(str(backup_dir), ignore_errors=True)

        # 7. Schedule restart
        _schedule_restart()

        return {
            "status": "updated",
            "old_version": local_ver,
            "new_version": req.version,
            "message": "更新完成，程序即将重启...",
        }

    except Exception as e:
        # Restore backup on failure
        if backup_dir.exists():
            try:
                for item in backup_dir.iterdir():
                    dest = BASE_DIR / item.name
                    if item.is_file():
                        shutil.copy2(str(item), str(dest))
                    elif item.is_dir():
                        if dest.exists():
                            shutil.rmtree(str(dest))
                        shutil.copytree(str(item), str(dest))
            except Exception:
                pass
        return {"error": f"更新失败: {str(e)}"}


def _schedule_restart():
    """Start a new process and exit current one."""
    python = sys.executable
    script = str(BASE_DIR / "start.py")

    if sys.platform == "win32":
        # Windows: use start command to detach
        subprocess.Popen(
            ["cmd", "/c", "timeout", "/t", "3", "/nobreak", "&",
             "start", "", python, script],
            cwd=str(BASE_DIR),
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )
    else:
        # Linux/Mac: use nohup
        subprocess.Popen(
            ["sh", "-c", f"sleep 3 && nohup {python} {script} &"],
            cwd=str(BASE_DIR),
            start_new_session=True,
        )

    # Schedule exit of current process
    import threading
    def _delayed_exit():
        import time
        time.sleep(2)
        os._exit(0)
    threading.Thread(target=_delayed_exit, daemon=True).start()
