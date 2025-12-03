import { createRouter, createWebHistory } from "vue-router";
import Inventory from "./views/Inventory.vue";
import Login from "./views/Login.vue";
import { setAuthToken } from "./api";

function ensureToken() {
  const token = localStorage.getItem("access_token");
  if (token) {
    setAuthToken(token);
  }
  return token;
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", name: "login", component: Login },
    { path: "/", name: "inventory", component: Inventory },
  ],
});

router.beforeEach((to, from, next) => {
  const token = ensureToken();
  if (!token && to.name !== "login") {
    next({ name: "login" });
    return;
  }
  if (token && to.name === "login") {
    next({ name: "inventory" });
    return;
  }
  next();
});

export default router;
