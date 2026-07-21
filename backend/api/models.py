import asyncio
import threading
from fastapi import APIRouter, BackgroundTasks
from pathlib import Path
from pydantic import BaseModel

from backend.db.database import get_db, ENGINE_REGISTRY

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent

_download_progress: dict[int, dict] = {}

# Thread-local storage for per-download progress isolation.
# Each download thread sets its own _agg and _task_id before calling
# snapshot_download, so concurrent downloads don't cross-talk.
_dl_local = threading.local()
_tqdm_patched = False
_tqdm_patch_lock = threading.Lock()


def _patch_tqdm_once():
    """Globally patch tqdm once so progress updates are captured per-thread."""
    global _tqdm_patched
    with _tqdm_patch_lock:
        if _tqdm_patched:
            return
        import tqdm as _tqdm

        class ProgressTqdm(_tqdm.tqdm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                agg = getattr(_dl_local, "agg", None)
                if agg is not None and self.total:
                    agg["total"] += self.total

            def update(self, n=1):
                super().update(n)
                agg = getattr(_dl_local, "agg", None)
                task_id = getattr(_dl_local, "task_id", None)
                if agg is not None and task_id is not None:
                    agg["done"] += n
                    if agg["total"] > 0:
                        pct = min(99.0, agg["done"] / agg["total"] * 100)
                        _download_progress[task_id]["progress"] = round(pct, 1)
                        _download_progress[task_id]["detail"] = f"{_fmt_size(agg['done'])} / {_fmt_size(agg['total'])}"

        _tqdm.tqdm = ProgressTqdm
        try:
            import tqdm.std
            tqdm.std.tqdm = ProgressTqdm
        except Exception:
            pass
        _tqdm_patched = True


class DownloadRequest(BaseModel):
    engine_name: str
    model_id: str | None = None
    local_dir: str | None = None
    is_asr: bool = False
    source: str | None = None  # "modelscope" or "huggingface"


@router.get("/")
async def list_models():
    result = []

    # Shared ASR model
    asr_dir = BASE_DIR / "models" / "asr" / "SenseVoiceSmall"
    legacy_asr_dir = BASE_DIR / "models" / "voxcpm" / "SenseVoiceSmall"
    asr_downloaded = False
    asr_size = 0
    if asr_dir.exists():
        asr_files = list(asr_dir.rglob("*"))
        asr_downloaded = any(f.is_file() for f in asr_files)
        asr_size = sum(f.stat().st_size for f in asr_files if f.is_file())
    elif legacy_asr_dir.exists():
        asr_files = list(legacy_asr_dir.rglob("*"))
        asr_downloaded = any(f.is_file() for f in asr_files)
        asr_size = sum(f.stat().st_size for f in asr_files if f.is_file())
    result.append({
        "engine_name": "asr",
        "display_name": "SenseVoiceSmall (ASR 语音识别)",
        "model_scope_id": "iic/SenseVoiceSmall",
        "huggingface_id": "FunAudioLLM/SenseVoiceSmall",
        "model_dir": str(asr_dir),
        "downloaded": asr_downloaded,
        "total_size_mb": round(asr_size / 1024 / 1024, 1),
        "is_asr": True,
        "asr_description": "共享语音识别模型，用于所有引擎的参考音频文本自动填充",
        "parent_engine": "全局共享",
    })

    for eng in ENGINE_REGISTRY:
        name = eng["name"]
        # Skip the shared ASR tool entry — it's already appended above
        if name == "asr" or eng.get("is_tool"):
            continue
        model_dir = BASE_DIR / "models" / name
        has_models = False
        total_size = 0
        if model_dir.exists():
            files = list(model_dir.rglob("*"))
            has_models = any(f.is_file() for f in files)
            total_size = sum(f.stat().st_size for f in files if f.is_file())
        result.append({
            "engine_name": name,
            "display_name": eng["display_name"],
            "model_scope_id": eng["model_scope_id"],
            "huggingface_id": eng.get("huggingface_id", ""),
            "model_dir": str(model_dir),
            "downloaded": has_models,
            "total_size_mb": round(total_size / 1024 / 1024, 1),
            "is_asr": False,
        })
    return {"models": result}


@router.post("/download")
async def download_model(req: DownloadRequest, background_tasks: BackgroundTasks):
    engine_name = req.engine_name
    model_id = req.model_id
    source = req.source or "modelscope"

    if not model_id:
        for eng in ENGINE_REGISTRY:
            if eng["name"] == engine_name:
                if source == "huggingface":
                    model_id = eng.get("huggingface_id", eng["model_scope_id"])
                else:
                    model_id = eng["model_scope_id"]
                break

    if not model_id:
        return {"error": "Model ID not specified"}

    # Handle shared ASR model
    if req.is_asr or engine_name == "asr":
        local_dir = req.local_dir or str(BASE_DIR / "models" / "asr" / "SenseVoiceSmall")
        if not model_id:
            model_id = "iic/SenseVoiceSmall" if source == "modelscope" else "FunAudioLLM/SenseVoiceSmall"
    else:
        local_dir = req.local_dir or str(BASE_DIR / "models" / engine_name)

    # Insert with retry to handle concurrent SQLite writes
    task_id = None
    for attempt in range(3):
        try:
            db = await get_db()
            try:
                cursor = await db.execute(
                    "INSERT INTO download_tasks (engine_name, model_id, local_dir, status, progress) VALUES (?, ?, ?, 'running', 0)",
                    (engine_name, model_id, local_dir),
                )
                task_id = cursor.lastrowid
                await db.commit()
            finally:
                await db.close()
            break
        except Exception:
            if attempt < 2:
                await asyncio.sleep(0.5)
            else:
                raise

    _download_progress[task_id] = {"progress": 0, "status": "running", "error": None, "detail": ""}

    background_tasks.add_task(_run_download_thread, task_id, model_id, local_dir, engine_name, source)

    return {"task_id": task_id, "model_id": model_id, "local_dir": local_dir, "status": "running"}


def _run_download_thread(task_id, model_id, local_dir, engine_name, source="modelscope"):
    t = threading.Thread(target=_do_download_sync, args=(task_id, model_id, local_dir, engine_name, source), daemon=True)
    t.start()


def _needs_extraction(engine_name):
    """Check if the engine's downloaded model contains archives to extract."""
    for eng in ENGINE_REGISTRY:
        if eng["name"] == engine_name:
            return eng.get("extract_archives", False)
    return False


def _extract_archives(local_dir, task_id):
    """Extract all .zip / .tar.gz archives in the download directory in place."""
    import zipfile
    import tarfile

    dir_path = Path(local_dir)
    if not dir_path.exists():
        return

    archives = []
    for f in dir_path.iterdir():
        if not f.is_file():
            continue
        name = f.name.lower()
        if name.endswith(".zip") or name.endswith(".tar.gz") or (name.endswith(".tgz")):
            archives.append(f)

    if not archives:
        return

    total = len(archives)
    for i, archive in enumerate(archives):
        _download_progress[task_id]["detail"] = f"正在解压 {archive.name} ({i+1}/{total})..."
        _download_progress[task_id]["progress"] = min(99, 90 + round((i / total) * 9))
        try:
            if archive.name.lower().endswith(".zip"):
                with zipfile.ZipFile(str(archive), "r") as zf:
                    zf.extractall(str(dir_path))
            else:
                with tarfile.open(str(archive), "r:gz") as tf:
                    tf.extractall(str(dir_path))
        except Exception:
            pass


def _do_download_sync(task_id, model_id, local_dir, engine_name, source="modelscope"):
    import os
    os.environ.setdefault("MODELSCOPE_CACHE", str(BASE_DIR / ".modelscope_cache"))

    # Set up thread-local progress state so concurrent downloads are isolated
    _dl_local.agg = {"total": 0, "done": 0}
    _dl_local.task_id = task_id

    try:
        _download_progress[task_id] = {"progress": 2, "status": "running", "error": None, "detail": "正在初始化..."}
        _update_db_sync(task_id, "running", 2)

        # Patch tqdm once globally; per-thread state is read from _dl_local
        _patch_tqdm_once()

        if source == "huggingface":
            _download_progress[task_id]["detail"] = "正在连接 HuggingFace..."
            _update_db_sync(task_id, "running", 3)

            from huggingface_hub import snapshot_download as hf_snapshot_download

            _download_progress[task_id]["progress"] = 5
            _download_progress[task_id]["detail"] = f"开始从 HuggingFace 下载 {model_id}..."
            _update_db_sync(task_id, "running", 5)

            hf_snapshot_download(model_id, local_dir=local_dir)
        else:
            _download_progress[task_id]["detail"] = "正在连接 ModelScope..."
            _update_db_sync(task_id, "running", 3)

            from modelscope import snapshot_download

            _download_progress[task_id]["progress"] = 5
            _download_progress[task_id]["detail"] = f"开始从 ModelScope 下载 {model_id}..."
            _update_db_sync(task_id, "running", 5)

            snapshot_download(model_id, local_dir=local_dir)

        # Extract archives if the engine requires it (e.g. GPT-SoVITS)
        if _needs_extraction(engine_name):
            _download_progress[task_id]["detail"] = "正在解压模型文件..."
            _download_progress[task_id]["progress"] = 90
            _update_db_sync(task_id, "running", 90)
            _extract_archives(local_dir, task_id)

        _download_progress[task_id] = {"progress": 100, "status": "completed", "error": None, "detail": "下载完成"}
        _update_db_sync(task_id, "completed", 100)
        _mark_engine_ready(engine_name)

    except Exception as e:
        err_msg = str(e)
        _download_progress[task_id] = {"progress": 0, "status": "failed", "error": err_msg, "detail": ""}
        _update_db_sync(task_id, "failed", 0, err_msg)
    finally:
        _dl_local.agg = None
        _dl_local.task_id = None


def _fmt_size(b):
    if b < 1024:
        return f"{b}B"
    if b < 1024 * 1024:
        return f"{b / 1024:.0f}KB"
    if b < 1024 * 1024 * 1024:
        return f"{b / 1024 / 1024:.1f}MB"
    return f"{b / 1024 / 1024 / 1024:.2f}GB"


def _update_db_sync(task_id, status, progress, error=None):
    import sqlite3
    db_path = BASE_DIR / "data" / "uni-tts.db"
    if not db_path.exists():
        return
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        if error:
            conn.execute("UPDATE download_tasks SET status=?, progress=?, error=? WHERE id=?", (status, progress, error, task_id))
        else:
            conn.execute("UPDATE download_tasks SET status=?, progress=? WHERE id=?", (status, progress, task_id))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _mark_engine_ready(engine_name):
    import sqlite3
    db_path = BASE_DIR / "data" / "uni-tts.db"
    if not db_path.exists():
        return
    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.execute("UPDATE engines SET models_downloaded=1 WHERE name=?", (engine_name,))
        conn.commit()
        conn.close()
    except Exception:
        pass


@router.get("/tasks")
async def list_download_tasks():
    db = await get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM download_tasks ORDER BY created_at DESC")
        tasks = []
        for r in rows:
            d = dict(r)
            tid = d["id"]
            if tid in _download_progress:
                d["progress"] = _download_progress[tid]["progress"]
                d["status"] = _download_progress[tid]["status"]
                d["error"] = _download_progress[tid]["error"]
                d["detail"] = _download_progress[tid].get("detail", "")
            tasks.append(d)
        return {"tasks": tasks}
    finally:
        await db.close()


@router.get("/tasks/{task_id}")
async def get_download_task(task_id: int):
    if task_id in _download_progress:
        p = _download_progress[task_id]
        return {"id": task_id, "progress": p["progress"], "status": p["status"], "error": p["error"], "detail": p.get("detail", "")}

    db = await get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM download_tasks WHERE id=?", (task_id,))
        if rows:
            return dict(rows[0])
        return {"error": "Task not found"}
    finally:
        await db.close()


@router.delete("/{engine_name}")
async def delete_model(engine_name: str, is_asr: bool = False, model_id: str = ""):
    import shutil

    # Handle shared ASR model
    if engine_name == "asr" or (is_asr and engine_name == "asr"):
        asr_dir = BASE_DIR / "models" / "asr" / "SenseVoiceSmall"
        legacy_asr_dir = BASE_DIR / "models" / "voxcpm" / "SenseVoiceSmall"
        deleted = False
        if asr_dir.exists():
            shutil.rmtree(asr_dir)
            deleted = True
        if legacy_asr_dir.exists():
            shutil.rmtree(legacy_asr_dir)
            deleted = True
        if deleted:
            return {"status": "deleted", "engine": "asr", "asr_model": "iic/SenseVoiceSmall"}
        return {"error": "ASR 模型目录不存在"}

    model_dir = BASE_DIR / "models" / engine_name
    if not model_dir.exists():
        return {"error": "Model directory not found"}

    if is_asr and model_id:
        for eng in ENGINE_REGISTRY:
            if eng["name"] == engine_name:
                for asr in eng.get("asr_models", []):
                    if asr["model_scope_id"] == model_id:
                        target = model_dir / asr["local_subdir"]
                        if target.exists():
                            shutil.rmtree(target)
                        return {"status": "deleted", "engine": engine_name, "asr_model": model_id}
                break
        return {"error": "ASR model not found"}

    shutil.rmtree(model_dir)
    db = await get_db()
    try:
        await db.execute("UPDATE engines SET models_downloaded=0 WHERE name=?", (engine_name,))
        await db.commit()
    finally:
        await db.close()
    return {"status": "deleted", "engine": engine_name}
