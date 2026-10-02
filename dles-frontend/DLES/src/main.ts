import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";
import router from "./router";
import ElementPlus from "element-plus";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import "element-plus/dist/index.css";
import { createPinia } from "pinia";

import { useUserInofStore } from "./init-page/store/userInfo";
import { LoginService } from "./login-page/service/login-servive";

const app = createApp(App);
app.use(ElementPlus);
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

app.use(createPinia());

app.use(router);
//路由守卫

router.beforeEach(async (to, _from, next) => {
  if (!to.matched.some((record) => record.meta.requiresAuth)) {
    next();
    return;
  }
  // 需要登录的页面：向后端确认登录状态（Cookie 里的凭证前端读不到，只能问后端）
  const userInfoStore = useUserInofStore();
  if (!userInfoStore.getUserName) {
    const res = await new LoginService().getUserInfo();
    if ("message" in res) {
      // 如果未登录，跳转到登录页面
      next({ path: "/login/login", query: { redirect: to.fullPath } });
      return;
    }
    userInfoStore.setUser({
      userEmail: res.email,
      avatarUrl: res.avatar_path,
      userType: res.user_type,
    });
  }
  next();
});

app.mount("#app");
