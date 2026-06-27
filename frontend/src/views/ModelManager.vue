<template>
  <div>
    <div class="mb-8">
      <h1 class="text-heading-md mb-2" style="color: var(--ink)">资源管理</h1>
      <p class="text-body-md" style="color: var(--steel)">安装引擎运行环境 & 下载模型文件</p>
    </div>

    <div class="flex gap-2 mb-8">
      <button v-for="t in tabs" :key="t.key" @click="tab = t.key"
        class="px-5 py-2 rounded-full text-body-sm font-medium transition-all duration-150"
        :style="tab === t.key ? 'background: var(--btn-primary-bg); color: var(--btn-primary-text)' : 'background: var(--btn-tertiary-bg); color: var(--steel); border: 1px solid var(--border-hairline)'">
        {{ t.label }}
      </button>
    </div>

    <!-- ── Engine Install Tab ── -->
    <div v-if="tab === 'engines'" class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <div v-for="eng in engines" :key="eng.name" class="glass rounded-xl p-6 transition-all duration-150 hover:shadow-card-hover">
        <div class="flex items-start justify-between mb-3">
          <div>
            <h3 class="text-card-title" style="color: var(--ink)">{{ eng.display_name }}</h3>
            <p class="text-micro mt-1" style="color: var(--muted)">{{ eng.github_repo }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="eng.device_type" class="badge" :class="eng.device_type === 'gpu' ? 'badge-ready' : 'badge-missing'">
              {{ eng.device_type === 'gpu' ? 'GPU' : 'CPU' }}
            </span>
            <span class="badge" :class="engStatusBadge(eng)">{{ engStatusText(eng) }}</span>
          </div>
        </div>

        <p class="text-micro mb-4" style="color: var(--steel)">Python {{ eng.python_version }} · {{ eng.entry_script }}</p>

        <!-- Install controls (only when not installed) -->
        <div v-if="!eng.installed">
          <div class="mb-3">
            <label class="text-micro block mb-2" style="color: var(--steel)">安装类型</label>
            <div class="flex gap-2">
              <button @click="deviceType[eng.name] = 'cpu'" class="flex-1 px-3 py-1.5 rounded-lg text-micro font-medium transition-all duration-150 text-center"
                :style="deviceType[eng.name] === 'cpu'
                  ? 'background: var(--btn-primary-bg); color: var(--btn-primary-text)'
                  : 'background: var(--btn-tertiary-bg); color: var(--steel); border: 1px solid var(--border-hairline)'">
                CPU 版本
              </button>
              <button @click="deviceType[eng.name] = 'gpu'" :disabled="gpuInfo && !gpuInfo.gpu_available"
                class="flex-1 px-3 py-1.5 rounded-lg text-micro font-medium transition-all duration-150 text-center"
                :style="deviceType[eng.name] === 'gpu'
                  ? 'background: var(--btn-primary-bg); color: var(--btn-primary-text)'
                  : gpuInfo && !gpuInfo.gpu_available
                    ? 'background: var(--btn-tertiary-bg); color: var(--muted); opacity: 0.5; cursor: not-allowed'
                    : 'background: var(--btn-tertiary-bg); color: var(--steel); border: 1px solid var(--border-hairline)'">
                GPU 版本
              </button>
            </div>
            <div class="mt-1.5 flex items-center gap-1.5">
              <span v-if="gpuInfo?.gpu_available" class="text-micro" style="color: var(--badge-ready-text)">
                ✓ {{ gpuInfo.gpu_name }} ({{ (gpuInfo.gpu_memory_mb / 1024).toFixed(0) }}GB)
              </span>
              <span v-else-if="gpuInfo" class="text-micro" style="color: var(--muted)">
                ✗ 未检测到 GPU/CUDA
              </span>
            </div>
          </div>

          <label v-if="eng.flash_attention" class="flex items-center gap-2 mb-3 cursor-pointer">
            <input type="checkbox" v-model="flashAttn[eng.name]" class="w-4 h-4 rounded" style="accent-color: var(--btn-primary-bg)" />
            <span class="text-micro" style="color: var(--steel)">安装 Flash Attention 2 (加速推理，需要 CUDA)</span>
          </label>

          <button @click="installEngine(eng)" :disabled="installRunning[eng.name]"
            class="btn-primary w-full py-2.5 text-body-sm flex items-center justify-center gap-2">
            <div v-if="installRunning[eng.name]" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            {{ installRunning[eng.name] ? "安装中..." : "安装引擎" }}
          </button>
        </div>
        <div v-else>
          <button @click="confirmUninstall(eng)" :disabled="uninstallRunning[eng.name]"
            class="w-full py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150 flex items-center justify-center gap-2"
            :style="uninstallRunning[eng.name]
              ? 'background: var(--bg-surface); color: var(--muted); cursor: wait'
              : 'border: 1px solid var(--error-border); color: var(--error-text); background: var(--error-bg)'">
            <div v-if="uninstallRunning[eng.name]" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
            {{ uninstallRunning[eng.name] ? "卸载中..." : "卸载引擎" }}
          </button>
        </div>

        <!-- Progress bar -->
        <div v-if="installRunning[eng.name] || installProgress[eng.name]" class="mt-4">
          <div class="flex items-center justify-between text-micro mb-1.5" style="color: var(--steel)">
            <span>{{ installStep[eng.name] || '准备中...' }}</span>
            <span>{{ installPercent[eng.name] || 0 }}%</span>
          </div>
          <div class="w-full rounded-full h-1.5 overflow-hidden" style="background: var(--border-hairline)">
            <div class="rounded-full h-1.5 transition-all duration-500 ease-out" style="background: var(--btn-primary-bg)" :style="{ width: (installPercent[eng.name] || 0) + '%' }"></div>
          </div>
          <p v-if="installError[eng.name]" class="text-micro mt-2" style="color: var(--error-text)">{{ installError[eng.name] }}</p>
        </div>

        <!-- Terminal log -->
        <div v-if="showTerminal[eng.name]" class="mt-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-micro font-medium" style="color: var(--steel)">终端输出</span>
            <button @click="showTerminal[eng.name] = false" class="text-micro" style="color: var(--muted)">收起</button>
          </div>
          <div ref="terminals" :data-eng="eng.name" class="terminal-output rounded-lg p-3 text-micro font-mono overflow-y-auto" style="background: #0d1117; color: #c9d1d9; max-height: 260px; border: 1px solid #21262d">
            <div v-for="(line, i) in terminalLines[eng.name]" :key="i" class="whitespace-pre-wrap break-all leading-relaxed" v-html="ansiToHtml(line)"></div>
            <div v-if="installRunning[eng.name]" class="inline-block w-2 h-3.5 ml-0.5 animate-pulse" style="background: #58a6ff"></div>
          </div>
        </div>
        <button v-if="installRunning[eng.name] && !showTerminal[eng.name]" @click="showTerminal[eng.name] = true" class="mt-3 text-micro w-full text-center" style="color: var(--btn-primary-bg)">
          查看终端输出
        </button>
      </div>
    </div>

    <!-- ── Model Download Tab ── -->
    <div v-if="tab === 'models'" class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <div v-for="model in models" :key="model.engine_name + (model.is_asr ? '-asr' : '')" class="glass rounded-xl p-6 transition-all duration-150 hover:shadow-card-hover"
        :style="model.is_asr ? 'border-left: 3px solid var(--badge-loaded-text)' : ''">
        <div class="flex items-start justify-between mb-3">
          <div>
            <h3 class="text-card-title" style="color: var(--ink)">{{ model.display_name }}</h3>
            <p class="text-micro font-mono mt-1" style="color: var(--muted)">{{ model.model_scope_id }}</p>
            <p v-if="model.is_asr" class="text-micro mt-1" style="color: var(--badge-loaded-text)">
              {{ model.parent_engine }} · ASR 语音识别 · {{ model.asr_description }}
            </p>
          </div>
          <span class="badge" :class="model.downloaded ? 'badge-ready' : 'badge-not-installed'">
            {{ model.downloaded ? `已下载 ${model.total_size_mb}MB` : "未下载" }}
          </span>
        </div>

        <div class="flex items-center gap-2 text-micro mb-4" style="color: var(--muted)">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>
          <span class="truncate">{{ model.model_dir }}</span>
        </div>

        <div class="flex gap-2">
          <button @click="downloadModel(model)" :disabled="dlRunning[model.engine_name + (model.is_asr ? '-asr' : '')]"
            class="flex-1 py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150 flex items-center justify-center gap-2"
            :class="dlRunning[model.engine_name + (model.is_asr ? '-asr' : '')] ? '' : model.downloaded ? 'btn-tertiary' : 'btn-primary'"
            :style="dlRunning[model.engine_name + (model.is_asr ? '-asr' : '')] ? 'background: var(--bg-surface); color: var(--muted); cursor: wait' : ''">
            <div v-if="dlRunning[model.engine_name + (model.is_asr ? '-asr' : '')]" class="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
            {{ dlRunning[model.engine_name + (model.is_asr ? '-asr' : '')] ? "下载中..." : model.downloaded ? "重新下载" : "下载模型" }}
          </button>
          <button v-if="model.downloaded" @click="confirmDeleteModel(model)"
            class="px-4 py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150 flex items-center gap-1.5"
            :style="deleteModelRunning[model.engine_name + (model.is_asr ? '-asr' : '')]
              ? 'background: var(--bg-surface); color: var(--muted); cursor: wait'
              : 'border: 1px solid var(--error-border); color: var(--error-text); background: var(--error-bg)'">
            <div v-if="deleteModelRunning[model.engine_name + (model.is_asr ? '-asr' : '')]" class="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
            {{ deleteModelRunning[model.engine_name + (model.is_asr ? '-asr' : '')] ? "删除中..." : "删除" }}
          </button>
        </div>

        <div v-if="dlProgress[model.engine_name + (model.is_asr ? '-asr' : '')] !== undefined" class="mt-4">
          <div class="flex items-center justify-between text-micro mb-1.5" style="color: var(--steel)">
            <span>{{ dlDetail[model.engine_name + (model.is_asr ? '-asr' : '')] || '下载进度' }}</span>
            <span>{{ dlProgress[model.engine_name + (model.is_asr ? '-asr' : '')] }}%</span>
          </div>
          <div class="w-full rounded-full h-1.5 overflow-hidden" style="background: var(--border-hairline)">
            <div class="rounded-full h-1.5 transition-all duration-500 ease-out" style="background: var(--btn-primary-bg)" :style="{ width: dlProgress[model.engine_name + (model.is_asr ? '-asr' : '')] + '%' }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Disk usage -->
    <div class="mt-8 glass rounded-xl p-6 flex items-center justify-between">
      <div>
        <h3 class="text-body-sm font-medium" style="color: var(--ink)">磁盘空间</h3>
        <p class="text-micro mt-1" style="color: var(--muted)">引擎 + 模型总计占用</p>
      </div>
      <p class="text-heading-lg" style="color: var(--ink)">{{ totalSize }}<span class="text-body-sm ml-1" style="color: var(--steel)">MB</span></p>
    </div>

    <!-- Toast -->
    <transition name="fade">
      <div v-if="toast" class="fixed bottom-6 right-6 z-50 glass-strong rounded-xl px-6 py-4 max-w-sm shadow-card-hover" :style="{ borderLeft: '4px solid ' + (toast.type === 'error' ? 'var(--error-text)' : 'var(--badge-ready-text)') }">
        <p class="text-body-sm" style="color: var(--charcoal)">{{ toast.msg }}</p>
      </div>
    </transition>

    <!-- Uninstall Confirm Modal -->
    <transition name="fade">
      <div v-if="uninstallTarget" class="fixed inset-0 z-50 flex items-center justify-center" style="background: var(--overlay); backdrop-filter: blur(4px)" @click.self="cancelUninstall">
        <div class="glass-strong rounded-hero p-8 max-w-sm w-full mx-4 shadow-modal">
          <!-- Confirm state -->
          <template v-if="!uninstallPhase">
            <div class="text-center mb-6">
              <div class="w-14 h-14 rounded-full mx-auto mb-4 flex items-center justify-center" style="background: var(--error-bg)">
                <svg class="w-7 h-7" style="color: var(--error-text)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </div>
              <h3 class="text-heading-sm mb-2" style="color: var(--ink)">卸载引擎</h3>
              <p class="text-body-sm" style="color: var(--steel)">确定要卸载 <strong style="color: var(--ink)">{{ uninstallTarget.display_name }}</strong> 吗？</p>
            </div>
            <div class="rounded-lg p-3 mb-6" style="background: var(--error-bg); border: 1px solid var(--error-border)">
              <p class="text-micro" style="color: var(--error-text)">将删除以下内容：</p>
              <ul class="text-micro mt-1.5 space-y-1" style="color: var(--error-text)">
                <li>• 引擎源码目录</li>
                <li>• Python 虚拟环境</li>
                <li>• 安装配置记录</li>
              </ul>
            </div>
            <div class="flex gap-3">
              <button @click="cancelUninstall" class="flex-1 py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150"
                style="border: 1px solid var(--border-hairline); color: var(--steel)">取消</button>
              <button @click="doUninstall" class="flex-1 py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150 flex items-center justify-center gap-2"
                style="background: var(--error-text); color: white">
                确认卸载
              </button>
            </div>
          </template>

          <!-- Uninstalling state -->
          <template v-else-if="uninstallPhase === 'deleting'">
            <div class="text-center py-4">
              <div class="w-14 h-14 border-3 rounded-full animate-spin mx-auto mb-5" style="border-color: var(--border-hairline); border-top-color: var(--error-text); border-width: 3px"></div>
              <h3 class="text-heading-sm mb-2" style="color: var(--ink)">正在卸载</h3>
              <p class="text-body-sm mb-1" style="color: var(--steel)">{{ uninstallTarget.display_name }}</p>
              <p class="text-micro mt-3" style="color: var(--muted)">正在删除引擎文件和虚拟环境...</p>
            </div>
          </template>

          <!-- Done state -->
          <template v-else-if="uninstallPhase === 'done'">
            <div class="text-center py-4">
              <div class="w-14 h-14 rounded-full mx-auto mb-5 flex items-center justify-center" style="background: var(--badge-ready-bg)">
                <svg class="w-7 h-7" style="color: var(--badge-ready-text)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
              </div>
              <h3 class="text-heading-sm mb-2" style="color: var(--ink)">卸载完成</h3>
              <p class="text-body-sm" style="color: var(--steel)">{{ uninstallTarget.display_name }} 已成功卸载</p>
              <button @click="finishUninstall" class="mt-6 w-full py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150"
                style="background: var(--btn-primary-bg); color: var(--btn-primary-text)">完成</button>
            </div>
          </template>
        </div>
      </div>
    </transition>

    <!-- Delete Model Confirm Modal -->
    <transition name="fade">
      <div v-if="deleteModelTarget" class="fixed inset-0 z-50 flex items-center justify-center" style="background: var(--overlay); backdrop-filter: blur(4px)" @click.self="cancelDeleteModel">
        <div class="glass-strong rounded-hero p-8 max-w-sm w-full mx-4 shadow-modal">
          <!-- Confirm state -->
          <template v-if="!deleteModelPhase">
            <div class="text-center mb-6">
              <div class="w-14 h-14 rounded-full mx-auto mb-4 flex items-center justify-center" style="background: var(--error-bg)">
                <svg class="w-7 h-7" style="color: var(--error-text)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </div>
              <h3 class="text-heading-sm mb-2" style="color: var(--ink)">删除模型</h3>
              <p class="text-body-sm" style="color: var(--steel)">确定要删除 <strong style="color: var(--ink)">{{ deleteModelTarget.display_name }}</strong> 的模型文件吗？</p>
            </div>
            <div class="rounded-lg p-3 mb-6" style="background: var(--error-bg); border: 1px solid var(--error-border)">
              <p class="text-micro" style="color: var(--error-text)">将删除以下内容：</p>
              <ul class="text-micro mt-1.5 space-y-1" style="color: var(--error-text)">
                <li>• 模型权重文件</li>
                <li>• 模型目录: <span class="font-mono">{{ deleteModelTarget.model_dir }}</span></li>
              </ul>
            </div>
            <div class="flex gap-3">
              <button @click="cancelDeleteModel" class="flex-1 py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150"
                style="border: 1px solid var(--border-hairline); color: var(--steel)">取消</button>
              <button @click="doDeleteModel" class="flex-1 py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150 flex items-center justify-center gap-2"
                style="background: var(--error-text); color: white">
                确认删除
              </button>
            </div>
          </template>

          <!-- Deleting state -->
          <template v-else-if="deleteModelPhase === 'deleting'">
            <div class="text-center py-4">
              <div class="w-14 h-14 border-3 rounded-full animate-spin mx-auto mb-5" style="border-color: var(--border-hairline); border-top-color: var(--error-text); border-width: 3px"></div>
              <h3 class="text-heading-sm mb-2" style="color: var(--ink)">正在删除</h3>
              <p class="text-body-sm mb-1" style="color: var(--steel)">{{ deleteModelTarget.display_name }}</p>
              <p class="text-micro mt-3" style="color: var(--muted)">正在删除模型文件...</p>
            </div>
          </template>

          <!-- Done state -->
          <template v-else-if="deleteModelPhase === 'done'">
            <div class="text-center py-4">
              <div class="w-14 h-14 rounded-full mx-auto mb-5 flex items-center justify-center" style="background: var(--badge-ready-bg)">
                <svg class="w-7 h-7" style="color: var(--badge-ready-text)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
              </div>
              <h3 class="text-heading-sm mb-2" style="color: var(--ink)">删除完成</h3>
              <p class="text-body-sm" style="color: var(--steel)">{{ deleteModelTarget.display_name }} 模型已删除</p>
              <button @click="finishDeleteModel" class="mt-6 w-full py-2.5 rounded-full text-body-sm font-semibold transition-all duration-150"
                style="background: var(--btn-primary-bg); color: var(--btn-primary-text)">完成</button>
            </div>
          </template>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from "vue";
import axios from "axios";

const tabs = [{ key: "engines", label: "引擎安装" }, { key: "models", label: "模型下载" }];
const tab = ref("engines");

const engines = ref([]);
const models = ref([]);
const toast = ref(null);

// Install state
const flashAttn = reactive({});
const deviceType = reactive({});
const gpuInfo = ref(null);
const installRunning = reactive({});
const uninstallRunning = reactive({});
const uninstallTarget = ref(null);
const uninstallPhase = ref(null);
const deleteModelRunning = reactive({});
const deleteModelTarget = ref(null);
const deleteModelPhase = ref(null);
const installProgress = reactive({});
const installStep = reactive({});
const installPercent = reactive({});
const installError = reactive({});
const showTerminal = reactive({});
const terminalLines = reactive({});
let sseSources = {};

// Download state
const dlRunning = reactive({});
const dlProgress = reactive({});
const dlDetail = reactive({});

const totalSize = computed(() => models.value.reduce((s, m) => s + m.total_size_mb, 0).toFixed(0));

function showToast(msg, type = "success") { toast.value = { msg, type }; setTimeout(() => (toast.value = null), 3000); }

function engStatusBadge(eng) {
  if (eng.installing || installRunning[eng.name]) return "badge-missing";
  if (eng.installed && eng.models_ready) return "badge-ready";
  if (eng.installed) return "badge-missing";
  return "badge-not-installed";
}
function engStatusText(eng) {
  if (eng.installing || installRunning[eng.name]) return "安装中";
  if (eng.installed && eng.models_ready) return "就绪";
  if (eng.installed) return "已安装";
  return "未安装";
}

function ansiToHtml(str) {
  return str
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\x1b\[32m(.*?)\x1b\[0m/g, '<span style="color:#3fb950">$1</span>')
    .replace(/\x1b\[31m(.*?)\x1b\[0m/g, '<span style="color:#f85149">$1</span>')
    .replace(/\x1b\[33m(.*?)\x1b\[0m/g, '<span style="color:#d29922">$1</span>')
    .replace(/\x1b\[36m(.*?)\x1b\[0m/g, '<span style="color:#58a6ff">$1</span>');
}

function scrollTerm(name) {
  nextTick(() => {
    const el = document.querySelector(`[data-eng="${name}"]`);
    if (el) el.scrollTop = el.scrollHeight;
  });
}

// ── Install ──

async function installEngine(eng) {
  try {
    const { data } = await axios.post("/api/engines/install", {
      engine_name: eng.name,
      flash_attention: !!flashAttn[eng.name],
      device_type: deviceType[eng.name] || "cpu",
    });
    if (data.status === "already_installed") { showToast(`${eng.display_name} 已安装`); return; }
    if (data.error) { showToast(data.error, "error"); return; }
    installRunning[eng.name] = true;
    installProgress[eng.name] = true;
    terminalLines[eng.name] = [];
    showTerminal[eng.name] = true;
    connectLogSSE(eng.name);
    showToast(`${eng.display_name} 开始安装`);
  } catch (e) { showToast(`安装失败: ${e.response?.data?.error || e.message}`, "error"); }
}

function connectLogSSE(name) {
  if (sseSources[name]) sseSources[name].close();
  const es = new EventSource(`/api/engines/install/${name}/logs`);
  sseSources[name] = es;

  es.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.line !== undefined) {
        if (!terminalLines[name]) terminalLines[name] = [];
        terminalLines[name].push(msg.line);
        if (terminalLines[name].length > 500) terminalLines[name].splice(0, terminalLines[name].length - 500);
        scrollTerm(name);
      }
      if (msg.progress) {
        installStep[name] = msg.progress.step;
        installPercent[name] = msg.progress.percent;
        installError[name] = msg.progress.error;
      }
      if (msg.done) {
        es.close(); delete sseSources[name];
        installRunning[name] = false;
        loadEngines();
      }
    } catch {}
  };
  es.onerror = () => { es.close(); delete sseSources[name]; };
}

function confirmUninstall(eng) {
  uninstallTarget.value = eng;
  uninstallPhase.value = null;
}

function cancelUninstall() {
  if (uninstallPhase.value === 'deleting') return;
  uninstallTarget.value = null;
  uninstallPhase.value = null;
}

async function doUninstall() {
  if (!uninstallTarget.value) return;
  const eng = uninstallTarget.value;
  uninstallPhase.value = 'deleting';
  uninstallRunning[eng.name] = true;
  try {
    await axios.post("/api/engines/uninstall", { engine_name: eng.name });
    uninstallPhase.value = 'done';
    loadEngines();
  } catch (e) {
    showToast(`卸载失败: ${e.response?.data?.error || e.message}`, "error");
    uninstallPhase.value = null;
  } finally {
    uninstallRunning[eng.name] = false;
  }
}

function finishUninstall() {
  uninstallTarget.value = null;
  uninstallPhase.value = null;
}

// ── Download ──

async function downloadModel(model) {
  const key = model.engine_name + (model.is_asr ? '-asr' : '');
  dlRunning[key] = true;
  dlProgress[key] = 0;
  dlDetail[key] = "正在准备...";
  try {
    const { data } = await axios.post("/api/models/download", {
      engine_name: model.engine_name,
      model_id: model.model_scope_id,
      is_asr: !!model.is_asr,
    });
    if (data.task_id) pollDlTask(data.task_id, key, model.engine_name);
    showToast(`${model.display_name} 开始下载`);
  } catch (e) {
    showToast(`下载失败: ${e.message}`, "error");
    dlRunning[key] = false;
    delete dlProgress[key]; delete dlDetail[key];
  }
}

function pollDlTask(tid, key, engineName) {
  const iv = setInterval(async () => {
    try {
      const { data } = await axios.get(`/api/models/tasks/${tid}`);
      if (data.status === "completed") {
        clearInterval(iv); dlRunning[key] = false;
        delete dlProgress[key]; delete dlDetail[key];
        showToast(`下载完成`); loadModels();
      } else if (data.status === "failed") {
        clearInterval(iv); dlRunning[key] = false;
        delete dlProgress[key]; delete dlDetail[key];
        showToast(`下载失败: ${data.error}`, "error");
      } else {
        dlProgress[key] = Math.round(data.progress || 0);
        if (data.detail) dlDetail[key] = data.detail;
      }
    } catch { clearInterval(iv); dlRunning[key] = false; }
  }, 1000);
}

function confirmDeleteModel(model) {
  deleteModelTarget.value = model;
  deleteModelPhase.value = null;
}

function cancelDeleteModel() {
  if (deleteModelPhase.value === 'deleting') return;
  deleteModelTarget.value = null;
  deleteModelPhase.value = null;
}

async function doDeleteModel() {
  if (!deleteModelTarget.value) return;
  const model = deleteModelTarget.value;
  const key = model.engine_name + (model.is_asr ? '-asr' : '');
  deleteModelPhase.value = 'deleting';
  deleteModelRunning[key] = true;
  try {
    if (model.is_asr) {
      await axios.delete(`/api/models/${model.engine_name}`, { params: { is_asr: true, model_id: model.model_scope_id } });
    } else {
      await axios.delete(`/api/models/${model.engine_name}`);
    }
    deleteModelPhase.value = 'done';
    loadModels();
  } catch (e) {
    showToast(`删除失败: ${e.response?.data?.error || e.message}`, "error");
    deleteModelPhase.value = null;
  } finally {
    deleteModelRunning[key] = false;
  }
}

function finishDeleteModel() {
  deleteModelTarget.value = null;
  deleteModelPhase.value = null;
}

// ── Load data ──

async function loadEngines() {
  try {
    const { data } = await axios.get("/api/engines/");
    engines.value = data.engines || [];
  } catch (e) {
    console.error("Failed to load engines:", e);
    engines.value = [];
  }
}
async function loadModels() {
  try { const { data } = await axios.get("/api/models/"); models.value = data.models; } catch {}
}

function resumeInstallState(name, progress) {
  installRunning[name] = true;
  installProgress[name] = true;
  installStep[name] = progress.step || '';
  installPercent[name] = progress.percent || 0;
  installError[name] = progress.error || null;
  terminalLines[name] = [];
  showTerminal[name] = true;
  connectLogSSE(name);
}

let pollTimer = null;
onMounted(async () => {
  await loadEngines();
  loadModels();
  try {
    const { data } = await axios.get("/api/engines/system/device-info");
    gpuInfo.value = data;
    for (const eng of engines.value) {
      deviceType[eng.name] = data.gpu_available ? "gpu" : "cpu";
    }
  } catch {}
  pollTimer = setInterval(loadEngines, 5000);
  for (const eng of engines.value) {
    if (eng.installing) {
      try {
        const { data: prog } = await axios.get(`/api/engines/install/${eng.name}/status`);
        resumeInstallState(eng.name, prog);
      } catch {
        resumeInstallState(eng.name, {});
      }
    }
  }
});
onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
  Object.values(sseSources).forEach(es => es.close());
});
</script>

<style scoped>
.terminal-output {
  scrollbar-width: thin;
  scrollbar-color: #30363d #0d1117;
}
.terminal-output::-webkit-scrollbar { width: 6px; }
.terminal-output::-webkit-scrollbar-track { background: #0d1117; }
.terminal-output::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
</style>
