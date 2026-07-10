import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from backend.api.tts import router as tts_router
from backend.api.models import router as models_router
from backend.api.engines import router as engines_router
from backend.api.batch import router as batch_router
from backend.api.system import router as system_router
from backend.db.database import init_db

app = FastAPI(title="Uni-TTS", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(engines_router, prefix="/api/engines", tags=["engines"])
app.include_router(models_router, prefix="/api/models", tags=["models"])
app.include_router(tts_router, prefix="/api/tts", tags=["tts"])
app.include_router(batch_router, prefix="/api/batch", tags=["batch"])
app.include_router(system_router, prefix="/api/system", tags=["system"])

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(OUTPUT_DIR)), name="outputs")

FRONTEND_DIST = Path("frontend/dist")


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))


if __name__ == "__main__":
    uvicorn.run(
        "main:app", host="0.0.0.0", port=8000, reload=True,
        reload_excludes=["engines/**", "venvs/**", "models/**", "outputs/**", "data/**", ".modelscope_cache/**"],
    )
