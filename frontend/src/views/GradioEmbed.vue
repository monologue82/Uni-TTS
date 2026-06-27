<template>
  <div>
    <div class="flex items-center gap-3 mb-8">
      <button @click="$router.back()" class="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-150" style="border: 1px solid var(--border-hairline); color: var(--steel)">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/></svg>
      </button>
      <div>
        <h1 class="text-heading-md" style="color: var(--ink)">{{ engineInfo?.display_name || engine }}</h1>
        <p class="text-body-sm" style="color: var(--steel)">Gradio 原版演示界面</p>
      </div>
      <div class="ml-auto flex items-center gap-2">
        <span class="badge" :class="gradioRunning ? 'badge-ready' : 'badge-not-installed'">{{ gradioRunning ? "运行中" : "未启动" }}</span>
        <button v-if="gradioRunning" @click="stopGradio" class="px-3 py-1.5 rounded-full text-micro font-semibold transition-all duration-150 flex items-center gap-1.5"
          style="border: 1px solid var(--error-border); color: var(--error-text); background: var(--error-bg)">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/></svg>
          停止
        </button>
      </div>
    </div>

    <div v-if="starting" class="glass rounded-hero p-16 text-center">
      <div class="w-12 h-12 border-3 rounded-full animate-spin mx-auto mb-5" style="border-color: var(--border-hairline); border-top-color: var(--ink); border-width: 3px"></div>
      <h3 class="text-heading-sm mb-2" style="color: var(--ink)">正在启动 Gradio</h3>
      <p class="text-body-md mb-4" style="color: var(--steel)">{{ engineInfo?.display_name }} 正在加载模型并启动服务...</p>
      <div class="max-w-xs mx-auto">
        <div class="flex items-center justify-between text-micro mb-1.5" style="color: var(--steel)">
          <span>{{ statusMsg }}</span>
        </div>
        <div class="w-full rounded-full h-2 overflow-hidden" style="background: var(--border-hairline)">
          <div class="h-2 rounded-full transition-all duration-500 ease-out animate-pulse" style="background: var(--btn-primary-bg); width: 100%"></div>
        </div>
      </div>
      <button @click="cancelStart" class="mt-6 px-6 py-2 text-sm rounded-full transition-colors" style="border: 1px solid var(--border-hairline); color: var(--steel)">取消</button>
    </div>

    <div v-else-if="!gradioRunning" class="glass rounded-hero p-16 text-center">
      <svg class="w-16 h-16 mx-auto mb-5" style="color: var(--stone)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
      <h3 class="text-heading-sm mb-2" style="color: var(--ink)">启动 Gradio 演示</h3>
      <p class="text-body-md mb-8" style="color: var(--steel)">将启动 {{ engineInfo?.display_name }} 的官方 Gradio Demo 界面</p>

      <div class="max-w-xs mx-auto mb-6">
        <label class="text-micro block mb-2" style="color: var(--steel)">推理设备</label>
        <div class="flex gap-2">
          <button v-for="d in devices" :key="d.value" @click="device = d.value"
            :disabled="d.value === 'cuda' && gpuInfo && !gpuInfo.gpu_available"
            class="flex-1 px-3 py-2 rounded-lg text-body-sm font-medium transition-all duration-150 text-center"
            :style="device === d.value
              ? 'background: var(--btn-primary-bg); color: var(--btn-primary-text)'
              : d.value === 'cuda' && gpuInfo && !gpuInfo.gpu_available
                ? 'background: var(--btn-tertiary-bg); color: var(--muted); opacity: 0.5; cursor: not-allowed'
                : 'background: var(--btn-tertiary-bg); color: var(--steel); border: 1px solid var(--border-hairline)'">
            {{ d.label }}
          </button>
        </div>
        <div class="mt-2 flex items-center gap-2">
          <span v-if="gpuInfo?.gpu_available" class="inline-flex items-center gap-1 text-micro" style="color: var(--badge-ready-text)">
            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
            GPU 可用: {{ gpuInfo.gpu_name }} ({{ (gpuInfo.gpu_memory_mb / 1024).toFixed(0) }}GB)
          </span>
          <span v-else-if="gpuInfo" class="inline-flex items-center gap-1 text-micro" style="color: var(--muted)">
            <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/></svg>
            GPU 不可用，仅可使用 CPU 推理
          </span>
        </div>
      </div>

      <button @click="startGradio" :disabled="starting" class="btn-primary px-8 py-3 text-base inline-flex items-center gap-2">
        <div v-if="starting" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
        <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
        {{ starting ? "启动中..." : "启动 Gradio" }}
      </button>
    </div>

    <div v-else class="glass rounded-xl overflow-hidden" style="height: calc(100vh - 200px)">
      <iframe :src="gradioUrl" class="w-full h-full border-0" allow="microphone" @load="iframeLoaded = true"></iframe>
      <div v-if="!iframeLoaded" class="absolute inset-0 flex items-center justify-center" style="background: var(--bg)">
        <div class="text-center">
          <div class="w-10 h-10 border-3 rounded-full animate-spin mx-auto mb-4" style="border-color: var(--border-hairline); border-top-color: var(--ink); border-width: 3px"></div>
          <p class="text-body-sm" style="color: var(--steel)">正在加载 Gradio 界面...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import axios from "axios";

const route = useRoute();
const router = useRouter();
const engine = route.params.engine;
const engineInfo = ref(null);
const gradioRunning = ref(false);
const starting = ref(false);
const gradioUrl = ref("");
const pollTimer = ref(null);
const statusMsg = ref("正在准备...");
const iframeLoaded = ref(false);
const device = ref("auto");
const gpuInfo = ref(null);
let startCancelled = false;

const devices = [
  { value: "auto", label: "自动" },
  { value: "cuda", label: "GPU (CUDA)" },
  { value: "cpu", label: "CPU" },
];

async function startGradio() {
  starting.value = true;
  startCancelled = false;
  statusMsg.value = "正在启动 Gradio 进程...";
  try {
    const { data } = await axios.post(`/api/engines/${engine}/start-gradio`, { device: device.value });
    if (startCancelled) return;

    if (data.url || data.status === "already_running") {
      statusMsg.value = "Gradio 进程已启动，正在加载模型...";

      let ready = false;
      for (let i = 0; i < 60; i++) {
        if (startCancelled) return;
        try {
          const { data: st } = await axios.get(`/api/engines/${engine}/gradio-status`);
          if (st.running) {
            ready = true;
            break;
          }
        } catch {}
        if (i % 3 === 2) {
          statusMsg.value = `正在等待 Gradio 就绪 (${i + 1}s)...`;
        }
        await new Promise(r => setTimeout(r, 2000));
      }

      if (!startCancelled) {
        if (ready) {
          gradioUrl.value = data.url || `http://localhost:${engineInfo.value?.port}`;
          gradioRunning.value = true;
          iframeLoaded.value = false;
        } else {
          statusMsg.value = "启动超时，请检查引擎日志";
        }
      }
    } else {
      statusMsg.value = data.error || "启动失败";
    }
  } catch (e) {
    if (!startCancelled) {
      statusMsg.value = e.response?.data?.error || "启动失败";
    }
  } finally {
    if (!startCancelled) starting.value = false;
  }
}

function cancelStart() {
  startCancelled = true;
  starting.value = false;
  axios.post(`/api/engines/${engine}/stop-gradio`).catch(() => {});
}

async function stopGradio() {
  try {
    await axios.post(`/api/engines/${engine}/stop-gradio`);
    gradioRunning.value = false;
    gradioUrl.value = "";
    iframeLoaded.value = false;
  } catch (e) {
    console.error(e);
  }
}

async function checkStatus() {
  try {
    const { data } = await axios.get(`/api/engines/${engine}/gradio-status`);
    if (data.running) {
      gradioRunning.value = true;
      gradioUrl.value = data.url;
    } else {
      gradioRunning.value = false;
    }
  } catch {}
}

onMounted(async () => {
  try {
    const { data } = await axios.get(`/api/engines/${engine}`);
    engineInfo.value = data;
  } catch {}
  try {
    const { data } = await axios.get("/api/engines/system/device-info");
    gpuInfo.value = data;
    if (!data.gpu_available) device.value = "cpu";
  } catch {}
  checkStatus();
  pollTimer.value = setInterval(checkStatus, 5000);
});

onUnmounted(() => {
  if (pollTimer.value) clearInterval(pollTimer.value);
});
</script>
