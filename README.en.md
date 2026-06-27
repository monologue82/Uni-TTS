<div align="center">

  **English** | [简体中文](README.md)

  <img src="assets/logo.png" alt="Uni-TTS" width="300" height="300">

  <p>
    <strong>Unified Multi-Engine Text-to-Speech Platform</strong>
  </p>

  <p>
    <a href="#features">Features</a> •
    <a href="#supported-engines">Supported Engines</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#usage">Usage</a> •
    <a href="#license">License</a>
  </p>

</div>

---

## Features

- 🚀 **One-Click Installation**: Each engine runs in an isolated virtual environment, auto-installed with one click — no dependency conflicts
- 🎯 **Unified Interface**: Manage all engines in one web UI, switch effortlessly
- 📦 **Model Management**: Built-in model download manager, supports ModelScope / HuggingFace sources
- 🔧 **Flexible Configuration**: GPU / CPU switching, optional Flash Attention
- 🎨 **Beautiful UI**: Modern Vue 3 + Element Plus frontend, intuitive operation
- 🔊 **ASR Integration**: Built-in speech recognition, auto-fills reference audio text
- ⚡ **Parallel Loading**: Multiple engines can be loaded simultaneously without interference

## Supported Engines

| Engine | Description | Min VRAM |
|--------|-------------|----------|
| **GPT-SoVITS** | High-quality TTS with just 1 minute of training data | 4 GB |
| **CosyVoice** | Alibaba's multilingual speech generation model | 4 GB |
| **Qwen3-TTS** | Qwen 3-second voice cloning, 10+ languages | 6 GB |
| **IndexTTS-2** | Emotion-rich, duration-controllable zero-shot TTS | 4 GB |
| **LuxTTS** | Lightweight & fast, 150x real-time with 1GB VRAM | 1 GB |
| **VoxCPM 2** | Tsinghua's tokenizer-free TTS, 30 languages, 48kHz | 8 GB |
| **MOSS-TTS** | Fudan's open-source speech suite, high-fidelity long text | 4 GB |
| **Fish Audio S2 Pro** | 15000+ emotion tags, 80+ languages, 100ms first frame | 8 GB |

## Quick Start

### Requirements

- Python 3.10+
- Node.js 18+
- (Optional) NVIDIA GPU + CUDA 12.1+

### Installation & Launch

```bash
# Clone the repository
git clone https://github.com/monologue82/Uni-TTS.git
cd Uni-TTS

# Recommended: use a virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install backend dependencies
pip install -r requirements.txt

# Launch (auto-installs frontend dependencies)
python start.py
```

Once started, visit:
- Frontend UI: http://localhost:5173
- Backend API: http://localhost:8000

## Usage

### 1. Install an Engine

Go to the **Engine Management** page, click the **Install** button on the desired engine card, and wait for the automatic installation to complete.

### 2. Download Models

Go to the **Model Management** page, select an engine and click **Download** to get the corresponding model files.

### 3. Start Inference

Back on the home page, click an engine card and choose **Start Inference** or **Gradio UI**. Wait for the model to load and you're ready to go.

## Project Structure

```
Uni-TTS/
├── backend/          # Backend (FastAPI)
│   ├── api/          # API routes
│   ├── engines/      # Inference servers
│   └── db/           # Database
├── frontend/         # Frontend (Vue 3 + Element Plus)
│   └── src/
├── engines/          # Engine source code (generated after install)
├── venvs/            # Engine virtual environments (generated after install)
├── models/           # Model files (generated after download)
└── start.py          # Launch script
```

## License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)** License.

**Summary (for informational purposes only, not legal advice):**

- ✅ **Permitted**: Copy, distribute, modify, and adapt the work
- ✅ **Required**: Attribution, share-alike, indication of changes
- ❌ **Prohibited**: Commercial use is not allowed

See the [LICENSE](LICENSE) file for the full license text.

Each sub-engine follows its own open-source license. Please comply with the corresponding licenses when using them.

## Disclaimer

This project is for learning and research purposes only. Do not use it for any illegal purposes. Users are solely responsible for the audio content generated using this project.

---

<div align="center">
  <p>If you find this project helpful, please give it a ⭐ Star</p>
</div>
