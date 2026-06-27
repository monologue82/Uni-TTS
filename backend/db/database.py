import aiosqlite
from pathlib import Path

DB_PATH = Path("data/uni-tts.db")


async def get_db() -> aiosqlite.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=5000")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA busy_timeout=5000")
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS engines (
                name TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                installed INTEGER DEFAULT 0,
                venv_created INTEGER DEFAULT 0,
                models_downloaded INTEGER DEFAULT 0,
                port INTEGER,
                github_repo TEXT,
                model_scope_id TEXT,
                python_version TEXT DEFAULT '3.10',
                device_type TEXT DEFAULT 'cpu'
            );

            CREATE TABLE IF NOT EXISTS download_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                engine_name TEXT NOT NULL,
                model_id TEXT NOT NULL,
                local_dir TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress REAL DEFAULT 0,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (engine_name) REFERENCES engines(name)
            );

            CREATE TABLE IF NOT EXISTS batch_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                engine_name TEXT NOT NULL,
                text_input TEXT NOT NULL,
                ref_audio TEXT,
                params TEXT,
                status TEXT DEFAULT 'pending',
                output_path TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (engine_name) REFERENCES engines(name)
            );

            CREATE TABLE IF NOT EXISTS install_tasks (
                engine_name TEXT PRIMARY KEY,
                status TEXT DEFAULT 'idle',
                progress REAL DEFAULT 0,
                step TEXT DEFAULT '',
                error TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Migration: add device_type column if missing
        try:
            await db.execute("ALTER TABLE engines ADD COLUMN device_type TEXT DEFAULT 'cpu'")
            await db.commit()
        except Exception:
            pass

        await db.commit()
    finally:
        await db.close()


ENGINE_REGISTRY = [
    {
        "name": "gptsovits",
        "display_name": "GPT-SoVITS",
        "port": 7861,
        "github_repo": "https://github.com/RVC-Boss/GPT-SoVITS.git",
        "model_scope_id": "XXXXRT/GPT-SoVITS-Pretrained",
        "python_version": "3.10",
        "description": "1分钟语音数据即可训练高质量TTS模型",
        "min_vram_gb": 4,
        "entry_script": "webui.py",
        "flash_attention": False,
        "extract_archives": True,
    },
    {
        "name": "cosyvoice",
        "display_name": "CosyVoice",
        "port": 7862,
        "github_repo": "https://github.com/FunAudioLLM/CosyVoice.git",
        "model_scope_id": "iic/CosyVoice2-0.5B",
        "python_version": "3.10",
        "description": "阿里多语言大语音生成模型",
        "min_vram_gb": 4,
        "entry_script": "webui.py",
        "flash_attention": True,
    },
    {
        "name": "qwen3tts",
        "display_name": "Qwen3-TTS",
        "port": 7863,
        "github_repo": "https://github.com/QwenLM/Qwen3-TTS.git",
        "model_scope_id": "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "python_version": "3.10",
        "description": "通义千问3秒语音克隆，支持10种语言",
        "min_vram_gb": 6,
        "entry_script": "app.py",
        "flash_attention": True,
    },
    {
        "name": "indextts",
        "display_name": "IndexTTS-2",
        "port": 7864,
        "github_repo": "https://github.com/index-tts/index-tts.git",
        "model_scope_id": "IndexTeam/IndexTTS-2",
        "python_version": "3.10",
        "description": "B站情感丰富、时长可控的零样本TTS",
        "min_vram_gb": 4,
        "entry_script": "webui.py",
        "flash_attention": True,
    },
    {
        "name": "luxtts",
        "display_name": "LuxTTS",
        "port": 7865,
        "github_repo": "https://github.com/ysharma3501/LuxTTS.git",
        "model_scope_id": "hf/YatharthS-LuxTTS",
        "python_version": "3.10",
        "description": "轻量高速，1GB显存即可150倍实时",
        "min_vram_gb": 1,
        "entry_script": "app.py",
        "flash_attention": False,
    },
    {
        "name": "voxcpm",
        "display_name": "VoxCPM 2",
        "port": 7866,
        "github_repo": "https://github.com/OpenBMB/VoxCPM.git",
        "model_scope_id": "OpenBMB/VoxCPM2",
        "python_version": "3.10",
        "description": "清华无分词器TTS，30种语言48kHz",
        "min_vram_gb": 8,
        "entry_script": "app.py",
        "flash_attention": True,
        "asr_models": [
            {
                "model_scope_id": "iic/SenseVoiceSmall",
                "display_name": "SenseVoiceSmall (ASR)",
                "description": "语音识别模型，用于参考音频文本自动填充",
                "local_subdir": "SenseVoiceSmall",
            },
        ],
    },
    {
        "name": "mosstts",
        "display_name": "MOSS-TTS",
        "port": 7867,
        "github_repo": "https://github.com/OpenMOSS/MOSS-TTS.git",
        "model_scope_id": "openmoss/MOSS-TTS",
        "python_version": "3.10",
        "description": "复旦开源语音全家桶，高保真长文本",
        "min_vram_gb": 4,
        "entry_script": "demo/demo_moss_tts.py",
        "flash_attention": True,
    },
    {
        "name": "fishspeech",
        "display_name": "Fish Audio S2 Pro",
        "port": 7868,
        "github_repo": "https://github.com/fishaudio/fish-speech.git",
        "model_scope_id": "fishaudio/s2-pro",
        "python_version": "3.10",
        "description": "15000+情感标签，80+语言，100ms首帧",
        "min_vram_gb": 8,
        "entry_script": "fish_speech/webui.py",
        "flash_attention": True,
    },
    {
        "name": "asr",
        "display_name": "SenseVoice ASR",
        "port": 0,
        "github_repo": "",
        "model_scope_id": "iic/SenseVoiceSmall",
        "python_version": "3.10",
        "description": "语音识别模型，用于参考音频文本自动填充",
        "min_vram_gb": 0,
        "entry_script": "",
        "flash_attention": False,
        "is_tool": True,
    },
]
