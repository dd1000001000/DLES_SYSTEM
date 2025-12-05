<template>
  <div class="error-message">
    <el-result
      icon="error"
      title="页面不存在"
      sub-title="当前页面不存在，请关闭当前页面。"
    >
    </el-result>
  </div>
</template>

<script lang="ts">
export default {
  name: "NotFound",
};
</script>

<script setup lang="ts"></script>

<style scoped lang="scss">
.error-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}
</style>
