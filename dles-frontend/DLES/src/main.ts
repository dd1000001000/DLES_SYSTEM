import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";
import router from "./router";
import ElementPlus from "element-plus";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import "element-plus/dist/index.css";
import { createPinia } from "pinia";

import { useUserInofStore } from "./init-page/store/userInfo";

const app = createApp(App);
app.use(ElementPlus);
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

app.use(createPinia());

app.use(router);
//路由守卫

router.beforeEach((to, from, next) => {
  const userInfoStore = useUserInofStore();
  const userToken = localStorage.getItem(userInfoStore.getStorageName);
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    // 判断目标路由是否需要登录
    if (!userToken) {
      // 如果未登录，跳转到登录页面
      next({ path: "/login/login", query: { redirect: to.fullPath } });
    } else {
      next();
    }
  } else {
    next();
  }
});

app.mount("#app");
