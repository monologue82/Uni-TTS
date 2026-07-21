import json
import sys
import os
import uuid
import importlib
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

engine_name = sys.argv[1]
model_dir = sys.argv[2]
engine_dir = sys.argv[3]
port = int(sys.argv[4])
device = sys.argv[5] if len(sys.argv) > 5 else "auto"

os.chdir(engine_dir)
sys.path.insert(0, engine_dir)

# GPT-SoVITS and similar engines have their core code in a subdirectory
gpt_sovits_dir = os.path.join(engine_dir, "GPT_SoVITS")
if os.path.isdir(gpt_sovits_dir):
    sys.path.insert(0, gpt_sovits_dir)

# Add venv site-packages to path for installed packages
python_dir = Path(sys.executable).parent.parent
site_packages = python_dir / "Lib" / "site-packages"
if not site_packages.exists():
    # Linux/Mac venv structure
    site_packages = python_dir.parent / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
if site_packages.exists():
    sys.path.insert(0, str(site_packages))

MODEL = None
SAMPLE_RATE = 24000
READY = False
ERROR = None


def resolve_device(requested):
    import torch
    if requested == "cuda":
        if torch.cuda.is_available():
            # Test if CUDA actually works
            try:
                torch.cuda.init()
                torch.zeros(1, device="cuda")
                return "cuda"
            except RuntimeError:
                return "cpu"
        return "cpu"
    elif requested == "cpu":
        return "cpu"
    else:
        if torch.cuda.is_available():
            try:
                torch.cuda.init()
                torch.zeros(1, device="cuda")
                return "cuda"
            except RuntimeError:
                return "cpu"
        return "cpu"


def emit_progress(pct, msg):
    print(json.dumps({"status": "loading", "percent": pct, "message": msg}), flush=True)


def load_model():
    global MODEL, SAMPLE_RATE, READY, ERROR
    try:
        if engine_name == "cosyvoice":
            emit_progress(10, "正在导入 CosyVoice 模块...")
            sys.path.insert(0, os.path.join(engine_dir, "third_party", "Matcha-TTS"))
            from cosyvoice.cli.cosyvoice import CosyVoice2
            emit_progress(30, "正在定位模型目录...")
            mdir = _find_model_dir(model_dir, "cosyvoice")
            emit_progress(50, "正在加载模型权重...")
            try:
                MODEL = CosyVoice2(mdir, load_jit=False, load_trt=False, fp16=False)
            except RuntimeError as e:
                if "CUDA" in str(e) or "no kernel image" in str(e):
                    emit_progress(60, "GPU 加载失败，尝试 CPU 模式...")
                    MODEL = CosyVoice2(mdir, load_jit=False, load_trt=False, fp16=False)
                else:
                    raise
            SAMPLE_RATE = MODEL.sample_rate
            emit_progress(95, "CosyVoice 模型加载完成")

        elif engine_name == "qwen3tts":
            emit_progress(10, "正在导入 PyTorch 和 Qwen3-TTS...")
            import torch
            from qwen_tts import Qwen3TTSModel
            emit_progress(20, "正在检测设备...")
            _device = resolve_device(device)
            emit_progress(30, "正在定位模型目录...")
            mdir = _find_model_dir(model_dir, "qwen")
            emit_progress(50, f"正在加载模型权重到 {_device}...")
            dtype = torch.bfloat16 if _device == "cuda" else torch.float32
            try:
                MODEL = Qwen3TTSModel.from_pretrained(mdir, device_map=_device, dtype=dtype)
            except RuntimeError as e:
                if "CUDA" in str(e) or "no kernel image" in str(e):
                    emit_progress(60, "GPU 加载失败，尝试 CPU 模式...")
                    _device = "cpu"
                    MODEL = Qwen3TTSModel.from_pretrained(mdir, device_map="cpu", dtype=torch.float32)
                else:
                    raise
            SAMPLE_RATE = 24000
            emit_progress(95, "Qwen3-TTS 模型加载完成")

        elif engine_name == "indextts":
            emit_progress(10, "正在导入 IndexTTS 模块...")
            from indextts.infer import IndexTTS
            emit_progress(30, "正在定位模型目录...")
            mdir = _find_model_dir(model_dir, "index")
            cfg = os.path.join(mdir, "config.yaml")
            emit_progress(50, "正在加载模型权重...")
            try:
                MODEL = IndexTTS(cfg, mdir)
            except RuntimeError as e:
                if "CUDA" in str(e) or "no kernel image" in str(e):
                    emit_progress(60, "GPU 加载失败，尝试 CPU 模式...")
                    os.environ["INDEX_TTS_DEVICE"] = "cpu"
                    MODEL = IndexTTS(cfg, mdir)
                else:
                    raise
            SAMPLE_RATE = 24000
            emit_progress(95, "IndexTTS 模型加载完成")

        elif engine_name == "voxcpm":
            emit_progress(10, "正在导入 VoxCPM 模块...")
            from voxcpm import VoxCPM
            from voxcpm.model.utils import resolve_runtime_device
            emit_progress(20, "正在检测设备...")
            _device = resolve_runtime_device(device, "cuda")
            _optimize = _device.startswith("cuda")
            emit_progress(30, "正在定位模型目录...")
            mdir = _find_model_dir(model_dir, "voxcpm")
            emit_progress(50, f"正在加载模型权重到 {_device}...")
            try:
                MODEL = VoxCPM.from_pretrained(mdir, optimize=_optimize, device=_device)
            except RuntimeError as e:
                if "CUDA" in str(e) or "no kernel image" in str(e):
                    emit_progress(60, "GPU 加载失败，尝试 CPU 模式...")
                    _device = "cpu"
                    _optimize = False
                    MODEL = VoxCPM.from_pretrained(mdir, optimize=False, device="cpu")
                else:
                    raise
            SAMPLE_RATE = MODEL.tts_model.sample_rate
            emit_progress(95, "VoxCPM 模型加载完成")

        elif engine_name == "mosstts":
            emit_progress(10, "正在导入 Transformers 模块...")
            import torch
            from transformers import AutoModel, AutoProcessor
            emit_progress(20, "正在检测设备...")
            _device = resolve_device(device)
            dtype = torch.bfloat16 if _device == "cuda" else torch.float32
            emit_progress(30, "正在定位模型目录...")
            mdir = _find_model_dir(model_dir, "moss")
            emit_progress(40, "正在加载 Processor...")
            processor = AutoProcessor.from_pretrained(mdir, trust_remote_code=True)
            emit_progress(50, f"正在加载模型权重到 {_device}...")
            try:
                model = AutoModel.from_pretrained(mdir, trust_remote_code=True, torch_dtype=dtype, attn_implementation="eager").to(_device)
            except RuntimeError as e:
                if "CUDA" in str(e) or "no kernel image" in str(e):
                    emit_progress(60, "GPU 加载失败，尝试 CPU 模式...")
                    _device = "cpu"
                    dtype = torch.float32
                    model = AutoModel.from_pretrained(mdir, trust_remote_code=True, torch_dtype=dtype, attn_implementation="eager").to("cpu")
                else:
                    raise
            model.eval()
            MODEL = {"model": model, "processor": processor, "device": _device}
            SAMPLE_RATE = 24000
            emit_progress(95, "MOSS-TTS 模型加载完成")

        elif engine_name == "gptsovits":
            emit_progress(10, "正在导入 GPT-SoVITS 模块...")
            from GPT_SoVITS.inference_webui import change_gpt_weights, change_sovits_weights, get_tts_wav
            gpt_dir = os.path.join(model_dir, "GPT-SoVITS")
            if os.path.isdir(gpt_dir):
                gpt_files = [f for f in os.listdir(gpt_dir) if f.endswith(".pth")]
                sovits_files = [f for f in os.listdir(gpt_dir) if f.endswith(".pth")]
                if gpt_files:
                    emit_progress(40, f"正在加载 GPT 权重: {gpt_files[0]}")
                    change_gpt_weights(os.path.join(gpt_dir, gpt_files[0]))
                if sovits_files:
                    emit_progress(70, f"正在加载 SoVITS 权重: {sovits_files[0]}")
                    change_sovits_weights(os.path.join(gpt_dir, sovits_files[0]))
            MODEL = get_tts_wav
            SAMPLE_RATE = 32000
            emit_progress(95, "GPT-SoVITS 模型加载完成")

        elif engine_name == "fishspeech":
            emit_progress(10, "正在初始化 Fish Speech...")
            MODEL = {"checkpoint": _find_model_dir(model_dir, "s2"), "engine_dir": engine_dir}
            SAMPLE_RATE = 44100
            emit_progress(95, "Fish Speech 初始化完成")

        elif engine_name == "luxtts":
            emit_progress(10, "正在导入 LuxTTS 模块...")
            from zipvoice.luxvoice import LuxTTS
            emit_progress(50, "正在加载模型权重...")
            MODEL = LuxTTS(model_dir)
            SAMPLE_RATE = 48000
            emit_progress(95, "LuxTTS 模型加载完成")

        elif engine_name == "omnivoice":
            emit_progress(10, "正在导入 OmniVoice 模块...")
            import torch
            from omnivoice import OmniVoice
            emit_progress(20, "正在检测设备...")
            _device = resolve_device(device)
            emit_progress(30, "正在定位模型目录...")
            mdir = _find_model_dir(model_dir, "omnivoice")
            emit_progress(50, f"正在加载模型权重到 {_device}...")
            dtype = torch.float16 if _device == "cuda" else torch.float32
            try:
                MODEL = OmniVoice.from_pretrained(mdir, device_map=_device, dtype=dtype)
            except RuntimeError as e:
                if "CUDA" in str(e) or "no kernel image" in str(e):
                    emit_progress(60, "GPU 加载失败，尝试 CPU 模式...")
                    _device = "cpu"
                    MODEL = OmniVoice.from_pretrained(mdir, device_map="cpu", dtype=torch.float32)
                else:
                    raise
            SAMPLE_RATE = 24000
            emit_progress(95, "OmniVoice 模型加载完成")

        elif engine_name == "confucius4tts":
            emit_progress(10, "正在导入 Confucius4-TTS 模块...")
            import torch
            from confuciustts.cli.inference import ConfuciusTTS
            emit_progress(20, "正在检测设备...")
            _device = resolve_device(device)
            emit_progress(30, "正在定位模型目录...")
            mdir = _find_model_dir(model_dir, "confucius")
            emit_progress(50, f"正在加载模型权重到 {_device}...")
            config_path = os.path.join(engine_dir, "config", "inference_config.yaml")
            try:
                MODEL = ConfuciusTTS(
                    config_path=config_path,
                    device=_device,
                )
            except RuntimeError as e:
                if "CUDA" in str(e) or "no kernel image" in str(e):
                    emit_progress(60, "GPU 加载失败，尝试 CPU 模式...")
                    MODEL = ConfuciusTTS(
                        config_path=config_path,
                        device="cpu",
                    )
                else:
                    raise
            SAMPLE_RATE = MODEL.sample_rate
            emit_progress(95, "Confucius4-TTS 模型加载完成")

        elif engine_name == "longcataudiodit":
            emit_progress(10, "正在导入 LongCat-AudioDiT 模块...")
            import torch
            import audiodit
            from audiodit import AudioDiTModel
            from transformers import AutoTokenizer
            emit_progress(20, "正在检测设备...")
            _device = resolve_device(device)
            emit_progress(30, "正在定位模型目录...")
            mdir = _find_model_dir(model_dir, "longcat")
            emit_progress(50, f"正在加载模型权重到 {_device}...")
            try:
                MODEL = AudioDiTModel.from_pretrained(mdir).to(_device)
                MODEL.vae.to_half() if _device == "cuda" else None
                MODEL.eval()
                tokenizer = AutoTokenizer.from_pretrained(MODEL.config.text_encoder_model)
                MODEL = {"model": MODEL, "tokenizer": tokenizer, "device": _device}
            except RuntimeError as e:
                if "CUDA" in str(e) or "no kernel image" in str(e):
                    emit_progress(60, "GPU 加载失败，尝试 CPU 模式...")
                    MODEL = AudioDiTModel.from_pretrained(mdir).to("cpu")
                    MODEL.eval()
                    tokenizer = AutoTokenizer.from_pretrained(MODEL.config.text_encoder_model)
                    MODEL = {"model": MODEL, "tokenizer": tokenizer, "device": "cpu"}
                else:
                    raise
            SAMPLE_RATE = 24000
            emit_progress(95, "LongCat-AudioDiT 模型加载完成")

        elif engine_name == "viitorvoice":
            emit_progress(10, "正在导入 ViiTor Voice 模块...")
            import torch
            from viitor_voice.cli import VIITOR_VOCALIZE
            emit_progress(20, "正在检测设备...")
            _device = resolve_device(device)
            emit_progress(30, "正在定位模型目录...")
            mdir = _find_model_dir(model_dir, "viitor")
            emit_progress(50, f"正在加载模型权重到 {_device}...")
            try:
                MODEL = VIITOR_VOCALIZE(
                    llm_model_path=os.path.join(mdir, "llm"),
                    soundstorm_model_path=os.path.join(mdir, "soundstorm"),
                    dualcodec_model_path=os.path.join(mdir, "dualcodec"),
                    w2v_path=os.path.join(mdir, "w2v"),
                    device=_device,
                )
            except RuntimeError as e:
                if "CUDA" in str(e) or "no kernel image" in str(e):
                    emit_progress(60, "GPU 加载失败，尝试 CPU 模式...")
                    MODEL = VIITOR_VOCALIZE(
                        llm_model_path=os.path.join(mdir, "llm"),
                        soundstorm_model_path=os.path.join(mdir, "soundstorm"),
                        dualcodec_model_path=os.path.join(mdir, "dualcodec"),
                        w2v_path=os.path.join(mdir, "w2v"),
                        device="cpu",
                    )
                else:
                    raise
            SAMPLE_RATE = 24000
            emit_progress(95, "ViiTor Voice 模型加载完成")

        READY = True
        emit_progress(100, "模型加载完成")
        print(json.dumps({"status": "ready"}), flush=True)

    except Exception as e:
        ERROR = str(e)
        READY = False
        print(json.dumps({"status": "error", "error": str(e)}), flush=True)


def _find_model_dir(base, keyword):
    if os.path.isdir(base):
        for d in os.listdir(base):
            dp = os.path.join(base, d)
            if os.path.isdir(dp) and keyword.lower() in d.lower():
                return dp
    return base


def do_synthesize(params):
    output = params["output"]

    if engine_name == "cosyvoice":
        import torchaudio
        from cosyvoice.utils.file_utils import load_wav
        ref = params.get("ref_audio")
        if ref:
            prompt = load_wav(ref, 16000)
            for j in MODEL.inference_cross_lingual(params["text"], prompt, stream=False):
                torchaudio.save(output, j["tts_speech"], MODEL.sample_rate)
        else:
            for j in MODEL.inference_sft(params["text"], "中文女", stream=False):
                torchaudio.save(output, j["tts_speech"], MODEL.sample_rate)

    elif engine_name == "qwen3tts":
        import soundfile as sf
        import torch
        ref = params.get("ref_audio")
        if ref:
            wavs, sr = MODEL.generate_custom_voice(text=params["text"], ref_audio=ref, ref_text=params.get("ref_text", ""))
        else:
            wavs, sr = MODEL.generate_voice_design(text=params["text"], description=params.get("description", "A clear and natural voice"))
        sf.write(output, wavs[0].cpu().numpy(), sr)

    elif engine_name == "indextts":
        ref = params.get("ref_audio", "")
        MODEL.infer(ref, params["text"], output_path=output)

    elif engine_name == "voxcpm":
        import soundfile as sf
        import re as _re
        ref = params.get("ref_audio")
        control = (params.get("control_instruction") or "").strip()
        control = _re.sub(r"[()（）]", "", control).strip()
        prompt_text = (params.get("prompt_text") or "").strip() or None
        cfg = float(params.get("cfg_value", 2.0))
        steps = int(params.get("dit_steps", 10))
        do_normalize = bool(params.get("normalize", False))
        do_denoise = bool(params.get("denoise", False))

        final_text = f"({control}){params['text']}" if control else params["text"]

        gen_kwargs = dict(
            text=final_text,
            reference_wav_path=ref,
            cfg_value=cfg,
            inference_timesteps=steps,
            normalize=do_normalize,
            denoise=do_denoise,
        )
        if prompt_text and ref:
            gen_kwargs["prompt_wav_path"] = ref
            gen_kwargs["prompt_text"] = prompt_text

        wav = MODEL.generate(**gen_kwargs)
        sf.write(output, wav, MODEL.tts_model.sample_rate)

    elif engine_name == "mosstts":
        import torch, torchaudio
        model = MODEL["model"]
        processor = MODEL["processor"]
        device = MODEL["device"]
        ref = params.get("ref_audio")
        if ref:
            convs = [processor.build_user_message(text=params["text"], audio=ref)]
        else:
            convs = [processor.build_user_message(text=params["text"])]
        inputs = processor(convs, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=2048)
        audio = processor.decode(out[0])
        torchaudio.save(output, audio["waveform"].cpu(), audio["sample_rate"])

    elif engine_name == "gptsovits":
        gen = MODEL(
            ref_wav_path=params.get("ref_audio") or "",
            prompt_text=params.get("ref_text", ""),
            prompt_language=params.get("language", "zh"),
            text=params["text"],
            text_language=params.get("language", "zh"),
            top_k=20, top_p=0.6, temperature=0.6,
            speed=params.get("speed", 1.0),
        )
        last_sr, last_audio = None, None
        for sr, audio_data in gen:
            last_sr, last_audio = sr, audio_data
        if last_audio is not None:
            import soundfile as sf
            sf.write(output, last_audio, last_sr)
        else:
            raise RuntimeError("No audio generated")

    elif engine_name == "fishspeech":
        import subprocess
        ckpt = MODEL["checkpoint"]
        eng_dir = MODEL["engine_dir"]
        py = sys.executable
        ref = params.get("ref_audio")
        script = os.path.join(eng_dir, "fish_speech", "models", "text2semantic", "inference.py")
        cmd = [py, script, "--text", params["text"], "--output", output, "--checkpoint-path", ckpt]
        if ref:
            cmd += ["--reference-audio", ref]
        subprocess.run(cmd, cwd=eng_dir, check=True)

    elif engine_name == "luxtts":
        import soundfile as sf
        ref = params.get("ref_audio", "")
        if not ref:
            raise RuntimeError("LuxTTS requires reference audio")
        encoded_prompt = MODEL.encode_prompt(ref, rms=0.01)
        final_wav = MODEL.generate_speech(params["text"], encoded_prompt, num_steps=4)
        sf.write(output, final_wav.numpy().squeeze(), 48000)

    elif engine_name == "omnivoice":
        import soundfile as sf
        ref = params.get("ref_audio")
        instruct = params.get("instruct", "")
        num_step = int(params.get("num_step", 32))
        speed = float(params.get("speed", 1.0))

        gen_kwargs = dict(text=params["text"], num_step=num_step, speed=speed)

        if ref:
            gen_kwargs["ref_audio"] = ref
            ref_text = params.get("ref_text", "")
            if ref_text:
                gen_kwargs["ref_text"] = ref_text
        elif instruct:
            gen_kwargs["instruct"] = instruct

        audio = MODEL.generate(**gen_kwargs)
        sf.write(output, audio[0], 24000)

    elif engine_name == "confucius4tts":
        import torch
        import torchaudio
        ref = params.get("ref_audio")
        lang = params.get("language", "zh")
        if ref:
            audio = MODEL.generate(
                text=params["text"],
                lang=lang,
                prompt_wav=ref,
                verbose=True,
            )
        else:
            audio = MODEL.generate(
                text=params["text"],
                lang=lang,
                verbose=True,
            )
        torchaudio.save(output, audio.cpu(), MODEL.sample_rate)

    elif engine_name == "longcataudiodit":
        import torch
        import soundfile as sf
        import librosa
        model = MODEL["model"]
        tokenizer = MODEL["tokenizer"]
        _device = MODEL["device"]
        ref = params.get("ref_audio")
        steps = int(params.get("steps", 16))
        cfg_strength = float(params.get("cfg_strength", 4.0))
        guidance_method = params.get("guidance_method", "apg")
        duration = int(params.get("duration", 62))
        
        if ref:
            audio, _ = librosa.load(ref, sr=24000, mono=True)
            prompt_wav = torch.from_numpy(audio).unsqueeze(0).unsqueeze(0).to(_device)
            prompt_text = params.get("prompt_text", "")
            gen_text = params["text"]
            inputs = tokenizer([f"{prompt_text} {gen_text}"], padding="longest", return_tensors="pt")
            output_audio = model(
                input_ids=inputs.input_ids.to(_device),
                attention_mask=inputs.attention_mask.to(_device),
                prompt_audio=prompt_wav,
                duration=duration,
                steps=steps,
                cfg_strength=cfg_strength,
                guidance_method=guidance_method,
            )
        else:
            inputs = tokenizer([params["text"]], padding="longest", return_tensors="pt")
            output_audio = model(
                input_ids=inputs.input_ids.to(_device),
                attention_mask=inputs.attention_mask.to(_device),
                duration=duration,
                steps=steps,
                cfg_strength=cfg_strength,
                guidance_method=guidance_method,
            )
        sf.write(output, output_audio.waveform.squeeze().cpu().numpy(), 24000)

    elif engine_name == "viitorvoice":
        import soundfile as sf
        ref = params.get("ref_audio")
        duration = float(params.get("duration", 0))
        if not ref:
            raise RuntimeError("ViiTor Voice requires reference audio")
        gen_kwargs = dict(prompt=ref, text=params["text"], output=output)
        if duration > 0:
            gen_kwargs["duration"] = duration
        MODEL.tts(**gen_kwargs)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/status":
            self._json_response({"ready": READY, "error": ERROR, "engine": engine_name})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/synthesize":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            params = json.loads(body)
            params.setdefault("output", str(Path(engine_dir) / "outputs" / f"{uuid.uuid4().hex[:10]}.wav"))
            os.makedirs(os.path.dirname(params["output"]), exist_ok=True)
            try:
                do_synthesize(params)
                self._json_response({"success": True, "output": params["output"]})
            except Exception as e:
                self._json_response({"success": False, "error": str(e)})
        elif self.path == "/shutdown":
            self._json_response({"status": "shutting_down"})
            def _shutdown():
                import time
                time.sleep(0.5)
                os._exit(0)
            threading.Thread(target=_shutdown, daemon=True).start()
        else:
            self.send_error(404)

    def _json_response(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


print(json.dumps({"status": "loading", "port": port}), flush=True)
load_model()
if READY:
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(json.dumps({"status": "listening", "port": port}), flush=True)
    server.serve_forever()
else:
    print(json.dumps({"status": "failed", "error": ERROR}), flush=True)
    sys.exit(1)
