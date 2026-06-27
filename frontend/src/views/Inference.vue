<template>
  <div>
    <div class="flex items-center gap-3 mb-10">
      <button @click="$router.back()" class="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-150" style="border: 1px solid var(--border-hairline); color: var(--steel)">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
      </button>
      <div>
        <h1 class="text-heading-md" style="color: var(--ink)">{{ engineInfo?.display_name || engine }}</h1>
        <p class="text-body-sm mt-1" style="color: var(--steel)">{{ engineInfo?.description }}</p>
      </div>
      <div class="ml-auto flex items-center gap-2">
        <span class="badge text-micro" :class="engineReady ? 'badge-loaded' : 'badge-not-installed'">{{ engineReady ? '模型已加载' : '未加载' }}</span>
        <button @click="stopEngine" class="px-3 py-1.5 rounded-full text-micro font-semibold transition-all duration-150 flex items-center gap-1.5"
          style="border: 1px solid var(--error-border); color: var(--error-text); background: var(--error-bg)">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/></svg>
          停止并卸载
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="lg:col-span-2 space-y-5">
        <!-- VoxCPM: Control Instruction -->
        <div v-if="isVoxCPM" class="glass rounded-xl p-6">
          <label class="text-body-sm font-medium block mb-3" style="color: var(--ink)">
            Control Instruction <span style="color: var(--muted)" class="font-normal">(可选 — 支持中英文描述)</span>
          </label>
          <input v-model="controlInstruction" type="text" class="w-full rounded-md px-4 py-2.5 text-body-md transition-colors"
            style="background: var(--bg-input); color: var(--ink); border: 1px solid var(--border-hairline)"
            :placeholder="ultimateCloning ? '极致克隆模式下 Control Instruction 已禁用' : '如：年轻女性，温柔甜美 / A warm young woman / 暴躁老哥，语速飞快'"
            :disabled="ultimateCloning" />
          <p v-if="!ultimateCloning" class="text-micro mt-2" style="color: var(--muted)">
            描述目标音色特征（性别、年龄、语气、情绪、语速等），无需参考音频即可创造声音
          </p>
        </div>

        <!-- Reference Audio -->
        <div class="glass rounded-xl p-6">
          <label class="text-body-sm font-medium block mb-3" style="color: var(--ink)">
            {{ isVoxCPM ? '参考音频 (可选 — 上传后用于克隆)' : '参考音频 (音色克隆)' }}
          </label>
          <div class="rounded-xl p-8 text-center cursor-pointer transition-colors" style="border: 2px dashed var(--border-hairline)" @click="$refs.audioInput.click()" @dragover.prevent @drop.prevent="handleDrop">
            <input ref="audioInput" type="file" accept="audio/*" class="hidden" @change="handleFileSelect" />
            <div v-if="!refAudio">
              <svg class="w-10 h-10 mx-auto mb-3" style="color: var(--stone)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 3a4 4 0 014 4v4a4 4 0 01-8 0V7a4 4 0 014-4z"/></svg>
              <p class="text-body-sm" style="color: var(--steel)">拖拽或点击上传参考音频</p>
              <p class="text-micro mt-1" style="color: var(--muted)">支持 WAV, MP3, FLAC 等格式</p>
            </div>
            <div v-else class="flex items-center gap-3 justify-center">
              <svg class="w-7 h-7" style="color: var(--badge-ready-text)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
              <div class="text-left">
                <p class="text-body-sm" style="color: var(--ink)">{{ refAudioName }}</p>
                <p class="text-micro" style="color: var(--muted)">点击更换</p>
              </div>
            </div>
          </div>

          <!-- Microphone recording -->
          <div class="mt-3 flex gap-2">
            <button @click="toggleRecording" class="flex-1 py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150 flex items-center justify-center gap-2"
              :style="isRecording
                ? 'background: var(--error-bg); color: var(--error-text); border: 1px solid var(--error-border)'
                : 'background: var(--btn-tertiary-bg); color: var(--steel); border: 1px solid var(--border-hairline)'">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 3a4 4 0 014 4v4a4 4 0 01-8 0V7a4 4 0 014-4z"/></svg>
              {{ isRecording ? '停止录音' : '麦克风录音' }}
            </button>
            <button v-if="refAudio" @click="clearAudio" class="px-4 py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150"
              style="border: 1px solid var(--error-border); color: var(--error-text); background: var(--error-bg)">清除</button>
          </div>

          <div v-if="refAudioUrl" class="mt-3"><audio :src="refAudioUrl" controls class="w-full h-10"></audio></div>

          <!-- ASR reminder -->
          <div v-if="asrReminder" class="mt-3 rounded-lg p-3 flex items-start gap-2" style="background: var(--badge-loaded-bg); border: 1px solid var(--badge-loaded-text)">
            <svg class="w-4 h-4 mt-0.5 flex-shrink-0" style="color: var(--badge-loaded-text)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            <div>
              <p class="text-micro" style="color: var(--badge-loaded-text)">{{ asrReminder }}</p>
              <router-link to="/models" class="text-micro hover:underline mt-1 inline-block font-medium" style="color: var(--badge-loaded-text)">前往下载 ASR 模型</router-link>
            </div>
          </div>
        </div>

        <!-- VoxCPM: Ultimate Cloning Mode -->
        <div v-if="isVoxCPM" class="glass rounded-xl p-6">
          <label class="flex items-center gap-3 cursor-pointer">
            <div class="relative">
              <input type="checkbox" v-model="ultimateCloning" class="sr-only" @change="onUltimateCloningToggle" />
              <div class="w-11 h-6 rounded-full transition-colors duration-200" :style="{ background: ultimateCloning ? 'var(--btn-primary-bg)' : 'var(--border-hairline)' }"></div>
              <div class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200" :style="{ transform: ultimateCloning ? 'translateX(20px)' : 'translateX(0)' }"></div>
            </div>
            <div>
              <span class="text-body-sm font-medium" style="color: var(--ink)">极致克隆模式 (基于文本引导的极致克隆)</span>
              <p class="text-micro mt-0.5" style="color: var(--muted)">自动识别参考音频文本，完整还原音色、节奏、情感等全部声音细节。开启后 Control Instruction 将暂时禁用</p>
            </div>
          </label>

          <div v-if="ultimateCloning" class="mt-4">
            <label class="text-body-sm font-medium block mb-2" style="color: var(--ink)">参考音频内容文本 (ASR 自动填充，可手动编辑)</label>
            <textarea v-model="promptText" rows="2" class="w-full rounded-md px-4 py-3 text-body-md resize-none transition-colors"
              style="background: var(--bg-input); color: var(--ink); border: 1px solid var(--border-hairline)"
              :placeholder="asrRunning ? '正在识别参考音频...' : '参考音频的文字内容将自动识别并显示在此处...'"></textarea>
            <p v-if="asrRunning" class="text-micro mt-1 flex items-center gap-1" style="color: var(--btn-primary-bg)">
              <span class="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
              ASR 识别中...
            </p>
          </div>
        </div>

        <!-- Target Text -->
        <div class="glass rounded-xl p-6">
          <label class="text-body-sm font-medium block mb-3" style="color: var-ink">{{ isVoxCPM ? 'Target Text — 要合成的目标文本' : '合成文本' }}</label>
          <textarea v-model="text" rows="5" class="w-full rounded-md px-4 py-3 text-body-md resize-none transition-colors"
            style="background: var(--bg-input); color: var(--ink); border: 1px solid var(--border-hairline)"
            :placeholder="isVoxCPM ? '输入要合成的文本内容...' : '输入要合成的文本内容...'"></textarea>
        </div>

        <!-- Non-VoxCPM: ref text & description -->
        <template v-if="!isVoxCPM">
          <div class="glass rounded-xl p-6">
            <label class="text-body-sm font-medium block mb-3" style="color: var(--ink)">参考音频文本 <span style="color: var(--muted)" class="font-normal">(可选 — ASR 自动填充)</span></label>
            <input v-model="refText" type="text" class="w-full rounded-md px-4 py-2.5 text-body-md transition-colors"
              style="background: var(--bg-input); color: var(--ink); border: 1px solid var(--border-hairline)"
              :placeholder="asrRunning ? '正在识别参考音频...' : '参考音频中说的文字内容'" />
            <p v-if="asrRunning" class="text-micro mt-2 flex items-center gap-1" style="color: var(--btn-primary-bg)">
              <span class="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
              ASR 识别中...
            </p>
          </div>
          <div class="glass rounded-xl p-6">
            <label class="text-body-sm font-medium block mb-3" style="color: var(--ink)">语音描述 <span style="color: var(--muted)" class="font-normal">(可选)</span></label>
            <input v-model="description" type="text" class="w-full rounded-md px-4 py-2.5 text-body-md transition-colors"
              style="background: var(--bg-input); color: var(--ink); border: 1px solid var(--border-hairline)"
              placeholder="A warm female voice, speaking slowly" />
          </div>
        </template>

        <!-- VoxCPM: Advanced Settings -->
        <div v-if="isVoxCPM" class="glass rounded-xl p-6">
          <h3 class="text-body-sm font-medium mb-5 cursor-pointer flex items-center gap-2" style="color: var(--ink)" @click="showAdvanced = !showAdvanced">
            <svg class="w-4 h-4 transition-transform duration-200" :style="{ transform: showAdvanced ? 'rotate(90deg)' : 'rotate(0)' }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/></svg>
            高级设置
          </h3>
          <div v-show="showAdvanced" class="space-y-5">
            <label class="flex items-center gap-3 cursor-pointer">
              <div class="relative">
                <input type="checkbox" v-model="denoise" class="sr-only" />
                <div class="w-11 h-6 rounded-full transition-colors duration-200" :style="{ background: denoise ? 'var(--btn-primary-bg)' : 'var(--border-hairline)' }"></div>
                <div class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200" :style="{ transform: denoise ? 'translateX(20px)' : 'translateX(0)' }"></div>
              </div>
              <div>
                <span class="text-body-sm" style="color: var(--ink)">参考音频降噪增强</span>
                <p class="text-micro mt-0.5" style="color: var(--muted)">克隆前使用 ZipEnhancer 对参考音频进行降噪处理</p>
              </div>
            </label>

            <label class="flex items-center gap-3 cursor-pointer">
              <div class="relative">
                <input type="checkbox" v-model="normalizeText" class="sr-only" />
                <div class="w-11 h-6 rounded-full transition-colors duration-200" :style="{ background: normalizeText ? 'var(--btn-primary-bg)' : 'var(--border-hairline)' }"></div>
                <div class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200" :style="{ transform: normalizeText ? 'translateX(20px)' : 'translateX(0)' }"></div>
              </div>
              <div>
                <span class="text-body-sm" style="color: var(--ink)">文本规范化</span>
                <p class="text-micro mt-0.5" style="color: var(--muted)">自动规范化数字、日期及缩写（基于 wetext）</p>
              </div>
            </label>

            <div>
              <label class="flex items-center justify-between text-micro mb-2" style="color: var(--steel)">
                <span>CFG（引导强度）</span>
                <span class="font-mono">{{ cfgValue.toFixed(1) }}</span>
              </label>
              <input type="range" v-model.number="cfgValue" min="1.0" max="3.0" step="0.1" class="w-full" />
              <p class="text-micro mt-1" style="color: var(--muted)">数值越高 → 越贴合提示/参考音色；数值越低 → 生成风格更自由</p>
            </div>

            <div>
              <label class="flex items-center justify-between text-micro mb-2" style="color: var(--steel)">
                <span>LocDiT 流匹配迭代步数</span>
                <span class="font-mono">{{ ditSteps }}</span>
              </label>
              <input type="range" v-model.number="ditSteps" min="1" max="50" step="1" class="w-full" />
              <p class="text-micro mt-1" style="color: var(--muted)">步数越多 → 可能生成更好的音频质量，但速度变慢</p>
            </div>
          </div>
        </div>

        <!-- Generate Button -->
        <button @click="synthesize" :disabled="!text || generating" class="btn-primary w-full py-3.5 text-base flex items-center justify-center gap-2">
          <div v-if="generating" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/></svg>
          {{ generating ? "合成中..." : "开始合成" }}
        </button>

        <!-- Result -->
        <transition name="fade">
          <div v-if="audioSrc" class="glass rounded-xl p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-body-sm font-medium" style="color: var(--ink)">合成结果</h3>
              <a :href="audioSrc" download class="text-body-sm hover:underline flex items-center gap-1" style="color: var(--btn-primary-bg)">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
                下载
              </a>
            </div>
            <audio :src="audioSrc" controls class="w-full"></audio>
          </div>
        </transition>

        <div v-if="error" class="rounded-xl p-4" style="background: var(--error-bg); border: 1px solid var(--error-border)">
          <p class="text-body-sm" style="color: var(--error-text)">{{ error }}</p>
        </div>
      </div>

      <!-- Right sidebar -->
      <div class="space-y-5">
        <!-- Non-VoxCPM: Parameter settings -->
        <div v-if="!isVoxCPM" class="glass rounded-xl p-6">
          <h3 class="text-body-sm font-medium mb-5" style="color: var(--ink)">参数设置</h3>
          <div class="space-y-5">
            <div>
              <label class="flex items-center justify-between text-micro mb-2" style="color: var(--steel)">
                <span>语速</span><span class="font-mono">{{ speed.toFixed(1) }}x</span>
              </label>
              <input type="range" v-model.number="speed" min="0.5" max="2.0" step="0.1" class="w-full" />
            </div>
            <div>
              <label class="flex items-center justify-between text-micro mb-2" style="color: var(--steel)">
                <span>音调</span><span class="font-mono">{{ pitch > 0 ? '+' : '' }}{{ pitch }}</span>
              </label>
              <input type="range" v-model.number="pitch" min="-12" max="12" step="1" class="w-full" />
            </div>
            <div>
              <label class="text-micro block mb-2" style="color: var(--steel)">语言</label>
              <select v-model="language" class="w-full rounded-md px-3 py-2 text-body-sm transition-colors" style="background: var(--bg-input); color: var(--ink); border: 1px solid var(--border-hairline)">
                <option value="zh">中文</option>
                <option value="en">English</option>
                <option value="ja">日本語</option>
                <option value="ko">한국어</option>
              </select>
            </div>
            <div>
              <label class="text-micro block mb-2" style="color: var(--steel)">情感</label>
              <div class="flex flex-wrap gap-2">
                <button v-for="e in emotions" :key="e.value" @click="emotion = e.value" class="px-3.5 py-1.5 rounded-full text-micro font-medium transition-all duration-150"
                  :style="emotion === e.value
                    ? 'background: var(--btn-primary-bg); color: var(--btn-primary-text)'
                    : 'background: var(--btn-tertiary-bg); color: var(--steel); border: 1px solid var(--border-hairline)'">
                  {{ e.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Engine info -->
        <div class="glass rounded-xl p-6">
          <h3 class="text-body-sm font-medium mb-4" style="color: var(--ink)">引擎信息</h3>
          <div class="space-y-2.5 text-micro">
            <div class="flex justify-between"><span style="color: var(--steel)">端口</span><span class="font-mono" style="color: var(--ink)">:{{ engineInfo?.port }}</span></div>
            <div class="flex justify-between"><span style="color: var(--steel)">最低显存</span><span style="color: var(--ink)">{{ engineInfo?.min_vram_gb }}GB</span></div>
            <div class="flex justify-between"><span style="color: var(--steel)">入口脚本</span><span class="font-mono" style="color: var(--ink)">{{ engineInfo?.entry_script }}</span></div>
          </div>
        </div>

        <!-- Batch inference -->
        <div class="glass rounded-xl p-6">
          <h3 class="text-body-sm font-medium mb-3" style="color: var(--ink)">批量推理</h3>
          <p class="text-micro mb-3" style="color: var(--muted)">每行一条文本</p>
          <textarea v-model="batchTexts" rows="4" class="w-full rounded-md px-3 py-2 text-body-sm resize-none mb-3" style="background: var(--bg-input); color: var(--ink); border: 1px solid var(--border-hairline)" placeholder="第一行文本&#10;第二行文本"></textarea>
          <button @click="batchSynthesize" :disabled="!batchTexts || batchRunning" class="btn-tertiary w-full py-2.5 text-sm flex items-center justify-center gap-2">
            {{ batchRunning ? `合成中 (${batchDone}/${batchTotal})` : "开始批量合成" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import axios from "axios";

const route = useRoute();
const engine = route.params.engine;
const engineInfo = ref(null);
const engineReady = ref(false);
const isVoxCPM = computed(() => engine === "voxcpm");

const text = ref("");
const refAudio = ref(null);
const refAudioName = ref("");
const refAudioUrl = ref("");
const refText = ref("");
const description = ref("");
const language = ref("zh");
const speed = ref(1.0);
const pitch = ref(0);
const emotion = ref("neutral");
const generating = ref(false);
const audioSrc = ref("");
const error = ref("");
const batchTexts = ref("");
const batchRunning = ref(false);
const batchDone = ref(0);
const batchTotal = ref(0);

// VoxCPM-specific
const controlInstruction = ref("");
const ultimateCloning = ref(false);
const promptText = ref("");
const cfgValue = ref(2.0);
const ditSteps = ref(10);
const normalizeText = ref(false);
const denoise = ref(false);
const showAdvanced = ref(false);
const asrAvailable = ref(false);
const asrReminder = ref("");

// Microphone
const isRecording = ref(false);
const asrRunning = ref(false);
let mediaRecorder = null;
let audioChunks = [];

const emotions = [
  { value: "neutral", label: "中性" },
  { value: "happy", label: "开心" },
  { value: "sad", label: "悲伤" },
  { value: "angry", label: "愤怒" },
  { value: "gentle", label: "温柔" },
  { value: "excited", label: "兴奋" },
];

function handleFileSelect(e) { const f = e.target.files[0]; if (f) setAudioFile(f); }
function handleDrop(e) { const f = e.dataTransfer.files[0]; if (f) setAudioFile(f); }
function setAudioFile(file) {
  refAudio.value = file;
  refAudioName.value = file.name;
  refAudioUrl.value = URL.createObjectURL(file);
  if (asrAvailable.value) {
    runASR();
  } else {
    asrReminder.value = "ASR 模型未下载，无法自动识别参考音频文本。请前往资源管理页面下载 SenseVoiceSmall ASR 模型。";
  }
}
function clearAudio() {
  refAudio.value = null;
  refAudioName.value = "";
  if (refAudioUrl.value) URL.revokeObjectURL(refAudioUrl.value);
  refAudioUrl.value = "";
  promptText.value = "";
}

async function toggleRecording() {
  if (isRecording.value) {
    stopRecording();
  } else {
    startRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = () => {
      const blob = new Blob(audioChunks, { type: "audio/wav" });
      const file = new File([blob], `recording_${Date.now()}.wav`, { type: "audio/wav" });
      setAudioFile(file);
      stream.getTracks().forEach(t => t.stop());
    };
    mediaRecorder.start();
    isRecording.value = true;
  } catch (e) {
    error.value = "麦克风访问失败: " + e.message;
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  isRecording.value = false;
}

async function onUltimateCloningToggle() {
  if (ultimateCloning.value && refAudio.value) {
    if (asrAvailable.value) {
      await runASR();
    } else {
      asrReminder.value = "ASR 模型未下载，无法自动识别参考音频文本。请前往资源管理页面下载 SenseVoiceSmall ASR 模型。";
    }
  }
}

async function stopEngine() {
  try {
    await axios.post(`/api/engines/${engine}/unload-model`);
    await axios.post(`/api/engines/${engine}/stop-gradio`);
    engineReady.value = false;
  } catch (e) {
    console.error("Failed to stop engine:", e);
  }
}

async function runASR() {
  if (!refAudio.value) return;
  asrRunning.value = true;
  asrReminder.value = "";
  try {
    const fd = new FormData();
    fd.append("audio", refAudio.value);
    const { data } = await axios.post(`/api/tts/asr`, fd);
    if (data.text) {
      if (isVoxCPM.value) {
        promptText.value = data.text;
      } else {
        refText.value = data.text;
      }
    } else if (data.error) {
      asrReminder.value = "ASR 识别失败: " + data.error;
    }
  } catch (e) {
    console.error("ASR failed:", e);
    asrReminder.value = "ASR 识别失败，请检查 ASR 模型是否已下载。";
  } finally {
    asrRunning.value = false;
  }
}

async function synthesize() {
  generating.value = true; error.value = ""; audioSrc.value = "";
  try {
    const fd = new FormData();
    fd.append("engine_name", engine);
    fd.append("text", text.value);
    fd.append("language", language.value);
    fd.append("speed", speed.value);
    fd.append("pitch", pitch.value);
    fd.append("emotion", emotion.value);

    if (isVoxCPM.value) {
      fd.append("control_instruction", ultimateCloning.value ? "" : controlInstruction.value);
      fd.append("prompt_text", ultimateCloning.value ? promptText.value : "");
      fd.append("cfg_value", cfgValue.value);
      fd.append("dit_steps", ditSteps.value);
      fd.append("normalize", normalizeText.value);
      fd.append("denoise", denoise.value);
    } else {
      fd.append("ref_text", refText.value);
      fd.append("description", description.value);
    }

    if (refAudio.value) fd.append("ref_audio", refAudio.value);
    const resp = await axios.post("/api/tts/synthesize", fd, { responseType: "blob" });
    audioSrc.value = URL.createObjectURL(resp.data);
  } catch (e) {
    if (e.response?.data) { try { const t = await e.response.data.text(); const j = JSON.parse(t); error.value = j.error || "Synthesis failed"; } catch { error.value = "Synthesis failed"; } }
    else error.value = e.message;
  } finally { generating.value = false; }
}

async function batchSynthesize() {
  const lines = batchTexts.value.split("\n").filter(l => l.trim());
  if (!lines.length) return;
  batchRunning.value = true; batchDone.value = 0; batchTotal.value = lines.length;
  try {
    const fd = new FormData();
    fd.append("engine_name", engine);
    fd.append("texts", lines.join("\n"));
    fd.append("language", language.value);
    fd.append("speed", speed.value);
    fd.append("pitch", pitch.value);
    fd.append("emotion", emotion.value);
    if (refAudio.value) fd.append("ref_audio", refAudio.value);
    await axios.post("/api/batch/create", fd);
    batchDone.value = lines.length;
  } catch (e) { error.value = e.message; }
  finally { batchRunning.value = false; }
}

onMounted(async () => {
  try {
    const { data } = await axios.get(`/api/engines/${engine}`);
    engineInfo.value = data;
    engineReady.value = data.model_loaded || false;
  } catch (e) { console.error(e); }
  try {
    const { data } = await axios.get(`/api/tts/asr-status`);
    asrAvailable.value = (data.engine_installed && data.downloaded) || false;
    if (!data.engine_installed) {
      asrReminder.value = "ASR 引擎未安装，请先在资源管理页面安装 ASR 引擎。";
    } else if (!data.downloaded) {
      asrReminder.value = "ASR 模型未下载，请先下载模型。";
    }
  } catch {}
});

onUnmounted(() => {
  if (refAudioUrl.value) URL.revokeObjectURL(refAudioUrl.value);
});
</script>
