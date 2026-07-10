import subprocess
import asyncio
import sys
import os
import json
import threading
import time
import http.client
import shutil
import sqlite3
import re
import urllib.request
import tempfile
from collections import deque
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pathlib import Path
from pydantic import BaseModel

from backend.db.database import ENGINE_REGISTRY, get_db

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent

_gradio_processes: dict[str, subprocess.Popen] = {}
_model_servers: dict[str, dict] = {}
_install_progress: dict[str, dict] = {}
_install_logs: dict[str, deque] = {}
_model_loading_progress: dict[str, dict] = {}

INFERENCE_PORT_START = 17860
MAX_LOG_LINES = 2000


def _get_engine_info(name):
    for eng in ENGINE_REGISTRY:
        if eng["name"] == name:
            return eng
    return None


def _check_installed(name):
    vd = BASE_DIR / "venvs" / name
    # ASR only needs venv, no engine directory
    if name == "asr":
        return vd.exists() and any(vd.iterdir())
    # OmniVoice is installed via pip, no engine directory needed
    if name == "omnivoice":
        return vd.exists() and any(vd.iterdir())
    ed = BASE_DIR / "engines" / name
    return ed.exists() and vd.exists() and any(vd.iterdir())


def _check_has_models(name):
    md = BASE_DIR / "models" / name
    return md.exists() and any(md.iterdir())


def _log(name, line):
    if name not in _install_logs:
        _install_logs[name] = deque(maxlen=MAX_LOG_LINES)
    _install_logs[name].append(line)


def _check_cuda_available():
    # Try nvidia-smi first
    try:
        subprocess.check_output(["nvidia-smi"], stderr=subprocess.DEVNULL, timeout=10)
        return True
    except Exception:
        pass
    # Fallback: try torch
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


# ── List / Get ───────────────────────────────────────────────────────

@router.get("/system/device-info")
async def device_info():
    gpu_available = False
    gpu_name = None
    gpu_memory_mb = None
    cuda_version = None

    # Try nvidia-smi first (doesn't require torch)
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            text=True, timeout=10, stderr=subprocess.DEVNULL,
        ).strip()
        if output:
            parts = output.split(",")
            gpu_name = parts[0].strip()
            gpu_memory_mb = int(parts[1].strip())
            gpu_available = True
    except Exception:
        pass

    # Get CUDA version from nvidia-smi
    if not cuda_version:
        try:
            output = subprocess.check_output(
                ["nvidia-smi"], text=True, timeout=10, stderr=subprocess.DEVNULL,
            )
            import re
            m = re.search(r"CUDA Version:\s*([\d.]+)", output)
            if m:
                cuda_version = m.group(1)
        except Exception:
            pass

    # Fallback: try torch if nvidia-smi failed
    if not gpu_available:
        try:
            import torch
            if torch.cuda.is_available():
                gpu_available = True
                gpu_name = gpu_name or torch.cuda.get_device_name(0)
                gpu_memory_mb = gpu_memory_mb or (torch.cuda.get_device_properties(0).total_mem // (1024 * 1024))
                cuda_version = cuda_version or torch.version.cuda
        except ImportError:
            pass

    return {
        "gpu_available": gpu_available,
        "gpu_name": gpu_name,
        "gpu_memory_mb": gpu_memory_mb,
        "cuda_version": cuda_version,
    }


@router.get("/")
async def list_engines():
    result = []
    for eng in ENGINE_REGISTRY:
        try:
            name = eng["name"]
            installing = name in _install_progress and _install_progress[name].get("status") == "running"
            installed = _check_installed(name) and not installing
            has_models = _check_has_models(name)
            gradio_running = name in _gradio_processes and _gradio_processes[name].poll() is None
            if installed and has_models:
                state = "ready"
            elif installing:
                state = "installing"
            elif installed:
                state = "installed_no_model"
            elif has_models:
                state = "model_only"
            else:
                state = "not_installed"
            # During install, use device_type from progress; after install, from DB
            if installing:
                device_type = _install_progress[name].get("device_type", "cpu")
            elif installed:
                device_type = _get_device_type(name)
            else:
                device_type = None
            result.append({
                **eng, "installed": installed, "models_ready": has_models,
                "state": state, "installing": installing,
                "model_loaded": _is_model_loaded(name),
                "model_loading": _is_model_loading(name),
                "gradio_running": gradio_running,
                "device_type": device_type,
            })
        except Exception as e:
            result.append({**eng, "installed": False, "models_ready": False, "state": "not_installed", "installing": False, "model_loaded": False, "model_loading": False, "gradio_running": False, "device_type": None, "error": str(e)})
    return {"engines": result}


@router.get("/{engine_name}")
async def get_engine(engine_name: str):
    info = _get_engine_info(engine_name)
    if not info:
        return {"error": "Engine not found"}
    return {**info, "installed": _check_installed(engine_name), "models_ready": _check_has_models(engine_name), "model_loaded": _is_model_loaded(engine_name)}


# ── Install / Uninstall ─────────────────────────────────────────────

class InstallRequest(BaseModel):
    engine_name: str
    flash_attention: bool = False
    device_type: str = "cpu"


class DeviceRequest(BaseModel):
    device: str = "auto"


@router.post("/install")
async def install_engine(req: InstallRequest):
    name = req.engine_name
    info = _get_engine_info(name)
    if not info:
        return {"error": "Engine not found"}

    if _check_installed(name):
        return {"status": "already_installed", "engine": name}

    if name in _install_progress and _install_progress[name].get("status") == "running":
        return {"status": "installing", "engine": name}

    if req.device_type == "gpu" and not _check_cuda_available():
        return {"error": "未检测到 CUDA 环境，无法安装 GPU 版本。请安装 NVIDIA 驱动和 CUDA 后重试。"}

    _install_logs[name] = deque(maxlen=MAX_LOG_LINES)
    _install_progress[name] = {"step": "排队中...", "percent": 0, "status": "running", "error": None, "device_type": req.device_type}

    t = threading.Thread(target=_safe_install, args=(name, info, req.flash_attention, req.device_type), daemon=True)
    t.start()

    return {"status": "started", "engine": name}


@router.get("/install/{engine_name}/status")
async def install_status(engine_name: str):
    if engine_name in _install_progress:
        p = _install_progress[engine_name]
        return {"engine": engine_name, **p}
    if _check_installed(engine_name):
        return {"engine": engine_name, "status": "completed", "percent": 100, "step": "已安装", "error": None}
    return {"engine": engine_name, "status": "idle", "percent": 0, "step": "", "error": None}


@router.get("/install/{engine_name}/logs-buffer")
async def install_logs_buffer(engine_name: str):
    logs = list(_install_logs.get(engine_name, []))
    return {"engine": engine_name, "lines": logs}


@router.get("/install/{engine_name}/logs")
async def install_logs_sse(engine_name: str):
    async def event_stream():
        last_idx = 0
        while True:
            logs = list(_install_logs.get(engine_name, []))
            if len(logs) > last_idx:
                for line in logs[last_idx:]:
                    yield f"data: {json.dumps({'line': line})}\n\n"
                last_idx = len(logs)

            prog = _install_progress.get(engine_name, {})
            yield f"data: {json.dumps({'progress': prog})}\n\n"

            if prog.get("status") in ("completed", "failed", "idle", None):
                yield f"data: {json.dumps({'done': True})}\n\n"
                break

            await asyncio.sleep(0.3)

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


def _safe_install(name, info, flash_attention, device_type):
    try:
        _do_install(name, info, flash_attention, device_type)
    except Exception as e:
        try:
            _install_progress[name] = {"step": "安装异常", "percent": 0, "status": "failed", "error": str(e)}
            _log(name, f"\033[31m✗ 安装异常: {e}\033[0m")
        except Exception:
            pass


def _prefetch_findlinks_wheels(req_file: Path, pip_exe: str, log_fn):
    """Pre-download wheels from --find-links GitHub pages that block pip's User-Agent."""
    try:
        text = req_file.read_text(encoding="utf-8")
    except Exception:
        return

    find_links_urls = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'^--find-links\s+(.+)$', line)
        if m:
            find_links_urls.append(m.group(1).strip())

    if not find_links_urls:
        return

    try:
        py_ver = subprocess.check_output(
            [pip_exe, "--version"], text=True, timeout=10
        )
        py_match = re.search(r'python(\d+)\.(\d+)', py_ver)
        if not py_match:
            return
        cp_tag = f"cp{py_match.group(1)}{py_match.group(2)}"
    except Exception:
        return

    plat_tag = "win_amd64" if sys.platform == "win32" else "manylinux2014_x86_64"

    tmp_dir = Path(tempfile.mkdtemp(prefix="prefetch_wheels_"))
    downloaded = []

    for page_url in find_links_urls:
        try:
            req = urllib.request.Request(page_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                page = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            log_fn(f"⚠ 无法获取 find-links 页面: {page_url} ({e})")
            continue

        wheel_urls = re.findall(
            r'https://github\.com/[^\s"\'<>]+\.whl', page
        )

        for whl_url in wheel_urls:
            filename = whl_url.rsplit("/", 1)[-1]
            if cp_tag not in filename or plat_tag not in filename:
                continue
            dest = tmp_dir / filename
            if dest.exists():
                continue
            try:
                log_fn(f"  预下载: {filename}")
                whl_req = urllib.request.Request(whl_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(whl_req, timeout=120) as resp:
                    dest.write_bytes(resp.read())
                downloaded.append(str(dest))
                log_fn(f"  ✓ 已下载: {filename}")
            except Exception as e:
                log_fn(f"  ⚠ 预下载失败: {filename} ({e})")

    if downloaded:
        log_fn(f"正在安装 {len(downloaded)} 个预下载的 wheel...")
        cmd = [pip_exe, "install"] + downloaded
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding="utf-8", errors="replace",
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    log_fn(line)
            proc.wait()
        except Exception as e:
            log_fn(f"⚠ 预下载 wheel 安装失败: {e}")

    shutil.rmtree(tmp_dir, ignore_errors=True)


def _preinstall_sdists(req_file, pip, trusted_hosts, log_fn):
    """Pre-install source distribution packages with --no-build-isolation.

    Pip's isolated build environment does not include setuptools, so packages
    whose setup.py does ``import pkg_resources`` (e.g. openai-whisper) fail
    with ``ModuleNotFoundError: No module named 'pkg_resources'``.

    We detect sdists by downloading each package (no deps) into a temp dir,
    and if the result is a .tar.gz or .zip, install it with --no-build-isolation
    so the venv's own setuptools is used for the build.
    """
    import re, subprocess, shutil, tempfile
    text = req_file.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("-") or line.startswith("#"):
            continue
        # Skip platform-conditional lines for non-Windows platforms
        if "sys_platform" in line and ("'linux'" in line or "'darwin'" in line):
            continue
        m = re.match(r'^([a-zA-Z0-9_.-]+)', line)
        if not m:
            continue
        pkg = m.group(1)
        tmp = Path(tempfile.mkdtemp())
        try:
            log_fn(f"  检查 {pkg}...")
            rc = subprocess.run(
                [pip, "download", "--no-deps", "--dest", str(tmp), pkg] + trusted_hosts,
                capture_output=True, text=True, timeout=120,
            )
            for f in tmp.iterdir():
                name = f.name.lower()
                if name.endswith((".tar.gz", ".zip", ".tar.bz2")):
                    log_fn(f"  ├ sdist: {f.name} → 使用 --no-build-isolation")
                    subprocess.run(
                        [pip, "install", "--no-build-isolation", str(f)] + trusted_hosts,
                        capture_output=True, timeout=120,
                    )
        except Exception as e:
            log_fn(f"  ⚠ 跳过 {pkg}: {e}")
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)


def _do_install(name: str, info: dict, flash_attention: bool, device_type: str):
    engine_dir = BASE_DIR / "engines" / name
    venv_dir = BASE_DIR / "venvs" / name

    def set_progress(step, pct):
        _install_progress[name] = {"step": step, "percent": pct, "status": "running", "error": None, "device_type": device_type}
        _log(name, f"\033[36m[{pct}%]\033[0m {step}")

    def set_done():
        _install_progress[name] = {"step": "安装完成", "percent": 100, "status": "completed", "error": None, "device_type": device_type}
        _log(name, "\033[32m✓ 安装完成!\033[0m")
        _db_mark_installed(name, device_type)

    def set_fail(err):
        _install_progress[name] = {"step": "安装失败", "percent": 0, "status": "failed", "error": str(err), "device_type": device_type}
        _log(name, f"\033[31m✗ 失败: {err}\033[0m")

    def run_stream(cmd, cwd=None):
        try:
            env = {**os.environ, "GIT_SSL_NO_VERIFY": "1", "PIP_TRUSTED_HOST": "github.com k2-fsa.github.io objects.githubusercontent.com"}
            proc = subprocess.Popen(
                cmd, cwd=str(cwd) if cwd else None, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, encoding="utf-8", errors="replace",
            )
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    _log(name, line)
            proc.wait()
            return proc.returncode
        except Exception as e:
            _log(name, f"\033[31m[子进程异常] {e}\033[0m")
            return -1

    try:
        # Special handling for ASR tool (no repo to clone)
        if name == "asr":
            set_progress("正在创建虚拟环境...", 30)
            if not venv_dir.exists():
                _log(name, f"$ {sys.executable} -m venv venvs/{name}")
                rc = run_stream([sys.executable, "-m", "venv", str(venv_dir)])
                if rc != 0:
                    set_fail("创建虚拟环境失败")
                    return
            set_progress("虚拟环境创建完成", 40)

            python = str(venv_dir / "Scripts" / "python.exe") if sys.platform == "win32" else str(venv_dir / "bin" / "python")
            
            # Verify python exists
            if not Path(python).exists():
                set_fail(f"虚拟环境 Python 不存在: {python}")
                return
            
            trusted_hosts = ["--trusted-host", "github.com", "--trusted-host", "pypi.org", "--trusted-host", "files.pythonhosted.org"]

            set_progress("正在安装 funasr...", 50)
            _log(name, f"$ {python} -m pip install funasr")
            rc = run_stream([python, "-m", "pip", "install", "funasr"] + trusted_hosts)
            if rc != 0:
                set_fail("funasr 安装失败")
                return
            set_progress("funasr 安装完成", 80)

            set_progress("正在安装模型依赖...", 85)
            _log(name, f"$ {python} -m pip install modelscope")
            run_stream([python, "-m", "pip", "install", "modelscope"] + trusted_hosts)

            set_progress("正在验证安装...", 95)
            if not Path(python).exists():
                set_fail("虚拟环境 Python 不存在")
                return
            set_done()
            return

        # Step 1: Clone — skip for pip-only engines like omnivoice
        if name == "omnivoice":
            set_progress("跳过克隆（pip 安装模式）", 25)
            engine_dir.mkdir(parents=True, exist_ok=True)
        else:
            need_clone = False
            if not engine_dir.exists():
                need_clone = True
            elif (engine_dir / ".git").exists():
                # Check if there are actual files besides .git
                has_files = any(f.name != ".git" for f in engine_dir.iterdir())
                if not has_files:
                    _log(name, "检测到不完整的克隆目录（只有 .git），正在清理...")
                    shutil.rmtree(engine_dir, ignore_errors=True)
                    need_clone = True

            if need_clone:
                set_progress("正在克隆仓库...", 5)
                _log(name, f"$ git clone {info['github_repo']}")
                # Use GIT_TERMINAL_PROMPT=0 to prevent hanging on auth prompts
                env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_SSL_NO_VERIFY": "1"}
                try:
                    proc = subprocess.Popen(
                        ["git", "clone", info["github_repo"], str(engine_dir)],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, bufsize=1, encoding="utf-8", errors="replace",
                        env=env,
                    )
                    for line in proc.stdout:
                        line = line.rstrip()
                        if line:
                            _log(name, line)
                    proc.wait(timeout=600)  # 10 minute timeout for clone
                    rc = proc.returncode
                except subprocess.TimeoutExpired:
                    proc.kill()
                    _log(name, "克隆超时（10分钟）")
                    if engine_dir.exists():
                        shutil.rmtree(engine_dir, ignore_errors=True)
                    set_fail("克隆超时，请检查网络连接")
                    return
                except Exception as e:
                    _log(name, f"克隆异常: {e}")
                    rc = -1

                if rc != 0:
                    _log(name, f"git clone 返回错误码: {rc}")
                    if engine_dir.exists():
                        shutil.rmtree(engine_dir, ignore_errors=True)
                    set_fail("克隆失败，请检查网络连接")
                    return

                # Verify clone succeeded - must have files besides .git
                if not engine_dir.exists():
                    set_fail("克隆失败：目录未创建")
                    return
                files = [f for f in engine_dir.iterdir() if f.name != ".git"]
                if not files:
                    _log(name, "克隆完成但目录为空，正在清理...")
                    shutil.rmtree(engine_dir, ignore_errors=True)
                    set_fail("克隆失败：仓库目录为空，请检查网络或仓库地址")
                    return
                _log(name, f"✓ 克隆成功，共 {len(files)} 个文件/目录")

        set_progress("仓库克隆完成", 25)

        # Step 2: Create venv
        if not venv_dir.exists():
            set_progress("正在创建虚拟环境...", 30)
            _log(name, f"$ {sys.executable} -m venv venvs/{name}")
            rc = run_stream([sys.executable, "-m", "venv", str(venv_dir)])
            if rc != 0:
                set_fail("创建虚拟环境失败")
                return
        set_progress("虚拟环境创建完成", 40)

        pip = str(venv_dir / "Scripts" / "pip.exe") if sys.platform == "win32" else str(venv_dir / "bin" / "pip")
        python = str(venv_dir / "Scripts" / "python.exe") if sys.platform == "win32" else str(venv_dir / "bin" / "python")

        trusted_hosts = [
            "--trusted-host", "github.com",
            "--trusted-host", "k2-fsa.github.io",
            "--trusted-host", "objects.githubusercontent.com",
        ]

        # Step 2.5: Upgrade build tools to avoid "No module named 'pkg_resources'" errors
        set_progress("正在升级构建工具...", 41)
        _log(name, "$ pip install --upgrade setuptools wheel")
        run_stream(
            [pip, "install", "--upgrade", "setuptools", "wheel"] + trusted_hosts,
            cwd=engine_dir,
        )

        # Step 3: Install PyTorch based on device_type
        if device_type == "gpu":
            set_progress("正在安装 PyTorch (GPU/CUDA 12.8 版本)...", 42)
            _log(name, "$ pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128")
            rc = run_stream(
                [pip, "install", "torch", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu128"] + trusted_hosts,
                cwd=engine_dir,
            )
            if rc != 0:
                set_progress("cu128 安装失败，尝试 cu126...", 43)
                _log(name, "$ pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu126")
                rc = run_stream(
                    [pip, "install", "torch", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu126"] + trusted_hosts,
                    cwd=engine_dir,
                )
            if rc != 0:
                set_fail("PyTorch GPU 版本安装失败，请检查网络连接")
                return
            _log(name, "✓ PyTorch GPU 版本安装完成")
        else:
            set_progress("正在安装 PyTorch (CPU 版本)...", 42)
            _log(name, "$ pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu")
            rc = run_stream(
                [pip, "install", "torch", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cpu"] + trusted_hosts,
                cwd=engine_dir,
            )
            if rc != 0:
                set_fail("PyTorch CPU 版本安装失败")
                return
            _log(name, "✓ PyTorch CPU 版本安装完成")

        # Step 4: Install deps
        req_file = engine_dir / "requirements.txt"
        if req_file.exists():
            set_progress("正在预下载 GitHub 资源...", 52)
            _prefetch_findlinks_wheels(req_file, pip, lambda line: _log(name, line))
            set_progress("正在安装依赖 (可能需要几分钟)...", 55)
            # Pre-install source-dist-only packages with --no-build-isolation,
            # so pip's isolated build env doesn't lack setuptools/pkg_resources.
            _preinstall_sdists(req_file, pip, trusted_hosts, lambda line: _log(name, line))
            pip_cmd = [pip, "install", "-r", str(req_file)] + trusted_hosts
            _log(name, f"$ {' '.join(pip_cmd)}")
            rc = run_stream(pip_cmd, cwd=engine_dir)
            if rc != 0:
                set_fail("安装依赖失败，请查看终端日志")
                return
        set_progress("依赖安装完成", 75)

        # Step 5: Flash Attention
        if flash_attention and info.get("flash_attention"):
            set_progress("正在安装 Flash Attention 2...", 80)
            _log(name, "$ pip install flash-attn --no-build-isolation")
            rc = run_stream([pip, "install", "flash-attn", "--no-build-isolation"] + trusted_hosts, cwd=engine_dir)
            if rc != 0:
                _log(name, "⚠ Flash Attention 安装失败，将使用默认 attention")
            else:
                _log(name, "✓ Flash Attention 2 安装成功")

        # Step 6: Extra pip per engine
        extra = info.get("extra_pip")
        if extra:
            set_progress("正在安装额外组件...", 88)
            for pkg in (extra if isinstance(extra, list) else [extra]):
                _log(name, f"$ pip install {pkg}")
                run_stream([pip, "install", pkg] + trusted_hosts, cwd=engine_dir)

        # Step 7: Editable install if pyproject.toml exists
        if (engine_dir / "pyproject.toml").exists():
            set_progress("正在以开发模式安装项目...", 92)
            _log(name, "$ pip install -e .")
            run_stream([pip, "install", "-e", "."] + trusted_hosts, cwd=engine_dir)

        set_progress("正在验证安装...", 95)
        if not Path(python).exists():
            set_fail("虚拟环境 Python 不存在")
            return

        set_done()

    except subprocess.TimeoutExpired:
        set_fail("安装超时")
    except Exception as e:
        set_fail(str(e))


@router.post("/uninstall")
async def uninstall_engine(req: InstallRequest):
    name = req.engine_name
    info = _get_engine_info(name)
    if not info:
        return {"error": "Engine not found"}

    for name_key, proc in list(_model_servers.items()):
        if name_key == name and proc.get("proc") and proc["proc"].poll() is None:
            proc["proc"].terminate()
    _model_servers.pop(name, None)

    p = _gradio_processes.pop(name, None)
    if p and p.poll() is None:
        p.terminate()

    for d in (BASE_DIR / "engines" / name, BASE_DIR / "venvs" / name):
        if d.exists():
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass

    _install_progress.pop(name, None)
    _install_logs.pop(name, None)

    db_path = BASE_DIR / "data" / "uni-tts.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("UPDATE engines SET installed=0, venv_created=0 WHERE name=?", (name,))
            conn.execute("DELETE FROM install_tasks WHERE engine_name=?", (name,))
            conn.commit(); conn.close()
        except Exception:
            pass

    return {"status": "uninstalled", "engine": name}


def _db_mark_installed(name, device_type="cpu"):
    db_path = BASE_DIR / "data" / "uni-tts.db"
    if not db_path.exists():
        return
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO engines (name, installed, venv_created, device_type) VALUES (?, 1, 1, ?) ON CONFLICT(name) DO UPDATE SET installed=1, venv_created=1, device_type=?",
                     (name, device_type, device_type))
        conn.commit(); conn.close()
    except Exception:
        pass


def _get_device_type(name):
    db_path = BASE_DIR / "data" / "uni-tts.db"
    if not db_path.exists():
        return "cpu"
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT device_type FROM engines WHERE name=?", (name,)).fetchone()
        conn.close()
        if row and row["device_type"]:
            return row["device_type"]
        return "cpu"
    except Exception:
        return "cpu"


# ── Model load / unload ─────────────────────────────────────────────

def _is_model_loaded(name):
    info = _model_servers.get(name)
    if not info or info["proc"].poll() is not None:
        _model_servers.pop(name, None)
        return False
    try:
        conn = http.client.HTTPConnection("127.0.0.1", info["port"], timeout=2)
        conn.request("GET", "/status")
        data = json.loads(conn.getresponse().read())
        conn.close()
        return data.get("ready", False)
    except Exception:
        return False


def _is_model_loading(name):
    """True when the inference server process is alive but not ready yet."""
    info = _model_servers.get(name)
    if not info:
        return False
    if info["proc"].poll() is not None:
        return False
    return not info.get("ready", False)


@router.post("/{engine_name}/load-model")
async def load_model(engine_name: str, req: DeviceRequest):
    info = _get_engine_info(engine_name)
    if not info:
        return {"error": "Engine not found"}
    if _is_model_loaded(engine_name):
        return {"status": "already_loaded", "engine": engine_name, "port": _model_servers[engine_name]["port"]}
    if not _check_installed(engine_name):
        return {"error": "引擎未安装，请先安装引擎"}
    if not _check_has_models(engine_name):
        return {"error": "模型未下载，请先下载模型"}

    # If a process is already running (still loading), don't kill it — let the
    # caller resume tracking via /load-progress. This prevents port conflicts
    # and avoids wasting work when the user closes the progress window and
    # clicks the card again.
    old = _model_servers.get(engine_name)
    if old and old["proc"].poll() is None:
        return {"status": "loading", "engine": engine_name, "port": old["port"]}
    # Stale entry (crashed/exited) — clean up before starting fresh
    if old:
        _model_servers.pop(engine_name, None)

    engine_dir = BASE_DIR / "engines" / engine_name
    venv_dir = BASE_DIR / "venvs" / engine_name
    model_dir = BASE_DIR / "models" / engine_name

    python = str(venv_dir / "Scripts" / "python.exe") if sys.platform == "win32" else str(venv_dir / "bin" / "python")
    server_script = str(BASE_DIR / "backend" / "engines" / "inference_server.py")
    port = INFERENCE_PORT_START + [e["name"] for e in ENGINE_REGISTRY].index(engine_name)

    proc = subprocess.Popen(
        [python, server_script, engine_name, str(model_dir), str(engine_dir), str(port), req.device],
        cwd=str(engine_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    _model_servers[engine_name] = {"proc": proc, "port": port, "ready": False}
    _model_loading_progress[engine_name] = {"percent": 0, "message": "正在启动推理服务器...", "status": "loading"}

    loop = asyncio.get_event_loop()
    ready = await loop.run_in_executor(None, _wait_for_ready, proc, port, 180, engine_name)
    if ready:
        _model_servers[engine_name]["ready"] = True
        return {"status": "loaded", "engine": engine_name, "port": port}
    else:
        _model_servers.pop(engine_name, None)
        proc.terminate()
        return {"error": "模型加载失败"}


def _wait_for_ready(proc, port, timeout=180, engine_name=""):
    start = time.time()
    while time.time() - start < timeout:
        if proc.poll() is not None:
            return False
        try:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.1); continue
            msg = json.loads(line.decode().strip())
            if msg.get("status") == "loading" and engine_name:
                _model_loading_progress[engine_name] = {
                    "percent": msg.get("percent", 0),
                    "message": msg.get("message", ""),
                    "status": "loading",
                }
            elif msg.get("status") in ("ready", "listening"):
                if engine_name:
                    _model_loading_progress[engine_name] = {"percent": 100, "message": "模型加载完成", "status": "ready"}
                return True
            elif msg.get("status") in ("error", "failed"):
                if engine_name:
                    _model_loading_progress[engine_name] = {"percent": 0, "message": msg.get("error", ""), "status": "error"}
                return False
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        except Exception:
            time.sleep(0.1)
    return False


@router.post("/{engine_name}/unload-model")
async def unload_model(engine_name: str):
    info = _model_servers.get(engine_name)
    if not info:
        return {"status": "not_loaded", "engine": engine_name}
    try:
        conn = http.client.HTTPConnection("127.0.0.1", info["port"], timeout=3)
        conn.request("POST", "/shutdown"); conn.getresponse(); conn.close()
    except Exception:
        pass
    proc = info["proc"]
    if proc.poll() is None:
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=3)
    _model_servers.pop(engine_name, None)
    return {"status": "unloaded", "engine": engine_name}


@router.get("/{engine_name}/model-status")
async def model_status(engine_name: str):
    return {"engine": engine_name, "loaded": _is_model_loaded(engine_name), "port": _model_servers.get(engine_name, {}).get("port")}


@router.get("/{engine_name}/load-progress")
async def load_progress(engine_name: str):
    p = _model_loading_progress.get(engine_name)
    if p:
        return p
    if _is_model_loaded(engine_name):
        return {"percent": 100, "message": "模型已加载", "status": "ready"}
    return {"percent": 0, "message": "", "status": "idle"}


# ── Gradio ───────────────────────────────────────────────────────────

@router.post("/{engine_name}/start-gradio")
async def start_gradio(engine_name: str, req: DeviceRequest):
    info = _get_engine_info(engine_name)
    if not info:
        return {"error": "Engine not found"}
    if not _check_installed(engine_name):
        return {"error": "引擎未安装"}
    if engine_name in _gradio_processes and _gradio_processes[engine_name].poll() is None:
        return {"status": "already_running", "url": f"http://localhost:{info['port']}"}

    engine_dir = BASE_DIR / "engines" / engine_name
    venv_dir = BASE_DIR / "venvs" / engine_name
    python = str(venv_dir / "Scripts" / "python.exe") if sys.platform == "win32" else str(venv_dir / "bin" / "python")
    if not (engine_dir / info["entry_script"]).exists():
        return {"error": f"入口脚本不存在: {info['entry_script']}"}

    env = os.environ.copy()
    env["UNI_TTS_DEVICE"] = req.device

    proc = subprocess.Popen(
        [python, info["entry_script"], "--port", str(info["port"]), "--server", "0.0.0.0"],
        cwd=str(engine_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
    )
    _gradio_processes[engine_name] = proc
    await asyncio.sleep(3)
    if proc.poll() is not None:
        return {"error": f"启动失败: {(proc.stdout.read().decode() if proc.stdout else '')[:500]}"}
    return {"status": "started", "url": f"http://localhost:{info['port']}"}


@router.get("/{engine_name}/gradio-status")
async def gradio_status(engine_name: str):
    info = _get_engine_info(engine_name)
    if not info:
        return {"error": "Engine not found"}
    running = engine_name in _gradio_processes and _gradio_processes[engine_name].poll() is None
    return {"running": running, "url": f"http://localhost:{info['port']}" if running else None}


@router.post("/{engine_name}/stop-gradio")
async def stop_gradio(engine_name: str):
    p = _gradio_processes.pop(engine_name, None)
    if p and p.poll() is None:
        p.terminate(); p.wait(timeout=5)
        return {"status": "stopped"}
    return {"status": "not_running"}
