<template>
  <div>
    <div class="text-center mb-16">
      <h1 class="text-display-lg mb-4" style="color: var(--ink)">选择 TTS 引擎</h1>
      <p class="text-subtitle" style="color: var(--steel)">集成 8 大主流开源 TTS 引擎，一站式语音合成</p>
    </div>

    <div v-if="loading" class="flex justify-center py-24">
      <div class="w-8 h-8 border-2 rounded-full animate-spin" style="border-color: var(--border-hairline); border-top-color: var(--ink)"></div>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <div
        v-for="(engine, i) in engines"
        :key="engine.name"
        @click="handleCardClick(engine)"
        class="rounded-hero p-7 cursor-pointer transition-all duration-200 hover:shadow-card-hover hover:-translate-y-0.5 relative overflow-hidden group"
        :class="cardStyles[i % cardStyles.length]"
      >
        <div class="absolute inset-0 bg-white/0 group-hover:bg-white/10 transition-all duration-200"></div>
        <div class="relative z-10">
          <div class="flex items-start justify-between mb-5">
            <div class="flex flex-col items-end gap-1.5">
              <span class="badge text-micro" :class="stateBadge(engine.state)">{{ stateLabel(engine.state) }}</span>
              <span v-if="engine.model_loading" class="badge text-micro badge-missing">模型加载中</span>
              <span v-if="engine.model_loaded" class="badge text-micro badge-loaded">模型已加载</span>
              <span v-if="engine.gradio_running" class="badge text-micro badge-ready">Gradio 运行中</span>
            </div>
          </div>
          <h3 class="text-card-title mb-2">{{ engine.display_name }}</h3>
          <p class="text-body-sm opacity-80 mb-6 leading-relaxed">{{ engine.description }}</p>
          <div class="flex items-center justify-between text-micro opacity-60">
            <span>{{ engine.min_vram_gb }}GB VRAM</span>
            <span class="font-mono">:{{ engine.port }}</span>
          </div>
        </div>
      </div>
    </div>

    <transition name="fade">
      <div v-if="modalEngine" class="fixed inset-0 z-50 flex items-center justify-center" style="background: var(--overlay); backdrop-filter: blur(4px)" @click.self="cancelModal">
        <div class="glass-strong rounded-hero p-10 max-w-md w-full mx-4 shadow-modal">
          <template v-if="!modelLoading">
            <h3 class="text-heading-sm mb-2" style="color: var(--ink)">{{ modalEngine.display_name }}</h3>
            <p class="text-body-sm mb-6" style="color: var(--steel)">{{ modalEngine.description }}</p>

            <div class="mb-6">
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
              <p class="text-micro mt-1" style="color: var(--muted)">{{ deviceDesc }}</p>
            </div>

            <div class="space-y-3">
              <button @click="goModern(modalEngine)" class="btn-primary w-full flex items-center justify-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                现代化推理页面
              </button>
              <button @click="goGradio(modalEngine)" class="btn-secondary w-full flex items-center justify-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>
                Gradio 原版 Demo
              </button>
            </div>
            <button @click="modalEngine = null" class="mt-5 w-full py-2 text-sm rounded-full transition-colors" style="color: var(--muted)">取消</button>
          </template>

          <template v-else-if="modelLoading && gradioLoading">
            <div class="py-4">
              <div class="text-center mb-6">
                <div class="w-12 h-12 border-3 rounded-full animate-spin mx-auto mb-4" style="border-color: var(--border-hairline); border-top-color: var(--ink); border-width: 3px"></div>
                <h3 class="text-heading-sm mb-1" style="color: var(--ink)">正在加载模型并启动 Gradio</h3>
                <p class="text-body-sm" style="color: var(--steel)">{{ modalEngine.display_name }}</p>
              </div>

              <div class="mb-3">
                <div class="flex items-center justify-between text-micro mb-1.5" style="color: var(--steel)">
                  <span>{{ loadMsg }}</span>
                  <span class="font-mono">{{ loadPercent }}%</span>
                </div>
                <div class="w-full rounded-full h-2 overflow-hidden" style="background: var(--border-hairline)">
                  <div class="h-2 rounded-full transition-all duration-500 ease-out" style="background: var(--btn-primary-bg)" :style="{ width: loadPercent + '%' }"></div>
                </div>
              </div>

              <button @click="cancelLoading" class="mt-4 w-full py-2 text-sm rounded-full transition-colors" style="border: 1px solid var(--border-hairline); color: var(--steel)">取消</button>
            </div>
          </template>

          <template v-else>
            <div class="py-4">
              <div class="text-center mb-6">
                <div class="w-12 h-12 border-3 rounded-full animate-spin mx-auto mb-4" style="border-color: var(--border-hairline); border-top-color: var(--ink); border-width: 3px"></div>
                <h3 class="text-heading-sm mb-1" style="color: var(--ink)">正在加载模型</h3>
                <p class="text-body-sm" style="color: var(--steel)">{{ modalEngine.display_name }}</p>
              </div>

              <div class="mb-3">
                <div class="flex items-center justify-between text-micro mb-1.5" style="color: var(--steel)">
                  <span>{{ loadMsg }}</span>
                  <span class="font-mono">{{ loadPercent }}%</span>
                </div>
                <div class="w-full rounded-full h-2 overflow-hidden" style="background: var(--border-hairline)">
                  <div class="h-2 rounded-full transition-all duration-500 ease-out" style="background: var(--btn-primary-bg)" :style="{ width: loadPercent + '%' }"></div>
                </div>
              </div>

              <button @click="cancelLoading" class="mt-4 w-full py-2 text-sm rounded-full transition-colors" style="border: 1px solid var(--border-hairline); color: var(--steel)">取消</button>
            </div>
          </template>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="alertMsg" class="fixed bottom-6 right-6 z-50 glass-strong rounded-xl px-6 py-4 max-w-sm shadow-card-hover" style="border-left: 4px solid var(--badge-missing-text)">
        <div class="flex items-start gap-3">
          <svg class="w-5 h-5 mt-0.5 flex-shrink-0" style="color: var(--badge-missing-text)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
          <div>
            <p class="text-body-sm" style="color: var(--charcoal)">{{ alertMsg }}</p>
            <router-link to="/models" class="text-micro hover:underline mt-1 inline-block" style="color: var(--btn-primary-bg)">前往模型管理</router-link>
          </div>
          <button @click="alertMsg = ''" class="ml-2" style="color: var(--muted)">&times;</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";

const router = useRouter();
const engines = ref([]);
const loading = ref(true);
const modalEngine = ref(null);
const alertMsg = ref("");
const modelLoading = ref(false);
const gradioLoading = ref(false);
const loadPercent = ref(0);
const loadMsg = ref("正在准备...");
let loadingCancelled = false;

const device = ref("auto");
const gpuInfo = ref(null);
const devices = [
  { value: "auto", label: "自动" },
  { value: "cuda", label: "GPU (CUDA)" },
  { value: "cpu", label: "CPU" },
];
const deviceDesc = computed(() => {
  if (device.value === "cuda" && !gpuInfo.value?.gpu_available) {
    return "CUDA 不可用，请安装 NVIDIA 驱动或选择其他设备";
  }
  return { auto: "自动检测可用设备，优先使用 GPU", cuda: "使用 NVIDIA GPU 加速推理", cpu: "使用 CPU 推理，速度较慢但无需显卡" }[device.value] || "";
});
const cardStyles = ["card-coral","card-blue","card-purple","card-magenta","card-cyan","card-green","card-orange","card-slate"];

function stateBadge(s){
  return {
    ready:"badge-ready",
    installing:"badge-missing",
    installed_no_model:"badge-missing",
    model_only:"badge-missing",
    models_missing:"badge-missing",
    not_installed:"badge-not-installed"
  }[s]||"badge-not-installed"
}
function stateLabel(s){
  return {
    ready:"就绪",
    installing:"安装中",
    installed_no_model:"缺模型",
    model_only:"缺引擎",
    models_missing:"缺模型",
    not_installed:"未安装"
  }[s]||"未知"
}

function handleCardClick(e){
  if(e.state==="not_installed" || e.state==="installing"){
    if(e.state==="installing"){
      alertMsg.value=`${e.display_name} 正在安装中，请等待安装完成。`;
    } else {
      alertMsg.value=`${e.display_name} 尚未安装引擎，请先前往资源管理页面安装引擎。`;
    }
    return
  }
  if(e.state==="installed_no_model"||e.state==="models_missing"){
    alertMsg.value=`${e.display_name} 模型文件未下载，请先前往资源管理页面下载模型。`; return
  }
  if(e.state==="model_only"){
    alertMsg.value=`${e.display_name} 引擎未安装，请先前往资源管理页面安装引擎。`; return
  }
  // Model already loaded → enter inference page directly
  if(e.model_loaded){
    router.push({ name: "Inference", params: { engine: e.name } });
    return
  }
  // Gradio already running → enter Gradio page directly
  if(e.gradio_running){
    router.push({ name: "Gradio", params: { engine: e.name } });
    return
  }
  // Load in progress → resume tracking the existing loading process
  if(e.model_loading){
    modalEngine.value = e
    goModern(e)
    return
  }
  modalEngine.value=e
}

async function goModern(engine) {
  modelLoading.value = true;
  loadPercent.value = 0;
  loadMsg.value = "正在启动推理引擎...";
  loadingCancelled = false;

  // Single progress poller that drives UI updates and navigation.
  // Keeps running when the load-model POST returns "loading" (resume tracking).
  let pollStarted = Date.now();
  const progressTimer = setInterval(async () => {
    if (loadingCancelled) { clearInterval(progressTimer); return; }
    // Safety timeout: 6 minutes
    if (Date.now() - pollStarted > 360000) {
      clearInterval(progressTimer);
      if (!loadingCancelled) {
        modelLoading.value = false;
        alertMsg.value = "模型加载超时";
      }
      return;
    }
    try {
      const { data } = await axios.get(`/api/engines/${engine.name}/load-progress`);
      if (loadingCancelled) { clearInterval(progressTimer); return; }
      if (data.percent !== undefined) loadPercent.value = data.percent;
      if (data.message) loadMsg.value = data.message;
      if (data.status === "ready") {
        clearInterval(progressTimer);
        loadPercent.value = 100;
        loadMsg.value = "模型加载完成";
        await new Promise(r => setTimeout(r, 400));
        if (!loadingCancelled) {
          modalEngine.value = null;
          modelLoading.value = false;
          router.push({ name: "Inference", params: { engine: engine.name } });
        }
      } else if (data.status === "error") {
        clearInterval(progressTimer);
        if (!loadingCancelled) {
          modelLoading.value = false;
          alertMsg.value = data.message || "模型加载失败";
        }
      }
    } catch {}
  }, 500);

  try {
    const { data } = await axios.post(`/api/engines/${engine.name}/load-model`, { device: device.value });
    if (loadingCancelled) { clearInterval(progressTimer); return; }

    if (data.status === "loaded" || data.status === "already_loaded") {
      // progressTimer will navigate, but also navigate immediately for responsiveness
      clearInterval(progressTimer);
      loadPercent.value = 100;
      loadMsg.value = "模型加载完成";
      await new Promise(r => setTimeout(r, 400));
      if (!loadingCancelled) {
        modalEngine.value = null;
        modelLoading.value = false;
        router.push({ name: "Inference", params: { engine: engine.name } });
      }
    } else if (data.status === "loading") {
      // Another load is in progress; keep the progressTimer running to track it
      loadMsg.value = "正在继续加载模型...";
    } else {
      clearInterval(progressTimer);
      modelLoading.value = false;
      alertMsg.value = data.error || "模型加载失败";
    }
  } catch (e) {
    clearInterval(progressTimer);
    if (!loadingCancelled) {
      modelLoading.value = false;
      alertMsg.value = e.response?.data?.error || "模型加载失败";
    }
  }
}

async function goGradio(engine) {
  gradioLoading.value = true;
  modelLoading.value = true;
  loadPercent.value = 0;
  loadMsg.value = "正在启动 Gradio...";
  loadingCancelled = false;

  try {
    const { data } = await axios.post(`/api/engines/${engine.name}/start-gradio`, { device: device.value });
    if (loadingCancelled) return;

    if (data.url || data.status === "already_running") {
      loadPercent.value = 30;
      loadMsg.value = "Gradio 进程已启动，正在加载模型（可能需要较长时间）...";

      let ready = false;
      for (let i = 0; i < 120; i++) {
        if (loadingCancelled) return;
        try {
          const { data: st } = await axios.get(`/api/engines/${engine.name}/gradio-status`);
          if (st.running) {
            loadPercent.value = 80;
            loadMsg.value = "Gradio 服务已就绪，正在加载页面...";
            ready = true;
            break;
          }
        } catch {}
        if (i % 5 === 4) {
          loadPercent.value = Math.min(30 + i, 75);
        }
        await new Promise(r => setTimeout(r, 2000));
      }

      if (!loadingCancelled) {
        if (ready) {
          loadPercent.value = 100;
          loadMsg.value = "就绪";
          await new Promise(r => setTimeout(r, 600));
          modalEngine.value = null;
          modelLoading.value = false;
          gradioLoading.value = false;
          router.push({ name: "Gradio", params: { engine: engine.name } });
        } else {
          modelLoading.value = false;
          gradioLoading.value = false;
          alertMsg.value = "Gradio 启动超时，请检查引擎日志";
        }
      }
    } else {
      modelLoading.value = false;
      gradioLoading.value = false;
      alertMsg.value = data.error || "Gradio 启动失败";
    }
  } catch (e) {
    if (!loadingCancelled) {
      modelLoading.value = false;
      gradioLoading.value = false;
      alertMsg.value = e.response?.data?.error || "启动失败";
    }
  }
}

function cancelLoading() {
  // Just close the window — keep the underlying load/gradio process running
  // so clicking the card again can resume tracking instead of restarting.
  loadingCancelled = true;
  modelLoading.value = false;
  gradioLoading.value = false;
  modalEngine.value = null;
}

function cancelModal() {
  if (modelLoading.value) cancelLoading();
  else modalEngine.value = null;
}

let pollTimer = null;
onMounted(async () => {
  try {
    const { data } = await axios.get("/api/engines/");
    engines.value = data.engines || [];
  } catch (e) {
    console.error(e);
    engines.value = [];
  } finally { loading.value = false; }
  try { const { data } = await axios.get("/api/engines/system/device-info"); gpuInfo.value = data; if (!data.gpu_available) device.value = "cpu"; }
  catch (e) { console.error(e); }
  // Poll engine status every 3 seconds
  pollTimer = setInterval(async () => {
    try {
      const { data } = await axios.get("/api/engines/");
      engines.value = data.engines || [];
    } catch {}
  }, 3000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});
</script>
