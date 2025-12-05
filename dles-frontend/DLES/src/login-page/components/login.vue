<template>
  <div class="login-card">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">登录系统</div>
      </template>
      <el-form label-width="auto" :model="loginForm">
        <el-form-item label="邮箱" label-position="right" required>
          <el-input
            v-model="loginForm.username"
            placeholder="请输入邮箱"
            clearable
          />
        </el-form-item>
        <el-form-item label="密码" label-position="right" required>
          <el-input
            v-model="loginForm.password"
            placeholder="请输入密码"
            clearable
            type="password"
            show-password
          />
        </el-form-item>
      </el-form>
      <div class="login-tools">
        <el-button type="primary" @click="userLogin">登录</el-button>
        <el-button type="info" @click="router.push('recover')">
          找回密码
        </el-button>
      </div>
      <template #footer>
        还没有账号？点击此处
        <router-link to="./register" append>注册账号</router-link>
      </template>
    </el-card>
  </div>
</template>

<script lang="ts">
export default {
  name: "Login",
};
</script>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { LoginService } from "../service/login-servive";
import { useUserInofStore } from "../../init-page/store/userInfo";

const router = useRouter();
const route = useRoute();
const userStore = useUserInofStore();
const loginService = new LoginService();

const loginForm = ref({
  username: "",
  password: "",
});

async function userLogin() {
  const res = await loginService.userLogin(
    loginForm.value.username,
    loginForm.value.password,
  );
  if (!("message" in res)) {
    localStorage.setItem(userStore.getStorageName, res.access_token);
    const redirect = (
      route.query.redirect === "/" ? "/home" : route.query.redirect || "/home"
    ) as string;
    router.push(redirect);
  }
}
</script>

<style scoped lang="scss">
.login-card {
  width: 400px;
  > .el-card {
    border-radius: 12px;
  }
}
</style>
