import { defineStore } from "pinia";
import { ref, watchEffect } from "vue";

export const useThemeStore = defineStore("theme", () => {
  const saved = typeof window !== "undefined" ? localStorage.getItem("uni-tts-theme") : null;
  const isDark = ref(saved === "dark");

  function toggle() {
    isDark.value = !isDark.value;
  }

  watchEffect(() => {
    const root = document.documentElement;
    if (isDark.value) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("uni-tts-theme", isDark.value ? "dark" : "light");
  });

  return { isDark, toggle };
});
