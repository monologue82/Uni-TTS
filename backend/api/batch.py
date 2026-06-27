from fastapi import APIRouter, UploadFile, File, Form
from pathlib import Path
from datetime import datetime
import uuid
import json

from backend.db.database import get_db

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent


@router.post("/create")
async def create_batch(
    engine_name: str = Form(...),
    texts: str = Form(...),
    ref_audio: UploadFile | None = File(None),
    language: str = Form("zh"),
    speed: float = Form(1.0),
    pitch: float = Form(0.0),
    emotion: str = Form("neutral"),
):
    text_list = [t.strip() for t in texts.split("\n") if t.strip()]
    if not text_list:
        return {"error": "No text provided"}

    ref_audio_path = None
    if ref_audio:
        ref_dir = BASE_DIR / "temp"
        ref_dir.mkdir(exist_ok=True)
        ref_audio_path = str(ref_dir / f"{uuid.uuid4().hex}_{ref_audio.filename}")
        content = await ref_audio.read()
        Path(ref_audio_path).write_bytes(content)

    params = json.dumps({
        "language": language,
        "speed": speed,
        "pitch": pitch,
        "emotion": emotion,
        "ref_audio": ref_audio_path,
    })

    db = await get_db()
    try:
        task_ids = []
        for text in text_list:
            cursor = await db.execute(
                "INSERT INTO batch_tasks (engine_name, text_input, ref_audio, params, status) VALUES (?, ?, ?, ?, 'pending')",
                (engine_name, text, ref_audio_path, params),
            )
            task_ids.append(cursor.lastrowid)
        await db.commit()
    finally:
        await db.close()

    return {"task_ids": task_ids, "count": len(task_ids), "status": "pending"}


@router.get("/tasks")
async def list_batch_tasks(engine_name: str | None = None):
    db = await get_db()
    try:
        if engine_name:
            rows = await db.execute_fetchall(
                "SELECT * FROM batch_tasks WHERE engine_name=? ORDER BY created_at DESC",
                (engine_name,),
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM batch_tasks ORDER BY created_at DESC LIMIT 200"
            )
        return {"tasks": [dict(r) for r in rows]}
    finally:
        await db.close()


@router.delete("/tasks/{task_id}")
async def delete_batch_task(task_id: int):
    db = await get_db()
    try:
        await db.execute("DELETE FROM batch_tasks WHERE id=?", (task_id,))
        await db.commit()
    finally:
        await db.close()
    return {"status": "deleted"}
