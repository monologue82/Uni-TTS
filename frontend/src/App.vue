<template>
  <div class="min-h-screen" style="background: var(--bg); transition: background 200ms ease">
    <nav class="glass sticky top-0 z-50 px-8 py-4 flex items-center justify-between" style="border-bottom: 1px solid var(--border-soft)">
      <router-link to="/" class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold" style="background: var(--btn-primary-bg); color: var(--btn-primary-text)">
          U
        </div>
        <span class="text-lg font-semibold tracking-tight" style="color: var(--ink)">Uni-TTS</span>
      </router-link>
      <div class="flex items-center gap-2">
        <button
          v-if="hasUpdate"
          @click="showUpdateModal = true"
          class="update-badge px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5"
          title="有新版本可用"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
          新版本 {{ remoteVersion }}
        </button>
        <router-link
          v-for="link in navLinks"
          :key="link.path"
          :to="link.path"
          class="nav-link px-5 py-2 rounded-full text-sm font-medium"
          :class="{ active: $route.path === link.path }"
        >
          {{ link.label }}
        </router-link>
        <button
          @click="theme.toggle()"
          class="theme-toggle w-9 h-9 rounded-full flex items-center justify-center"
          :title="theme.isDark ? '切换亮色' : '切换暗色'"
        >
          <svg v-if="theme.isDark" class="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
          <svg v-else class="w-[18px] h-[18px]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>
        </button>
      </div>
    </nav>
    <main :class="$route.path === '/about' ? '' : 'max-w-7xl mx-auto px-8 py-12'">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- Update Modal -->
    <transition name="fade">
      <div v-if="showUpdateModal" class="fixed inset-0 z-50 flex items-center justify-center" style="background: var(--overlay); backdrop-filter: blur(4px)" @click.self="showUpdateModal = false">
        <div class="glass-strong rounded-hero p-8 max-w-lg w-full mx-4 shadow-modal" style="background: var(--bg-card, #fff)">
          <template v-if="!updating && !updateDone && !updateError">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-10 h-10 rounded-full flex items-center justify-center" style="background: var(--badge-ready-bg); color: var(--badge-ready-text)">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
              </div>
              <div>
                <h3 class="text-heading-sm" style="color: var(--ink)">发现新版本</h3>
                <p class="text-micro" style="color: var(--muted)">v{{ localVersion }} → v{{ remoteVersion }}</p>
              </div>
            </div>
            <div v-if="releaseBody" class="rounded-lg p-4 mb-4 max-h-48 overflow-y-auto text-body-sm" style="background: var(--bg-input); color: var(--steel); white-space: pre-wrap">{{ releaseBody }}</div>
            <div class="flex gap-3">
              <button @click="showUpdateModal = false" class="flex-1 py-2.5 rounded-full text-sm font-medium transition-colors" style="border: 1px solid var(--border-hairline); color: var(--steel)">稍后再说</button>
              <button @click="doUpdate" class="flex-1 py-2.5 rounded-full text-sm font-medium transition-colors" style="background: var(--btn-primary-bg); color: var(--btn-primary-text)">立即更新</button>
            </div>
          </template>

          <template v-else-if="updating">
            <div class="text-center py-6">
              <div class="w-12 h-12 border-3 rounded-full animate-spin mx-auto mb-4" style="border-color: var(--border-hairline); border-top-color: var(--ink); border-width: 3px"></div>
              <h3 class="text-heading-sm mb-1" style="color: var(--ink)">正在更新</h3>
              <p class="text-body-sm" style="color: var(--steel)">正在下载并应用更新，请勿关闭程序...</p>
            </div>
          </template>

          <template v-else-if="updateDone">
            <div class="text-center py-6">
              <div class="w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4" style="background: var(--badge-ready-bg); color: var(--badge-ready-text)">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
              </div>
              <h3 class="text-heading-sm mb-1" style="color: var(--ink)">更新完成</h3>
              <p class="text-body-sm" style="color: var(--steel)">程序即将自动重启...</p>
            </div>
          </template>

          <template v-else-if="updateError">
            <div class="flex items-center gap-3 mb-4">
              <div class="w-10 h-10 rounded-full flex items-center justify-center" style="background: var(--error-bg); color: var(--error-text)">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
              </div>
              <div>
                <h3 class="text-heading-sm" style="color: var(--ink)">更新失败</h3>
                <p class="text-body-sm" style="color: var(--error-text)">{{ updateError }}</p>
              </div>
            </div>
            <button @click="showUpdateModal = false; updateError = ''" class="w-full py-2.5 rounded-full text-sm font-medium" style="border: 1px solid var(--border-hairline); color: var(--steel)">关闭</button>
          </template>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useThemeStore } from "./stores/theme";
import axios from "axios";

const theme = useThemeStore();
const navLinks = [
  { path: "/", label: "首页" },
  { path: "/models", label: "资源管理" },
  { path: "/about", label: "关于" },
];

const hasUpdate = ref(false);
const remoteVersion = ref("");
const localVersion = ref("");
const releaseBody = ref("");
const showUpdateModal = ref(false);
const updating = ref(false);
const updateDone = ref(false);
const updateError = ref("");
let downloadUrl = "";

async function checkForUpdates() {
  try {
    const { data } = await axios.get("/api/system/check-update");
    if (data.has_update) {
      hasUpdate.value = true;
      remoteVersion.value = data.remote_version;
      localVersion.value = data.local_version;
      releaseBody.value = data.release_body || "";
      downloadUrl = data.download_url;
    }
  } catch (e) {
    // silently ignore
  }
}

async function doUpdate() {
  if (!downloadUrl) { updateError.value = "下载地址无效"; return; }
  updating.value = true;
  try {
    const { data } = await axios.post("/api/system/do-update", {
      download_url: downloadUrl,
      version: remoteVersion.value,
    });
    if (data.error) {
      updateError.value = data.error;
    } else {
      updateDone.value = true;
    }
  } catch (e) {
    updateError.value = e.response?.data?.error || e.message;
  } finally {
    updating.value = false;
  }
}

onMounted(() => {
  checkForUpdates();
});
</script>

<style scoped>
.nav-link {
  color: var(--steel);
  border: 1px solid transparent;
  transition: all 150ms ease;
}
.nav-link:hover {
  border-color: var(--border-hairline);
  color: var(--ink);
}
.nav-link.active {
  background: var(--btn-primary-bg);
  color: var(--btn-primary-text);
  border-color: transparent;
}
.theme-toggle {
  border: 1px solid var(--border-hairline);
  color: var(--steel);
  transition: all 150ms ease;
}
.theme-toggle:hover {
  border-color: var(--ink);
  color: var(--ink);
}
.update-badge {
  background: var(--badge-ready-bg);
  color: var(--badge-ready-text);
  border: 1px solid var(--badge-ready-text);
  animation: pulse-badge 2s ease-in-out infinite;
}
.update-badge:hover {
  opacity: 0.85;
}
@keyframes pulse-badge {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
</style>
