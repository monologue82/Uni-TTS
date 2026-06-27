import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/",
    name: "Home",
    component: () => import("../views/Home.vue"),
  },
  {
    path: "/inference/:engine",
    name: "Inference",
    component: () => import("../views/Inference.vue"),
  },
  {
    path: "/models",
    name: "Models",
    component: () => import("../views/ModelManager.vue"),
  },
  {
    path: "/gradio/:engine",
    name: "Gradio",
    component: () => import("../views/GradioEmbed.vue"),
  },
  {
    path: "/about",
    name: "About",
    component: () => import("../views/About.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
