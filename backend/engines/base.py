from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import subprocess
import sys
import asyncio
import json
import uuid
import textwrap


@dataclass
class TTSRequest:
    text: str
    ref_audio: Optional[str] = None
    language: str = "zh"
    speed: float = 1.0
    pitch: float = 0.0
    emotion: str = "neutral"
    extra_params: dict = field(default_factory=dict)


@dataclass
class TTSResult:
    success: bool
    output_path: Optional[str] = None
    duration: float = 0.0
    sample_rate: int = 24000
    error: Optional[str] = None


class BaseEngine(ABC):
    name: str
    display_name: str
    port: int
    engine_dir: Path
    venv_dir: Path
    model_dir: Path

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.engine_dir = base_dir / "engines" / self.name
        self.venv_dir = base_dir / "venvs" / self.name
        self.model_dir = base_dir / "models" / self.name

    @property
    def python_path(self) -> str:
        if sys.platform == "win32":
            return str(self.venv_dir / "Scripts" / "python.exe")
        return str(self.venv_dir / "bin" / "python")

    @property
    def pip_path(self) -> str:
        if sys.platform == "win32":
            return str(self.venv_dir / "Scripts" / "pip.exe")
        return str(self.venv_dir / "bin" / "pip")

    @property
    def is_installed(self) -> bool:
        return self.engine_dir.exists() and self.venv_dir.exists()

    @property
    def models_ready(self) -> bool:
        return self.model_dir.exists() and any(self.model_dir.iterdir())

    @abstractmethod
    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        ...

    @abstractmethod
    def get_gradio_script(self) -> str:
        ...

    async def run_script(self, script: str, cwd: Path | None = None, timeout: int = None) -> tuple[int, str]:
        proc = await asyncio.create_subprocess_exec(
            self.python_path, "-c", script,
            cwd=str(cwd or self.engine_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return proc.returncode, stdout.decode(errors="replace")
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "Timeout"

    async def run_inference_script(self, script_content: str, request: TTSRequest, output_dir: Path, timeout: int = 300) -> TTSResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{uuid.uuid4().hex[:12]}.wav"

        params = {
            "text": request.text,
            "ref_audio": request.ref_audio,
            "language": request.language,
            "speed": request.speed,
            "pitch": request.pitch,
            "emotion": request.emotion,
            "output": str(output_file),
            "model_dir": str(self.model_dir),
            "engine_dir": str(self.engine_dir),
            **request.extra_params,
        }

        code = textwrap.dedent(f"""\
import sys, json, os
os.chdir(r"{self.engine_dir}")
sys.path.insert(0, r"{self.engine_dir}")
params = json.loads({json.dumps(json.dumps(params))})
try:
{textwrap.indent(script_content, "    ")}
    print(json.dumps({{"success": True, "output": params["output"]}}))
except Exception as e:
    print(json.dumps({{"success": False, "error": str(e)}}))
""")

        returncode, output = await self.run_script(code, cwd=self.engine_dir, timeout=timeout)

        if returncode != 0:
            return TTSResult(success=False, error=f"Process exited with code {returncode}: {output[-500:]}")

        try:
            last_line = output.strip().split("\n")[-1]
            result = json.loads(last_line)
            if result.get("success"):
                return TTSResult(success=True, output_path=result["output"])
            return TTSResult(success=False, error=result.get("error", "Unknown error"))
        except (json.JSONDecodeError, IndexError):
            return TTSResult(success=False, error=f"Failed to parse output: {output[-500:]}")
