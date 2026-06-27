import json
import uuid
import http.client
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import datetime

from backend.engines import get_engine
from backend.engines.base import TTSRequest

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"

_model_servers: dict[str, dict] = {}


def _get_model_server(engine_name: str) -> dict | None:
    from backend.api.engines import _model_servers as servers, _is_model_loaded
    info = servers.get(engine_name)
    if info and info["proc"].poll() is not None:
        servers.pop(engine_name, None)
        return None
    if info and _is_model_loaded(engine_name):
        return info
    return None


@router.post("/synthesize")
async def synthesize(
    engine_name: str = Form(...),
    text: str = Form(...),
    ref_audio: UploadFile | None = File(None),
    ref_text: str = Form(""),
    language: str = Form("zh"),
    speed: float = Form(1.0),
    pitch: float = Form(0.0),
    emotion: str = Form("neutral"),
    description: str = Form(""),
    control_instruction: str = Form(""),
    prompt_text: str = Form(""),
    cfg_value: float = Form(2.0),
    dit_steps: int = Form(10),
    normalize: bool = Form(False),
    denoise: bool = Form(False),
):
    ref_audio_path = None
    if ref_audio:
        ref_dir = BASE_DIR / "temp"
        ref_dir.mkdir(exist_ok=True)
        ref_audio_path = str(ref_dir / f"{uuid.uuid4().hex}_{ref_audio.filename}")
        content = await ref_audio.read()
        Path(ref_audio_path).write_bytes(content)

    task_output_dir = OUTPUT_DIR / engine_name / datetime.now().strftime("%Y%m%d")
    task_output_dir.mkdir(parents=True, exist_ok=True)
    output_file = task_output_dir / f"{uuid.uuid4().hex[:12]}.wav"

    server_info = _get_model_server(engine_name)
    if server_info:
        try:
            params = {
                "text": text,
                "ref_audio": ref_audio_path,
                "ref_text": ref_text,
                "language": language,
                "speed": speed,
                "pitch": pitch,
                "emotion": emotion,
                "description": description,
                "control_instruction": control_instruction,
                "prompt_text": prompt_text,
                "cfg_value": cfg_value,
                "dit_steps": dit_steps,
                "normalize": normalize,
                "denoise": denoise,
                "output": str(output_file),
            }
            conn = http.client.HTTPConnection("127.0.0.1", server_info["port"], timeout=None)
            conn.request("POST", "/synthesize", json.dumps(params), {"Content-Type": "application/json"})
            resp = conn.getresponse()
            result = json.loads(resp.read())
            conn.close()

            if result.get("success"):
                if Path(result["output"]).exists():
                    return FileResponse(result["output"], media_type="audio/wav")
                return {"error": "合成完成但输出文件不存在"}
            return {"error": result.get("error", "Synthesis failed")}
        except http.client.HTTPException as e:
            return {"error": f"推理服务器响应错误: {str(e)}"}
        except ConnectionRefusedError:
            return {"error": "推理服务器连接被拒绝，请重新加载模型"}
        except Exception as e:
            return {"error": f"推理服务器错误: {str(e)}"}

    engine = get_engine(engine_name, BASE_DIR)
    if not engine.is_installed:
        return {"error": f"Engine {engine.display_name} is not installed"}
    if not engine.models_ready:
        return {"error": f"Model for {engine.display_name} not downloaded. Please download first."}

    extra = {}
    if ref_text:
        extra["ref_text"] = ref_text
    if description:
        extra["description"] = description
    if control_instruction:
        extra["control_instruction"] = control_instruction
    if prompt_text:
        extra["prompt_text"] = prompt_text

    request = TTSRequest(
        text=text, ref_audio=ref_audio_path, language=language,
        speed=speed, pitch=pitch, emotion=emotion, extra_params=extra,
    )
    result = await engine.synthesize(request, task_output_dir)

    if result.success:
        return FileResponse(result.output_path, media_type="audio/wav")
    return {"error": result.error}


@router.post("/asr")
async def asr_recognize(
    audio: UploadFile = File(...),
):
    audio_dir = BASE_DIR / "temp"
    audio_dir.mkdir(exist_ok=True)
    audio_path = str(audio_dir / f"asr_{uuid.uuid4().hex}_{audio.filename}")
    content = await audio.read()
    Path(audio_path).write_bytes(content)

    try:
        # Check if ASR venv exists
        asr_venv = BASE_DIR / "venvs" / "asr"
        if not asr_venv.exists():
            return {"error": "ASR 引擎未安装，请先在资源管理页面安装 ASR 引擎", "text": ""}

        python = str(asr_venv / "Scripts" / "python.exe") if sys.platform == "win32" else str(asr_venv / "bin" / "python")
        if not Path(python).exists():
            return {"error": "ASR 引擎未安装，请先在资源管理页面安装 ASR 引擎", "text": ""}

        # Check shared ASR location first, then legacy VoxCPM location
        shared_asr = BASE_DIR / "models" / "asr" / "SenseVoiceSmall"
        legacy_asr = BASE_DIR / "models" / "voxcpm" / "SenseVoiceSmall"
        
        def has_model_files(path):
            if not path.exists():
                return False
            return any(path.rglob("*.pt")) or any(path.rglob("*.bin")) or any(path.rglob("*.safetensors"))
        
        if has_model_files(shared_asr):
            asr_model_path = str(shared_asr)
        elif has_model_files(legacy_asr):
            asr_model_path = str(legacy_asr)
        else:
            return {"error": "ASR 模型未下载，请先下载模型", "text": ""}

        # Run ASR in subprocess using ASR venv
        script_content = f'''import sys
import json
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
sys.path.insert(0, r"{asr_venv / 'Lib' / 'site-packages'}")
try:
    from funasr import AutoModel
    asr_model = AutoModel(
        model=r"{asr_model_path}",
        disable_update=True,
        log_level="DEBUG",
        device="cuda:0",
    )
    res = asr_model.generate(input=r"{audio_path}", language="auto", use_itn=True)
    text = res[0]["text"].split("|>")[-1]
    print(json.dumps({{"text": text}}))
except Exception as e:
    print(json.dumps({{"error": str(e), "text": ""}}))
'''
        import subprocess
        import tempfile
        # Write script to temp file to avoid command line escaping issues
        script_path = str(audio_dir / f"asr_script_{uuid.uuid4().hex}.py")
        Path(script_path).write_text(script_content, encoding="utf-8")
        try:
            result = subprocess.run(
                [python, script_path],
                capture_output=True, text=True, timeout=120
            )
        finally:
            try:
                Path(script_path).unlink(missing_ok=True)
            except:
                pass
        
        if result.returncode != 0:
            return {"error": f"ASR 执行失败: {result.stderr[:500]}", "text": ""}
        
        try:
            output = result.stdout.strip()
            # Get last line of output (ignore warnings)
            for line in reversed(output.split("\n")):
                line = line.strip()
                if line.startswith("{"):
                    return json.loads(line)
            return {"error": "ASR 输出格式错误", "text": ""}
        except json.JSONDecodeError:
            return {"error": f"ASR 输出解析失败: {output[:200]}", "text": ""}
    except Exception as e:
        return {"error": f"ASR failed: {str(e)}", "text": ""}
    finally:
        try:
            Path(audio_path).unlink(missing_ok=True)
        except Exception:
            pass


@router.get("/asr-status")
async def asr_status():
    # Check if ASR venv is installed
    asr_venv = BASE_DIR / "venvs" / "asr"
    engine_installed = asr_venv.exists() and any(asr_venv.iterdir())
    
    shared_asr = BASE_DIR / "models" / "asr" / "SenseVoiceSmall"
    legacy_asr = BASE_DIR / "models" / "voxcpm" / "SenseVoiceSmall"
    downloaded = False
    if shared_asr.exists() and any(shared_asr.rglob("*.pt")):
        downloaded = True
    elif legacy_asr.exists() and any(legacy_asr.rglob("*.pt")):
        downloaded = True
    # Also check for .bin files
    if not downloaded and shared_asr.exists() and any(shared_asr.rglob("*.bin")):
        downloaded = True
    elif not downloaded and legacy_asr.exists() and any(legacy_asr.rglob("*.bin")):
        downloaded = True
    # Check for model.safetensors
    if not downloaded and shared_asr.exists() and any(shared_asr.rglob("*.safetensors")):
        downloaded = True
    elif not downloaded and legacy_asr.exists() and any(legacy_asr.rglob("*.safetensors")):
        downloaded = True
    return {"has_asr": True, "downloaded": downloaded, "engine_installed": engine_installed, "model_id": "iic/SenseVoiceSmall"}


@router.get("/status/{engine_name}")
async def engine_status(engine_name: str):
    server_info = _get_model_server(engine_name)
    engine = get_engine(engine_name, BASE_DIR)
    return {
        "engine": engine_name,
        "installed": engine.is_installed,
        "models_ready": engine.models_ready,
        "model_loaded": server_info is not None,
        "gradio_port": engine.port,
        "gradio_script": engine.get_gradio_script(),
    }


@router.get("/asr-status/{engine_name}")
async def asr_status(engine_name: str):
    from backend.db.database import ENGINE_REGISTRY
    asr_models = []
    for eng in ENGINE_REGISTRY:
        if eng["name"] == engine_name:
            asr_models = eng.get("asr_models", [])
            break
    if not asr_models:
        return {"has_asr": False, "downloaded": False}
    model_dir = BASE_DIR / "models" / engine_name
    for asr in asr_models:
        asr_dir = model_dir / asr["local_subdir"]
        if asr_dir.exists() and any(f.is_file() for f in asr_dir.rglob("*")):
            return {"has_asr": True, "downloaded": True, "model_id": asr["model_scope_id"]}
    return {"has_asr": True, "downloaded": False, "model_id": asr_models[0]["model_scope_id"]}
