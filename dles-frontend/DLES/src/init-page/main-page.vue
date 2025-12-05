<template>
  <el-container style="height: 100%">
    <el-header class="introduction" height="100px">
      <el-link :underline="false" href="/#/home">
        <h2 class="introduction-text">基于数据湖的表格增强系统</h2>
      </el-link>
      <div class="header-tools-bar">
        <div class="welcome-text">欢迎，{{ userInfoStore.getUserName }}</div>
        <el-avatar
          :size="30"
          :src="
            userInfoStore.avatarUrl
              ? `http://localhost:8080/avatars/${userInfoStore.avatarUrl}`
              : 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'
          "
        />
        <el-button :icon="Setting" circle @click="router.push('/settings')" />
        <el-button
          :icon="SwitchButton"
          type="danger"
          circle
          style="margin: 0"
          @click="userLogout"
        />
      </div>
    </el-header>
    <el-container>
      <el-aside width="200px">
        <el-menu class="menu" router>
          <el-menu-item index="1" route="/home">
            <el-icon><House /></el-icon>
            <span>首页</span>
          </el-menu-item>
          <el-menu-item index="2" route="/enhance">
            <el-icon><Edit /></el-icon>
            <span>表格增强</span>
          </el-menu-item>
          <el-menu-item index="3" route="/train">
            <el-icon><VideoPlay /></el-icon>
            <span>增强评估</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-main style="padding: 0 20px 0 20px">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script lang="ts">
export default {
  name: "MainPage",
};
</script>

<script setup lang="ts">
import { Setting, SwitchButton } from "@element-plus/icons-vue";
import { useRouter } from "vue-router";
import { useUserInofStore } from "./store/userInfo";
import { onMounted } from "vue";
import { LoginService } from "../login-page/service/login-servive";

const router = useRouter();
const userInfoStore = useUserInofStore();
const loginService = new LoginService();

onMounted(async () => {
  const res = await loginService.getUserInfo();
  userInfoStore.setUser({
    userEmail: res.email,
    avatarUrl: res.avatar_path,
    userType: res.userType,
  });
});

function userLogout() {
  localStorage.removeItem(userInfoStore.getStorageName);
  userInfoStore.clearUserInfo();
  router.push("/login/login");
}
</script>

<style scoped lang="scss">
.introduction {
  display: flex;
  justify-content: space-between;
  flex-direction: row;
  align-items: center;
  > .el-link {
    .introduction-text {
      color: rgb(31, 31, 31);
      margin-left: 100px;
      font-size: 1.7em;
    }
  }
  .header-tools-bar {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 20px;
    margin-right: 100px;
  }
}

.menu {
  height: 100%;
}
</style>
