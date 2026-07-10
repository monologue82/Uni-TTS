# Uni-TTS 一站式 TTS 工作站 — 构建计划

## 一、项目概述

**项目名称**: Uni-TTS (Unified TTS Workstation)
**定位**: 集成 8 大主流开源 TTS 引擎的一站式 Web 工作站
**技术栈**: Python + FastAPI + Vue 3 (前端) + SQLite (配置/任务存储)

### 支持的 TTS 引擎

| # | TTS 引擎 | GitHub 仓库 | 入口文件 | Python 版本 | ModelScope 模型 ID |
|---|----------|-------------|----------|-------------|-------------------|
| 1 | GPT-SoVITS | `RVC-Boss/GPT-SoVITS` | `webui.py` | 3.10 | `XXXXRT/GPT-SoVITS-Pretrained` |
| 2 | CosyVoice | `FunAudioLLM/CosyVoice` | `webui.py` | 3.10 | `iic/CosyVoice-300M-SFT` / `iic/CosyVoice2-0.5B` |
| 3 | Qwen3-TTS | `QwenLM/Qwen3-TTS` | `app.py` (qwen-tts-demo) | 3.10+ | `Qwen/Qwen3-TTS-12Hz-0.6B-Base` / `Qwen/Qwen3-TTS-12Hz-1.7B-Base` |
| 4 | IndexTTS-2 | `index-tts/index-tts` | `webui.py` | 3.10 | `IndexTeam/IndexTTS-2` |
| 5 | LuxTTS | `ysharma3501/LuxTTS` | `app.py` | 3.10 | `luxtts/LuxTTS` |
| 6 | VoxCPM 2 | `OpenBMB/VoxCPM` | `app.py` | 3.10+ | `OpenBMB/VoxCPM2` |
| 7 | MOSS-TTS | `OpenMOSS/MOSS-TTS` | `demo/demo_moss_tts.py` | 3.10 | `OpenMOSS/MOSS-TTS` |
| 8 | Fish Audio S2 Pro | `fishaudio/fish-speech` | `fish_speech/webui.py` | 3.10+ | `fishaudio/s2-pro` |

---

## 二、系统架构

```
Uni-TTS/
├── main.py                    # FastAPI 主入口
├── config.yaml                # 全局配置
├── requirements.txt           # 主站依赖
│
├── frontend/                  # Vue 3 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue           # 首页 (TTS 卡片选择)
│   │   │   ├── Inference.vue      # 现代化推理页面
│   │   │   ├── ModelManager.vue   # 模型管理页面
│   │   │   └── GradioEmbed.vue    # Gradio 原版嵌入页面
│   │   ├── components/
│   │   │   ├── TTSCard.vue        # TTS 引擎卡片组件
│   │   │   ├── AudioPlayer.vue    # 音频播放器
│   │   │   ├── BatchPanel.vue     # 批量推理面板
│   │   │   └── DownloadTask.vue   # 下载任务组件
│   │   └── ...
│   └── package.json
│
├── backend/                   # 后端 API
│   ├── api/
│   │   ├── tts.py                 # TTS 推理 API
│   │   ├── models.py              # 模型管理 API
│   │   ├── batch.py               # 批量推理 API
│   │   └── engines.py             # TTS 引擎抽象层
│   ├── engines/                   # 各引擎适配器
│   │   ├── base.py                # 引擎基类
│   │   ├── gptsovits.py
│   │   ├── cosyvoice.py
│   │   ├── qwen3tts.py
│   │   ├── indextts.py
│   │   ├── luxtts.py
│   │   ├── voxcpm.py
│   │   ├── mosstts.py
│   │   └── fishspeech.py
│   ├── downloader/                # ModelScope 下载器
│   │   ├── manager.py
│   │   └── modelscope_client.py
│   └── db/
│       └── database.py            # SQLite 数据库
│
├── engines/                   # 各 TTS 引擎源码 (git clone)
│   ├── GPT-SoVITS/
│   ├── CosyVoice/
│   ├── Qwen3-TTS/
│   ├── index-tts/
│   ├── LuxTTS/
│   ├── VoxCPM/
│   ├── MOSS-TTS/
│   └── fish-speech/
│
├── venvs/                     # 各引擎独立虚拟环境
│   ├── gptsovits/
│   ├── cosyvoice/
│   ├── qwen3tts/
│   ├── indextts/
│   ├── luxtts/
│   ├── voxcpm/
│   ├── mosstts/
│   └── fishspeech/
│
├── models/                    # 模型文件存放
│   ├── GPT-SoVITS/
│   ├── CosyVoice/
│   ├── Qwen3-TTS/
│   ├── IndexTTS/
│   ├── LuxTTS/
│   ├── VoxCPM/
│   ├── MOSS-TTS/
│   └── FishSpeech/
│
└── outputs/                   # 合成音频输出
```

---

## 三、核心功能模块

### 3.1 首页 — TTS 引擎卡片选择

**设计风格**: 玻璃拟态 (Glassmorphism) + 暗色主题
- 顶部: Logo + 导航栏 (首页 / 模型管理 / 设置)
- 主体: 8 张 TTS 引擎卡片，2×4 或 4×2 网格布局
- 每张卡片包含:
  - 引擎 Logo/图标
  - 引擎名称
  - 一句话描述 (如 "5秒零样本语音克隆")
  - 状态指示灯 (已安装 / 未安装 / 模型未下载)
  - 悬停动效 (缩放 + 光晕)

**卡片状态逻辑**:
1. **就绪** (绿色): 引擎已安装 + 模型已下载 → 点击进入推理页
2. **未安装** (黄色): 引擎源码未克隆 / 虚拟环境未创建 → 提示先安装
3. **模型缺失** (橙色): 引擎已安装但模型未下载 → 提示先下载模型
4. **不可用** (灰色): 系统不满足依赖 (如无 GPU)

### 3.2 推理页面 — 双模式

用户点击卡片后，提供两种推理模式选择:

#### 模式 A: 现代化推理页面 (自研)

统一的现代化 UI，包含:

**基础功能区**:
- 文本输入框 (支持多行、SSML 标签)
- 参考音频上传 (用于音色克隆)
- 语速 / 音调 / 情感 滑块控制
- 生成按钮 + 实时进度条
- 音频播放器 + 波形可视化
- 下载按钮 (WAV/MP3)

**引擎特有功能** (根据引擎动态显示):
| 引擎 | 特有功能 |
|------|---------|
| GPT-SoVITS | 语言选择 (中/英/日/韩)、模型版本选择 (v1/v2/v3/v4) |
| CosyVoice | SFT/Instruct 模式切换、方言选择、指令控制 |
| Qwen3-TTS | 语音设计 (自然语言描述)、预置音色选择 |
| IndexTTS-2 | 情感控制 (4种方式)、时长精确控制 |
| LuxTTS | 极速模式开关 (150x实时) |
| VoxCPM 2 | 30种语言选择、语音设计、副语言控制 |
| MOSS-TTS | 多说话人对话、环境音效、角色设计 |
| Fish S2 Pro | 15000+情感标签、多说话人、内联情感标注 |

**批量推理功能**:
- 文本批量导入 (TXT/CSV/Excel)
- 批量任务队列管理
- 统一输出目录
- 进度追踪 + 失败重试
- 批量导出 (ZIP 打包)

#### 模式 B: Gradio 原版演示页面

通过 `<iframe>` 嵌入各引擎官方 Gradio Demo:
- 启动各引擎的原版 `webui.py` / `app.py`
- 在前端通过 iframe 嵌入 `http://localhost:<port>`
- 每个引擎分配独立端口 (如 7861-7868)

### 3.3 模型管理页面

**功能**:
- 展示所有 8 个引擎的模型列表
- 每个模型显示: 名称、大小、版本、下载状态、ModelScope 链接
- 一键下载按钮 (从 ModelScope 下载)
- 下载进度条 + 速度显示
- 下载完成后自动移动到对应目录
- 模型删除功能
- 磁盘空间占用统计

**ModelScope 下载实现**:
```python
from modelscope import snapshot_download

# 下载模型到指定目录
snapshot_download(
    model_id='Qwen/Qwen3-TTS-12Hz-1.7B-Base',
    local_dir='models/Qwen3-TTS/Qwen3-TTS-12Hz-1.7B-Base'
)
```

---

## 四、各引擎详细配置

### 4.1 GPT-SoVITS

- **GitHub**: https://github.com/RVC-Boss/GPT-SoVITS
- **入口**: `webui.py` (端口 7861)
- **Python**: 3.10
- **依赖**: `requirements.txt` + ffmpeg
- **模型目录**: `engines/GPT-SoVITS/GPT_SoVITS/pretrained_models/`
- **ModelScope 模型**:
  - `XXXXRT/GPT-SoVITS-Pretrained` (预训练模型)
  - `iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch` (ASR)
  - `iic/speech_fsmn_vad_zh-cn-16k-common-pytorch` (VAD)
  - `iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch` (标点)
- **功能**: 零样本TTS、少样本TTS、跨语言推理、语音伴奏分离、ASR标注

### 4.2 CosyVoice

- **GitHub**: https://github.com/FunAudioLLM/CosyVoice
- **入口**: `webui.py` (端口 7862)
- **Python**: 3.10
- **依赖**: `requirements.txt` + pynini==2.1.5 (conda)
- **模型目录**: `engines/CosyVoice/pretrained_models/`
- **ModelScope 模型**:
  - `iic/CosyVoice-300M-SFT`
  - `iic/CosyVoice-300M-Instruct`
  - `iic/CosyVoice2-0.5B`
- **功能**: SFT推理、Instruct推理、零样本克隆、跨语言合成

### 4.3 Qwen3-TTS

- **GitHub**: https://github.com/QwenLM/Qwen3-TTS
- **入口**: `app.py` / `qwen-tts-demo` CLI (端口 7863)
- **Python**: 3.10+
- **依赖**: `requirements.txt` (transformers, torch, gradio)
- **模型目录**: `engines/Qwen3-TTS/checkpoints/`
- **ModelScope 模型**:
  - `Qwen/Qwen3-TTS-12Hz-0.6B-Base`
  - `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
  - `Qwen/Qwen3-TTS-12Hz-0.6B-VoiceDesign`
  - `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`
- **功能**: 3秒语音克隆、语音设计、10种语言、流式生成

### 4.4 IndexTTS-2

- **GitHub**: https://github.com/index-tts/index-tts
- **入口**: `webui.py` (端口 7864)
- **Python**: 3.10
- **依赖**: `requirements.txt` / `uv sync`
- **模型目录**: `engines/index-tts/checkpoints/`
- **ModelScope 模型**:
  - `IndexTeam/IndexTTS-2`
- **功能**: 情感控制 (4种方式)、时长精确控制、零样本克隆

### 4.5 LuxTTS

- **GitHub**: https://github.com/ysharma3501/LuxTTS
- **入口**: `app.py` (端口 7865)
- **Python**: 3.10
- **依赖**: `requirements.txt`
- **模型目录**: `engines/LuxTTS/checkpoints/`
- **ModelScope 模型**:
  - `luxtts/LuxTTS`
- **功能**: 150x实时速度、1GB显存运行、高质量声音克隆

### 4.6 VoxCPM 2

- **GitHub**: https://github.com/OpenBMB/VoxCPM
- **入口**: `app.py` (端口 7866)
- **Python**: 3.10+ (< 3.13)
- **依赖**: `pip install voxcpm` + `requirements.txt`
- **模型目录**: 自动下载到 `~/.cache/` 或指定目录
- **ModelScope 模型**:
  - `OpenBMB/VoxCPM2`
- **功能**: 30种语言、语音设计、声音克隆、48kHz输出

### 4.7 MOSS-TTS

- **GitHub**: https://github.com/OpenMOSS/MOSS-TTS
- **入口**: `demo/demo_moss_tts.py` (端口 7867)
- **Python**: 3.10
- **依赖**: `requirements.txt`
- **模型目录**: `engines/MOSS-TTS/checkpoints/`
- **ModelScope 模型**:
  - `OpenMOSS/MOSS-TTS`
  - `OpenMOSS/MOSS-TTS-Nano` (轻量版)
- **功能**: 高保真长文本、多说话人对话、角色设计、环境音效、流式TTS

### 4.8 Fish Audio S2 Pro

- **GitHub**: https://github.com/fishaudio/fish-speech
- **入口**: `fish_speech/webui.py` (端口 7868)
- **Python**: 3.10+
- **依赖**: `requirements.txt`
- **模型目录**: `engines/fish-speech/checkpoints/s2-pro/`
- **ModelScope 模型**:
  - `fishaudio/s2-pro`
- **功能**: 15000+情感标签、80+语言、多说话人、100ms首音频延迟

---

## 五、实现步骤 (分阶段)

### Phase 1: 基础框架 (第1-2周)

1. **项目初始化**
   - 创建项目目录结构
   - 初始化 Git 仓库
   - 配置 FastAPI 后端框架
   - 配置 Vue 3 + Vite 前端框架
   - 设计 SQLite 数据库表结构

2. **首页 TTS 卡片页面**
   - 设计玻璃拟态 UI 风格
   - 实现 8 张 TTS 卡片组件
   - 实现卡片状态检测逻辑
   - 响应式布局适配

3. **引擎安装管理器**
   - 实现 Git 克隆各引擎源码
   - 实现虚拟环境创建 (`venv` / `conda`)
   - 实现各引擎依赖安装
   - 安装状态持久化

### Phase 2: 模型管理 (第3周)

4. **ModelScope 下载器**
   - 集成 `modelscope` SDK
   - 实现模型下载任务队列
   - 实现下载进度回调
   - 实现下载完成后自动移动到对应目录

5. **模型管理页面**
   - 模型列表展示
   - 下载状态管理
   - 磁盘空间统计
   - 模型删除功能

### Phase 3: 推理功能 (第4-6周)

6. **引擎抽象层**
   - 定义统一的引擎基类 `BaseEngine`
   - 实现各引擎适配器
   - 统一输入/输出接口

7. **现代化推理页面**
   - 文本输入 + 参考音频上传
   - 参数控制面板 (语速/音调/情感)
   - 音频播放器 + 波形可视化
   - 各引擎特有功能面板
   - 生成历史记录

8. **批量推理功能**
   - 文本批量导入 (TXT/CSV/Excel)
   - 任务队列管理
   - 进度追踪
   - 批量导出

### Phase 4: Gradio 嵌入 & 收尾 (第7周)

9. **Gradio 原版嵌入**
   - 实现各引擎 Gradio Demo 启动器
   - iframe 嵌入集成
   - 端口管理

10. **测试 & 优化**
    - 全流程功能测试
    - 性能优化
    - 错误处理完善
    - 用户文档编写

---

## 六、关键技术决策

### 6.1 虚拟环境隔离方案

采用 Python `venv` 为每个引擎创建独立虚拟环境:

```python
import subprocess
import venv

def create_engine_venv(engine_name, python_path="python3.10"):
    venv_path = f"venvs/{engine_name}"
    venv.create(venv_path, with_pip=True)
    
    pip_path = f"{venv_path}/bin/pip"  # Linux
    # pip_path = f"{venv_path}/Scripts/pip.exe"  # Windows
    
    # 安装引擎依赖
    subprocess.run([pip_path, "install", "-r", f"engines/{engine_name}/requirements.txt"])
```

### 6.2 引擎调用方式

通过子进程调用各引擎的虚拟环境 Python:

```python
def run_engine_inference(engine_name, script_path, args):
    python_path = f"venvs/{engine_name}/bin/python"
    subprocess.Popen([python_path, script_path] + args)
```

### 6.3 前后端通信

- **REST API**: 模型管理、任务管理
- **WebSocket**: 推理进度实时推送
- **iframe**: Gradio 原版嵌入

### 6.4 ModelScope 下载

```python
from modelscope import snapshot_download

def download_model(model_id, local_dir):
    snapshot_download(model_id, local_dir=local_dir)
```

---

## 七、UI 设计规范

### 色彩方案
- **主色**: `#6366f1` (Indigo)
- **强调色**: `#22d3ee` (Cyan)
- **背景**: `#0f172a` (深蓝黑)
- **卡片背景**: `rgba(255, 255, 255, 0.05)` (毛玻璃)
- **成功**: `#22c55e`
- **警告**: `#f59e0b`
- **错误**: `#ef4444`

### 字体
- 标题: Inter / Noto Sans SC
- 正文: Inter / Noto Sans SC
- 代码: JetBrains Mono

### 组件风格
- 圆角: 12px-16px
- 阴影: 多层柔和阴影
- 动效: 平滑过渡 (300ms ease)
- 玻璃拟态: backdrop-filter: blur(12px)

---

## 八、端口分配

| 端口 | 用途 |
|------|------|
| 8000 | Uni-TTS 主站 (FastAPI) |
| 5173 | 前端开发服务器 (Vite) |
| 7861 | GPT-SoVITS Gradio |
| 7862 | CosyVoice Gradio |
| 7863 | Qwen3-TTS Gradio |
| 7864 | IndexTTS-2 Gradio |
| 7865 | LuxTTS Gradio |
| 7866 | VoxCPM 2 Gradio |
| 7867 | MOSS-TTS Gradio |
| 7868 | Fish S2 Pro Gradio |

---

## 九、硬件要求

| 引擎 | 最低显存 | 推荐显存 | CPU 可用 |
|------|---------|---------|---------|
| GPT-SoVITS | 4 GB | 8 GB | 否 |
| CosyVoice | 4 GB | 8 GB | 否 |
| Qwen3-TTS | 4 GB (0.6B) / 6 GB (1.7B) | 8-12 GB | 否 |
| IndexTTS-2 | 4 GB | 8 GB | 否 |
| LuxTTS | 1 GB | 4 GB | 是 (150x实时) |
| VoxCPM 2 | 8 GB | 12 GB | 否 |
| MOSS-TTS | 4 GB (Nano) / 16 GB (Full) | 8-24 GB | 是 (Nano) |
| Fish S2 Pro | 8 GB | 16 GB | 否 |

---

## 十、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 引擎依赖冲突 | 部分引擎无法共存 | 虚拟环境完全隔离 |
| 模型文件过大 | 磁盘空间不足 | 支持按需下载、模型共用检测 |
| 引擎 API 变更 | 推理功能失效 | 引擎抽象层 + 版本锁定 |
| GPU 显存不足 | 推理失败 | 显存检测 + 模型大小提示 |
| 跨平台兼容性 | Windows/Linux 差异 | 路径统一处理 + CI 测试 |

---

## 十一、后续扩展

- [ ] 支持更多 TTS 引擎 (F5-TTS, Spark-TTS, MegaTTS)
- [ ] Docker 容器化部署
- [ ] 多用户支持 + 权限管理
- [ ] API Key 认证
- [ ] 模型微调界面
- [ ] 实时流式合成
- [ ] 语音转换 (Voice Conversion) 功能
- [ ] 插件系统
