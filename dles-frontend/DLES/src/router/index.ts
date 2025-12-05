import {
  createRouter,
  createWebHashHistory,
  type RouteRecordRaw,
} from "vue-router";
import mainPage from "../init-page/main-page.vue";
import home from "../init-page/components/home.vue";
import mainLogin from "../login-page/main-login.vue";
import login from "../login-page/components/login.vue";
import register from "../login-page/components/register.vue";
import recover from "../login-page/components/recover.vue";
import notFound from "../not-found.vue";
import settings from "../init-page/components/settings.vue";
import enhancePage from "../enhance-page/enhance-page.vue";
import trainPage from "../train-page/train/train-page.vue";
import qwenCode from "../train-page/code-page/qwen-code.vue";
const routes: Array<RouteRecordRaw> = [
  {
    path: "/",
    name: "",
    component: mainPage,
    meta: { requiresAuth: true },
    children: [
      {
        path: "home",
        name: "Home",
        component: home,
      },
      //表格增强
      {
        path: "enhance/:id?",
        name: "Enhance",
        component: enhancePage,
      },
      //模型训练
      {
        path: "/train",
        name: "Train",
        component: trainPage,
      },
      //千问帮写
      {
        path: "/train/code",
        name: "AI-Codeing",
        component: qwenCode,
      },
    ],
  },
  //登录
  {
    path: "/login",
    name: "MainLogin",
    component: mainLogin,
    children: [
      {
        path: "login",
        name: "Login",
        component: login,
      },
      {
        path: "register",
        name: "Register",
        component: register,
      },
      {
        path: "recover",
        name: "Recover",
        component: recover,
      },
    ],
  },
  {
    path: "/settings",
    name: "Setting",
    component: settings,
    meta: { requiresAuth: true },
  },
  // 404 通配路由
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: notFound,
  },
];

const router = createRouter({
  history: createWebHashHistory(),
  routes,
});

export default router;
