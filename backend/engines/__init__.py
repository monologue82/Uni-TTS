import json
import uuid
import textwrap
from pathlib import Path
from .base import BaseEngine, TTSRequest, TTSResult


class GPTSoVITSEngine(BaseEngine):
    name = "gptsovits"
    display_name = "GPT-SoVITS"
    port = 7861

    def get_gradio_script(self) -> str:
        return "webui.py"

    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        script = textwrap.dedent("""\
            import sys, json, os, re, torch, numpy as np, soundfile as sf
            os.chdir(params["engine_dir"])
            sys.path.insert(0, params["engine_dir"])

            from GPT_SoVITS.inference_webui import change_gpt_weights, change_sovits_weights, get_tts_wav

            gpt_dir = os.path.join(params["model_dir"], "GPT-SoVITS")
            sovits_dir = os.path.join(params["model_dir"], "GPT-SoVITS")

            gpt_models = [f for f in os.listdir(gpt_dir) if f.endswith(".pth")] if os.path.isdir(gpt_dir) else []
            sovits_models = [f for f in os.listdir(sovits_dir) if f.endswith(".pth")] if os.path.isdir(sovits_dir) else []

            if gpt_models:
                change_gpt_weights(os.path.join(gpt_dir, gpt_models[0]))
            if sovits_models:
                change_sovits_weights(os.path.join(sovits_dir, sovits_models[0]))

            lang_map = {"zh": "zh", "en": "en", "ja": "ja", "ko": "ko"}
            lang = lang_map.get(params["language"], "zh")

            ref_audio = params.get("ref_audio") or ""
            ref_text = params.get("extra_params", {}).get("ref_text", "")

            gen = get_tts_wav(
                ref_wav_path=ref_audio,
                prompt_text=ref_text,
                prompt_language=lang,
                text=params["text"],
                text_language=lang,
                top_k=20,
                top_p=0.6,
                temperature=0.6,
                speed=params.get("speed", 1.0),
            )

            last_audio = None
            sr = None
            for sr, audio_data in gen:
                last_audio = audio_data

            if last_audio is not None:
                import soundfile as sf
                sf.write(params["output"], last_audio, sr)
            else:
                raise RuntimeError("No audio generated")
        """)
        return await self.run_inference_script(script, request, output_dir, timeout=120)


class CosyVoiceEngine(BaseEngine):
    name = "cosyvoice"
    display_name = "CosyVoice"
    port = 7862

    def get_gradio_script(self) -> str:
        return "webui.py"

    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        script = textwrap.dedent("""\
            import sys, json, os, torch, torchaudio
            sys.path.insert(0, os.path.join(params["engine_dir"], "third_party", "Matcha-TTS"))
            sys.path.insert(0, params["engine_dir"])
            os.chdir(params["engine_dir"])

            from cosyvoice.cli.cosyvoice import CosyVoice2
            from cosyvoice.utils.file_utils import load_wav

            model_dir = os.path.join(params["model_dir"], "CosyVoice2-0.5B")
            if not os.path.isdir(model_dir):
                for d in os.listdir(params["model_dir"]):
                    dp = os.path.join(params["model_dir"], d)
                    if os.path.isdir(dp) and "cosyvoice" in d.lower():
                        model_dir = dp
                        break

            cosyvoice = CosyVoice2(model_dir, load_jit=False, load_trt=False, fp16=False)

            ref_audio = params.get("ref_audio")
            if ref_audio:
                prompt_speech = load_wav(ref_audio, 16000)
                for i, j in enumerate(cosyvoice.inference_cross_lingual(params["text"], prompt_speech, stream=False)):
                    torchaudio.save(params["output"], j["tts_speech"], cosyvoice.sample_rate)
            else:
                for i, j in enumerate(cosyvoice.inference_sft(params["text"], "中文女", stream=False)):
                    torchaudio.save(params["output"], j["tts_speech"], cosyvoice.sample_rate)
        """)
        return await self.run_inference_script(script, request, output_dir, timeout=120)


class Qwen3TTSEngine(BaseEngine):
    name = "qwen3tts"
    display_name = "Qwen3-TTS"
    port = 7863

    def get_gradio_script(self) -> str:
        return "app.py"

    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        script = textwrap.dedent("""\
            import sys, json, os, torch, soundfile as sf
            os.chdir(params["engine_dir"])
            sys.path.insert(0, params["engine_dir"])

            from qwen_tts import Qwen3TTSModel

            model_path = os.path.join(params["model_dir"], "Qwen3-TTS-12Hz-1.7B-Base")
            if not os.path.isdir(model_path):
                for d in os.listdir(params["model_dir"]):
                    dp = os.path.join(params["model_dir"], d)
                    if os.path.isdir(dp):
                        model_path = dp
                        break

            model = Qwen3TTSModel.from_pretrained(
                model_path,
                device_map="cuda:0",
                dtype=torch.bfloat16,
            )

            ref_audio = params.get("ref_audio")
            if ref_audio:
                wavs, sr = model.generate_custom_voice(
                    text=params["text"],
                    ref_audio=ref_audio,
                    ref_text=params.get("extra_params", {}).get("ref_text", ""),
                )
            else:
                wavs, sr = model.generate_voice_design(
                    text=params["text"],
                    description=params.get("extra_params", {}).get("description", "A clear and natural voice"),
                )

            sf.write(params["output"], wavs[0].cpu().numpy(), sr)
        """)
        return await self.run_inference_script(script, request, output_dir, timeout=120)


class IndexTTSEngine(BaseEngine):
    name = "indextts"
    display_name = "IndexTTS-2"
    port = 7864

    def get_gradio_script(self) -> str:
        return "webui.py"

    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        script = textwrap.dedent("""\
            import sys, json, os, torch, soundfile as sf
            os.chdir(params["engine_dir"])
            sys.path.insert(0, params["engine_dir"])

            from indextts.infer import IndexTTS

            checkpoint_dir = os.path.join(params["model_dir"], "IndexTTS-2")
            if not os.path.isdir(checkpoint_dir):
                for d in os.listdir(params["model_dir"]):
                    dp = os.path.join(params["model_dir"], d)
                    if os.path.isdir(dp):
                        checkpoint_dir = dp
                        break

            cfg_path = os.path.join(checkpoint_dir, "config.yaml")
            ckpt_dir = checkpoint_dir

            tts = IndexTTS(cfg_path, ckpt_dir)

            ref_audio = params.get("ref_audio", "")
            emotion = params.get("emotion", "neutral")
            speed = params.get("speed", 1.0)

            audio = tts.infer(
                ref_audio,
                params["text"],
                output_path=params["output"],
            )
        """)
        return await self.run_inference_script(script, request, output_dir, timeout=120)


class LuxTTSEngine(BaseEngine):
    name = "luxtts"
    display_name = "LuxTTS"
    port = 7865

    def get_gradio_script(self) -> str:
        return "app.py"

    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        script = textwrap.dedent("""\
            import sys, json, os, torch, soundfile as sf
            os.chdir(params["engine_dir"])
            sys.path.insert(0, params["engine_dir"])

            from zipvoice.luxvoice import LuxTTS

            model_dir = params["model_dir"]
            tts = LuxTTS(model_dir)

            ref_audio = params.get("ref_audio", "")
            if not ref_audio:
                raise RuntimeError("LuxTTS requires a reference audio for voice cloning")

            encoded_prompt = tts.encode_prompt(ref_audio, rms=0.01)
            final_wav = tts.generate_speech(params["text"], encoded_prompt, num_steps=4)

            sf.write(params["output"], final_wav.numpy().squeeze(), 48000)
        """)
        return await self.run_inference_script(script, request, output_dir, timeout=120)


class VoxCPMEngine(BaseEngine):
    name = "voxcpm"
    display_name = "VoxCPM 2"
    port = 7866

    def get_gradio_script(self) -> str:
        return "app.py"

    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        script = textwrap.dedent("""\
            import sys, json, os, torch, soundfile as sf
            os.chdir(params["engine_dir"])
            sys.path.insert(0, params["engine_dir"])

            from voxcpm import VoxCPM

            model_path = os.path.join(params["model_dir"], "VoxCPM2")
            if not os.path.isdir(model_path):
                model_path = params["model_dir"]

            model = VoxCPM.from_pretrained(model_path)

            ref_audio = params.get("ref_audio")
            control = params.get("extra_params", {}).get("control_instruction", "")
            prompt_text = params.get("extra_params", {}).get("prompt_text", "")

            gen_kwargs = dict(
                text=params["text"],
                reference_wav_path=ref_audio,
                cfg_value=float(params.get("extra_params", {}).get("cfg_value", 2.0)),
                inference_timesteps=int(params.get("extra_params", {}).get("dit_steps", 10)),
            )
            if control:
                gen_kwargs["text"] = f"({control}){params['text']}"
            if prompt_text and ref_audio:
                gen_kwargs["prompt_wav_path"] = ref_audio
                gen_kwargs["prompt_text"] = prompt_text

            wav = model.generate(**gen_kwargs)
            sf.write(params["output"], wav, model.tts_model.sample_rate)
        """)
        return await self.run_inference_script(script, request, output_dir, timeout=120)


class MossTTSEngine(BaseEngine):
    name = "mosstts"
    display_name = "MOSS-TTS"
    port = 7867

    def get_gradio_script(self) -> str:
        return "clis/moss_tts_app.py"

    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        script = textwrap.dedent("""\
            import sys, json, os, torch, torchaudio
            os.chdir(params["engine_dir"])
            sys.path.insert(0, params["engine_dir"])

            from transformers import AutoModel, AutoProcessor

            model_id = os.path.join(params["model_dir"], "MOSS-TTS")
            if not os.path.isdir(model_id):
                for d in os.listdir(params["model_dir"]):
                    dp = os.path.join(params["model_dir"], d)
                    if os.path.isdir(dp):
                        model_id = dp
                        break

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.bfloat16 if device == "cuda" else torch.float32

            processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
            model = AutoModel.from_pretrained(
                model_id, trust_remote_code=True,
                torch_dtype=dtype, attn_implementation="eager",
            ).to(device)
            model.eval()

            ref_audio = params.get("ref_audio")
            if ref_audio:
                conversations = [
                    processor.build_user_message(text=params["text"], audio=ref_audio),
                ]
            else:
                conversations = [
                    processor.build_user_message(text=params["text"]),
                ]

            inputs = processor(conversations, return_tensors="pt").to(device)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_new_tokens=2048)

            audio = processor.decode(outputs[0])
            torchaudio.save(params["output"], audio["waveform"].cpu(), audio["sample_rate"])
        """)
        return await self.run_inference_script(script, request, output_dir, timeout=120)


class FishSpeechEngine(BaseEngine):
    name = "fishspeech"
    display_name = "Fish Audio S2 Pro"
    port = 7868

    def get_gradio_script(self) -> str:
        return "fish_speech/webui.py"

    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        script = textwrap.dedent("""\
            import sys, json, os, subprocess
            os.chdir(params["engine_dir"])
            sys.path.insert(0, params["engine_dir"])

            checkpoint = os.path.join(params["model_dir"], "s2-pro")
            if not os.path.isdir(checkpoint):
                for d in os.listdir(params["model_dir"]):
                    dp = os.path.join(params["model_dir"], d)
                    if os.path.isdir(dp):
                        checkpoint = dp
                        break

            ref_audio = params.get("ref_audio")
            text = params["text"]
            output = params["output"]
            engine_dir = params["engine_dir"]

            if ref_audio:
                python = sys.executable
                vq_script = os.path.join(engine_dir, "fish_speech", "models", "dac", "inference.py")
                codec_path = os.path.join(checkpoint, "codec.pth")

                npy_out = output.replace(".wav", "_vq.npy")
                subprocess.run([
                    python, vq_script,
                    "-i", ref_audio,
                    "--checkpoint-path", codec_path,
                    "--output-path", npy_out,
                ], check=True, cwd=engine_dir)

                synth_script = os.path.join(engine_dir, "fish_speech", "models", "text2semantic", "inference.py")
                subprocess.run([
                    python, synth_script,
                    "--text", text,
                    "--output", output,
                    "--checkpoint-path", checkpoint,
                    "--reference-audio", ref_audio,
                ], check=True, cwd=engine_dir)
            else:
                python = sys.executable
                synth_script = os.path.join(engine_dir, "fish_speech", "models", "text2semantic", "inference.py")
                subprocess.run([
                    python, synth_script,
                    "--text", text,
                    "--output", output,
                    "--checkpoint-path", checkpoint,
                ], check=True, cwd=engine_dir)

            if not os.path.exists(output):
                raise RuntimeError("Fish Speech failed to generate audio")
        """)
        return await self.run_inference_script(script, request, output_dir, timeout=120)


class OmniVoiceEngine(BaseEngine):
    name = "omnivoice"
    display_name = "OmniVoice"
    port = 7869

    def get_gradio_script(self) -> str:
        return ""

    async def synthesize(self, request: TTSRequest, output_dir: Path) -> TTSResult:
        script = textwrap.dedent("""\
            import sys, json, os, torch, soundfile as sf
            os.chdir(params["engine_dir"])
            sys.path.insert(0, params["engine_dir"])

            from omnivoice import OmniVoice

            model = OmniVoice.from_pretrained(
                params["model_dir"],
                device_map="cuda:0" if torch.cuda.is_available() else "cpu",
                dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            )

            ref_audio = params.get("ref_audio")
            instruct = params.get("extra_params", {}).get("instruct", "")
            num_step = int(params.get("extra_params", {}).get("num_step", 32))
            speed = float(params.get("speed", 1.0))

            gen_kwargs = dict(text=params["text"], num_step=num_step, speed=speed)

            if ref_audio:
                gen_kwargs["ref_audio"] = ref_audio
                ref_text = params.get("extra_params", {}).get("ref_text", "")
                if ref_text:
                    gen_kwargs["ref_text"] = ref_text
            elif instruct:
                gen_kwargs["instruct"] = instruct

            audio = model.generate(**gen_kwargs)
            sf.write(params["output"], audio[0], 24000)
        """)
        return await self.run_inference_script(script, request, output_dir, timeout=180)


ENGINE_CLASSES: dict[str, type[BaseEngine]] = {
    "gptsovits": GPTSoVITSEngine,
    "cosyvoice": CosyVoiceEngine,
    "qwen3tts": Qwen3TTSEngine,
    "indextts": IndexTTSEngine,
    "luxtts": LuxTTSEngine,
    "voxcpm": VoxCPMEngine,
    "mosstts": MossTTSEngine,
    "fishspeech": FishSpeechEngine,
    "omnivoice": OmniVoiceEngine,
}


def get_engine(name: str, base_dir: Path) -> BaseEngine:
    cls = ENGINE_CLASSES.get(name)
    if cls is None:
        raise ValueError(f"Unknown engine: {name}")
    return cls(base_dir)
