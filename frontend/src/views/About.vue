<template>
  <div ref="scene" class="scene" @mousemove="onMouseMove" @mouseleave="onMouseLeave">
    <div class="perspective-layer">
      <div
        v-for="card in sortedCards"
        :key="card.id"
        class="bubble-anchor"
        :style="anchorStyle(card)"
      >
        <div
          class="bubble-card"
          :class="{ 'is-decorative': card.type === 'decorative' }"
          :style="cardStyle(card)"
          @click="onCardClick(card)"
          @mouseenter="hoveredId = card.id"
          @mouseleave="hoveredId = null"
        >
          <div class="ground-shadow" :style="groundStyle(card)"></div>
          <svg class="bubble-tail" width="30" height="15" viewBox="0 0 30 15">
            <polygon points="5,0 30,0 0,15" :fill="activeId === card.id ? '#fbfbfd' : (card.bg || '#444')" />
          </svg>

          <div class="bubble-face" :class="{ 'is-hidden': activeId === card.id && card.content }">
            <div v-if="card.icon" class="bubble-icon" v-html="card.icon"></div>
            <span v-if="card.titleTop" class="bubble-title-top">{{ card.titleTop }}</span>
            <span v-if="card.titleBottom" class="bubble-title-bottom">{{ card.titleBottom }}</span>
          </div>

          <div v-if="activeId === card.id && card.content" class="bubble-expanded">
            <button class="bubble-close" @click.stop="activeId = null">CLOSE</button>
            <h2 class="bubble-expanded-title">{{ card.titleTop }}</h2>
            <div class="bubble-divider"></div>
            <div class="bubble-content" v-html="card.content"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue";

const scene = ref(null);
const activeId = ref(null);
const hoveredId = ref(null);
const mouse = ref({ x: 0, y: 0 });

function onMouseMove(e) {
  const rect = scene.value?.getBoundingClientRect();
  if (!rect) return;
  mouse.value = {
    x: (e.clientX - rect.left) / rect.width - 0.5,
    y: (e.clientY - rect.top) / rect.height - 0.5,
  };
}
function onMouseLeave() {
  mouse.value = { x: 0, y: 0 };
}

function onCardClick(card) {
  if (card.type === "decorative") return;
  activeId.value = activeId.value === card.id ? null : card.id;
}

const sortedCards = computed(() => {
  const deco = cards.filter(c => c.type === "decorative");
  const content = cards.filter(c => c.type !== "decorative");
  return [...deco, ...content];
});

function anchorStyle(card) {
  const isActive = activeId.value === card.id;
  return {
    position: isActive ? "fixed" : "absolute",
    top: isActive ? "50%" : card.pos.top,
    left: isActive ? "50%" : card.pos.left,
    zIndex: isActive ? 1000 : card.zOrder,
    transform: isActive ? "translateZ(100px)" : "none",
  };
}

function cardStyle(card) {
  const isActive = activeId.value === card.id;
  const isHovered = hoveredId.value === card.id && !isActive;
  const isBg = card.type === "decorative";
  const p = card.pos;
  const mx = mouse.value.x;
  const my = mouse.value.y;
  const depthFactor = (p.z + 200) / 400;

  if (isActive) {
    return {
      width: card.activeW || "min(85vw, 520px)",
      height: card.activeH || "min(480px, calc(100vh - 160px))",
      background: "#fbfbfd",
      border: "1px solid rgba(255,255,255,0.6)",
      boxShadow: "0 15px 30px -5px rgba(0,0,0,0.1), 0 7px 15px -5px rgba(0,0,0,0.05), 0 1px 0px rgba(255,255,255,0.6) inset",
      transform: "translate(-50%, -50%)",
      opacity: 1,
      filter: "none",
    };
  }

  const tx = mx * 25 * depthFactor;
  const ty = my * 15 * depthFactor;
  const blur = isBg && !isHovered ? 1.5 : 0;
  const opacity = isBg ? (isHovered ? 0.8 : 0.55) : (isHovered ? 1 : 0.95);
  const hoverScale = isHovered ? 1.025 : 1;
  const scale = (p.scale || 1) * hoverScale;
  const hoverRotateY = isHovered ? p.rotateY * 0.3 : p.rotateY;

  return {
    width: card.w,
    height: card.h,
    background: card.bg || "#444",
    border: isHovered ? "1px solid rgba(255,255,255,0.3)" : "1px solid rgba(255,255,255,0.1)",
    boxShadow: isBg
      ? (isHovered ? "0 25px 50px -5px rgba(0,0,0,0.25)" : "0 5px 15px rgba(0,0,0,0.3)")
      : (isHovered ? "0 20px 36px -8px rgba(0,0,0,0.14), 0 1px 0 rgba(255,255,255,0.2) inset" : "0 15px 35px -5px rgba(0,0,0,0.1)"),
    transform: `translate3d(calc(-50% + ${tx}px), calc(-50% + ${ty}px), ${p.z}px) rotateY(${hoverRotateY}deg) scale(${scale})`,
    opacity,
    filter: blur > 0 ? `blur(${blur}px)` : "none",
    cursor: card.type === "decorative" ? "default" : "pointer",
  };
}

function groundStyle(card) {
  const isActive = activeId.value === card.id;
  const isHovered = hoveredId.value === card.id && !isActive;
  const isBg = card.type === "decorative";
  if (isActive) return { opacity: 0.5, transform: "scale(1)" };
  if (isBg) return { opacity: isHovered ? 0.15 : 0.1, transform: `scale(${isHovered ? 0.6 : 0.5})` };
  return { opacity: isHovered ? 0.25 : 0.2, transform: `scale(${isHovered ? 0.85 : 0.8})` };
}

const cards = [
  {
    id: "hero", type: "hero", titleTop: "Uni-TTS", titleBottom: "WORKSTATION", bg: "#333",
    w: "215px", h: "115px",
    activeW: "min(85vw, 520px)", activeH: "min(420px, calc(100vh - 160px))",
    pos: { top: "50%", left: "50%", z: 0, rotateY: 0, scale: 1 },
    zOrder: 300,
    icon: `<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>`,
    content: `<p>Uni-TTS 是一个集成 8 大主流开源 TTS 引擎的一站式 Web 工作站。无需逐个配置复杂的命令行环境，只需在网页上点击几下，即可完成引擎安装、模型下载、语音合成的全流程操作。</p><p>无论你是开发者、内容创作者，还是语音技术爱好者，都能在这里快速上手各种 TTS 模型。</p>`,
  },
  {
    id: "engines", type: "content", titleTop: "收录引擎", titleBottom: "ENGINES", bg: "#D2D1D6",
    w: "260px", h: "130px",
    activeW: "min(90vw, 600px)", activeH: "min(520px, calc(100vh - 160px))",
    pos: { top: "51%", left: "15%", z: 50, rotateY: 20, scale: 0.95 },
    zOrder: 310,
    icon: `<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="1.5"><rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/></svg>`,
    content: `<ul><li><b>GPT-SoVITS</b> — 1 分钟语音数据训练高质量 TTS</li><li><b>CosyVoice</b> — 阿里多语言大语音生成模型</li><li><b>Qwen3-TTS</b> — 通义千问 3 秒语音克隆</li><li><b>IndexTTS-2</b> — 情感丰富、时长可控的零样本 TTS</li><li><b>LuxTTS</b> — 1GB 显存，150 倍实时速度</li><li><b>VoxCPM 2</b> — 清华无分词器 TTS，30 种语言</li><li><b>MOSS-TTS</b> — 复旦高保真长文本 TTS</li><li><b>Fish Audio S2 Pro</b> — 15000+ 情感标签</li></ul>`,
  },
  {
    id: "features", type: "content", titleTop: "核心功能", titleBottom: "FEATURES", bg: "#D2D1D6",
    w: "280px", h: "150px",
    activeW: "min(90vw, 520px)", activeH: "min(440px, calc(100vh - 160px))",
    pos: { top: "62%", left: "76%", z: 50, rotateY: -15, scale: 0.9 },
    zOrder: 310,
    icon: `<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="1.5"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`,
    content: `<ul><li>自动化环境管理 — 克隆仓库、创建 venv、安装依赖</li><li>模型一键下载 — ModelScope 下载器，自动归档</li><li>统一推理界面 — Web UI，参考音频上传、参数调节</li><li>双模式推理 — 自研页面 + 原版 Gradio Demo</li><li>GPU / CPU 自适应 — 自动检测硬件</li></ul>`,
  },
  {
    id: "contact", type: "content", titleTop: "联系方式", titleBottom: "CONTACT", bg: "#D2D1D6",
    w: "155px", h: "90px",
    activeW: "min(90vw, 420px)", activeH: "min(280px, calc(100vh - 200px))",
    pos: { top: "39%", left: "67%", z: 0, rotateY: -20, scale: 1 },
    zOrder: 305,
    icon: `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="1.5"><path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>`,
    content: `<ul><li><b>Bilibili</b>：<a href="https://space.bilibili.com/1741551557" target="_blank">骄傲的狼W0R</a></li><li><b>QQ</b>：2627641908</li><li><b>GitHub</b>：<a href="https://github.com/monologue82" target="_blank">github.com/monologue82</a></li></ul>`,
  },
  {
    id: "tech", type: "content", titleTop: "技术栈", titleBottom: "TECH STACK", bg: "#D2D1D6",
    w: "165px", h: "95px",
    activeW: "min(88vw, 440px)", activeH: "min(300px, calc(100vh - 200px))",
    pos: { top: "40%", left: "32%", z: 0, rotateY: 15, scale: 1 },
    zOrder: 305,
    icon: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="1.5"><path d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>`,
    content: `<ul><li>后端：Python + FastAPI + SQLite</li><li>前端：Vue 3 + Vite + Tailwind CSS</li><li>推理：PyTorch + 各引擎官方依赖</li><li>模型源：ModelScope / Hugging Face</li></ul>`,
  },
  {
    id: "links", type: "content", titleTop: "友情链接", titleBottom: "PROJECTS", bg: "#D2D1D6",
    w: "155px", h: "90px",
    activeW: "min(90vw, 500px)", activeH: "min(420px, calc(100vh - 160px))",
    pos: { top: "75%", left: "15%", z: 0, rotateY: 20, scale: 1 },
    zOrder: 305,
    icon: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="1.5"><path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>`,
    content: `<ul>
      <li><b>Uni-API</b> — 统一 AI API 网关，代理管理 60+ AI 服务商<a href="https://github.com/monologue82/Uni-API" target="_blank"> → GitHub</a></li>
      <li><b>Vox-Engine-Framework</b> — 同声传译系统，支持流式传输和低延迟实时识别翻译<a href="https://github.com/monologue82/Vox-Engine-Framework" target="_blank"> → GitHub</a></li>
      <li><b>AuraMotion</b> — 高精度 MMD 动作捕捉，AI 姿态估计 + 手部面部追踪<a href="https://github.com/monologue82/AuraMotion" target="_blank"> → GitHub</a></li>
      <li><b>MiKaScore</b> — 实时舞蹈评分工具，MediaPipe 姿态捕捉 + VMD 对比<a href="https://github.com/monologue82/MiKaScore" target="_blank"> → GitHub</a></li>
      <li><b>Smart Classroom</b> — 现代化智能教室管理系统<a href="https://github.com/monologue82/smart-classroom" target="_blank"> → GitHub</a></li>
      <li><b>voice-assistant</b> — Android 语音输入助手（悬浮窗 + LLM 精炼）<a href="https://github.com/monologue82/voice-assistant" target="_blank"> → GitHub</a></li>
    </ul>`,
  },
  {
    id: "deco-1", type: "decorative", bg: "#D2D1D6", w: "180px", h: "100px",
    pos: { top: "40%", left: "48%", z: -10, rotateY: 2, scale: 1 },
    zOrder: 200,
  },
  {
    id: "deco-2", type: "decorative", bg: "#D2D1D6", w: "180px", h: "110px",
    pos: { top: "38%", left: "39%", z: -15, rotateY: 7, scale: 1 },
    zOrder: 210,
  },
  {
    id: "deco-3", type: "decorative", bg: "#D2D1D6", w: "290px", h: "135px",
    pos: { top: "44%", left: "88%", z: 20, rotateY: -30, scale: 0.755 },
    zOrder: 190,
  },
  {
    id: "deco-4", type: "decorative", bg: "#47474C", w: "175px", h: "85px",
    pos: { top: "44%", left: "79%", z: -45, rotateY: -20, scale: 1 },
    zOrder: 180,
  },
];
</script>

<style scoped>
.scene {
  position: relative;
  width: 100%;
  height: calc(100vh - 120px);
  min-height: 500px;
  overflow: hidden;
  perspective: 1200px;
}

.perspective-layer {
  position: absolute;
  inset: 0;
  transform-style: preserve-3d;
}

.bubble-anchor {
  transform-style: preserve-3d;
  pointer-events: none;
}

.bubble-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  user-select: none;
  pointer-events: auto;
  transform-style: preserve-3d;
  transition:
    transform 0.6s cubic-bezier(0.2, 0.8, 0.2, 1),
    opacity 160ms cubic-bezier(0.23, 1, 0.32, 1),
    filter 160ms cubic-bezier(0.23, 1, 0.32, 1),
    box-shadow 160ms cubic-bezier(0.23, 1, 0.32, 1),
    border-color 160ms cubic-bezier(0.23, 1, 0.32, 1),
    width 0.5s cubic-bezier(0.3, 1, 0.3, 1),
    height 0.5s cubic-bezier(0.3, 1, 0.3, 1),
    background-color 160ms cubic-bezier(0.23, 1, 0.32, 1);
}

.ground-shadow {
  position: absolute;
  bottom: -30px;
  left: 15%;
  width: 70%;
  height: 15px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.5);
  filter: blur(15px);
  z-index: -1;
  pointer-events: none;
  transition: opacity 500ms ease, transform 500ms ease;
}

.bubble-tail {
  position: absolute;
  bottom: -13px;
  left: 40px;
  pointer-events: none;
  transition: fill 400ms ease;
}

.is-decorative {
  pointer-events: none !important;
}

.bubble-face {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: white;
  transition: opacity 400ms ease-out, transform 400ms ease-out;
}
.bubble-face.is-hidden {
  opacity: 0;
  transform: scale(0.9);
  pointer-events: none;
}
.is-decorative .bubble-face {
  opacity: 0;
}
.hero .bubble-face { color: white; }

.bubble-icon {
  opacity: 0.85;
  transition: opacity 200ms ease, transform 200ms ease;
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.2));
}
.bubble-card:not(.is-decorative):hover .bubble-icon {
  opacity: 1;
  transform: scale(1.08);
}

.bubble-title-top {
  font-family: "DM Sans", system-ui, sans-serif;
  font-size: 11px;
  letter-spacing: 0.12em;
  font-weight: 500;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}
.bubble-title-bottom {
  font-family: "DM Sans", system-ui, sans-serif;
  font-size: 9px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  opacity: 0.6;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.bubble-expanded {
  position: absolute;
  inset: 0;
  padding: 24px 28px;
  display: flex;
  flex-direction: column;
  animation: fadeIn 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards;
  overflow: hidden;
  border-radius: 16px;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.bubble-close {
  position: absolute;
  top: 16px;
  right: 20px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.15em;
  color: #999;
  cursor: pointer;
  background: none;
  border: none;
  transition: color 150ms;
  z-index: 10;
}
.bubble-close:hover { color: #333; }

.bubble-expanded-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 12px;
}
.bubble-divider {
  width: 100%;
  height: 1px;
  background: #e2e2e2;
  margin-bottom: 16px;
}
.bubble-content {
  overflow-y: auto;
  flex: 1;
  color: #334155;
  font-size: 0.875rem;
  line-height: 1.75;
}
.bubble-content :deep(ul) { margin: 0; padding-left: 1.1rem; }
.bubble-content :deep(li) { margin-bottom: 0.4rem; }
.bubble-content :deep(p) { margin-bottom: 0.75rem; }
.bubble-content :deep(b) { color: #0f172a; }
.bubble-content :deep(a) { color: #2563eb; text-decoration: underline; text-underline-offset: 2px; }
.bubble-content :deep(a:hover) { opacity: 0.7; }
</style>
