<template>
  <div>
    <el-container style="height: 100%">
      <el-header class="introduction" height="100px">
        <h2 class="introduction-text">基于数据湖的表格增强系统</h2>
      </el-header>
      <el-main class="login-main">
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script lang="ts">
export default {
  name: "MainLogin",
};
</script>

<script setup lang="ts"></script>

<style scoped lang="scss">
.introduction {
  display: flex;
  justify-content: flex-start;
  flex-direction: row;
  align-items: center;
  > .introduction-text {
    color: rgb(31, 31, 31);
    margin-left: 100px;
  }
}

.login-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: absolute;
  top: 40%;
  left: 50%;
  transform: translate(-50%, -50%);
  > .login-card {
    width: 400px;
    > .el-card {
      border-radius: 12px;
    }
  }
}
</style>
