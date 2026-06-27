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
  </div>
</template>

<script setup>
import { useThemeStore } from "./stores/theme";
const theme = useThemeStore();
const navLinks = [
  { path: "/", label: "首页" },
  { path: "/models", label: "资源管理" },
  { path: "/about", label: "关于" },
];
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
</style>
