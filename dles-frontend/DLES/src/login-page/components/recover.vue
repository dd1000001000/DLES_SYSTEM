<template>
  <div class="login-card">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">找回密码</div>
      </template>
      <div v-if="isFormShow">
        <el-form
          ref="recoverFormRef1"
          label-width="auto"
          :model="recoverForm"
          :rules="recoverRules1"
        >
          <el-form-item
            label="邮箱"
            prop="username"
            label-position="right"
            required
          >
            <el-input
              v-model="recoverForm.username"
              placeholder="请输入邮箱"
              clearable
            />
          </el-form-item>
        </el-form>
        <div class="login-tools">
          <el-button
            type="primary"
            @click="sendRecoverMessage(recoverFormRef1)"
          >
            下一步</el-button
          >
        </div>
      </div>
      <div v-else>
        <el-form
          ref="recoverFormRef2"
          label-width="auto"
          :model="recoverForm"
          :rules="recoverRules2"
        >
          <el-form-item
            label="验证码"
            prop="verifyCode"
            label-position="right"
            required
          >
            <el-input
              v-model="recoverForm.verifyCode"
              placeholder="请输入邮箱验证码"
              clearable
            />
          </el-form-item>
          <el-form-item
            label="密码"
            prop="password"
            label-position="right"
            required
          >
            <el-tooltip
              content="密码应该是6-14位的大小写字母和数字的组合"
              placement="right"
              effect="light"
              trigger="click"
            >
              <el-input
                v-model="recoverForm.password"
                placeholder="请输入密码"
                clearable
                type="password"
                show-password
              />
            </el-tooltip>
          </el-form-item>
          <el-form-item
            label="确认密码"
            prop="confirmedPassword"
            label-position="right"
            required
          >
            <el-input
              v-model="recoverForm.confirmedPassword"
              placeholder="请输入确认密码"
              clearable
              type="password"
              show-password
            />
          </el-form-item>
        </el-form>
        <div class="login-tools">
          <el-button type="info" @click="backToLastStep">上一步</el-button>
          <el-button
            type="primary"
            @click="confirmChangePassword(recoverFormRef2)"
            >确认修改</el-button
          >
        </div>
      </div>
    </el-card>
  </div>
</template>

<script lang="ts">
export default {
  name: "Recover",
};
</script>

<script setup lang="ts">
import { reactive, ref } from "vue";
import type { FormInstance, FormRules } from "element-plus";
import { useRouter } from "vue-router";
import { LoginService } from "../service/login-servive";
import { useUserInofStore } from "../../init-page/store/userInfo";

const isFormShow = ref(true);
const loginService = new LoginService();
const userStore = useUserInofStore();
const router = useRouter();

const recoverForm = ref({
  username: "",
  verifyCode: "",
  password: "",
  confirmedPassword: "",
});

function sendRecoverMessage(recoverFormRef: FormInstance | undefined) {
  if (!recoverFormRef) return;
  recoverFormRef.validate(async (valid) => {
    if (valid) {
      isFormShow.value = false;
      recoverForm.value.verifyCode = "";
      recoverForm.value.password = "";
      recoverForm.value.confirmedPassword = "";
      await loginService.sendVerifyCode(recoverForm.value.username, "recover");
    }
  });
}

function backToLastStep() {
  isFormShow.value = true;
  recoverForm.value.username = "";
}

function confirmChangePassword(recoverFormRef: FormInstance | undefined) {
  if (!recoverFormRef) return;
  recoverFormRef.validate(async (valid) => {
    if (valid) {
      const res = await loginService.userRecover(
        recoverForm.value.username,
        recoverForm.value.verifyCode,
        recoverForm.value.password,
      );
      if (!("message" in res)) {
        localStorage.setItem(userStore.getStorageName, res.access_token);
        router.push("/home");
      }
    }
  });
}
const recoverFormRef1 = ref<FormInstance>();
const recoverFormRef2 = ref<FormInstance>();
const validUsername = (rule: any, value: any, callback: any) => {
  const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
  if (value === "") {
    callback(new Error("请输入邮箱"));
  } else if (!emailRegex.test(recoverForm.value.username)) {
    callback(new Error("邮箱名称不合法"));
  } else {
    callback();
  }
};
const validVerifyCode = (rule: any, value: any, callback: any) => {
  if (value === "") {
    callback(new Error("请输入邮箱验证码"));
  } else {
    callback();
  }
};
const validatePassword = (rule: any, value: any, callback: any) => {
  const passwordRegex = /^[A-Za-z0-9]{6,14}$/;
  if (value === "") {
    callback(new Error("请输入密码"));
  } else if (!passwordRegex.test(recoverForm.value.password)) {
    callback(new Error("密码必须6-14位且仅由大小写字母和数字组成"));
  } else {
    if (recoverForm.value.confirmedPassword !== "") {
      if (!recoverFormRef2.value) return;
      recoverFormRef2.value.validateField("confirmedPassword");
    }
    callback();
  }
};
const validateConfirmedPassword = (rule: any, value: any, callback: any) => {
  if (value === "") {
    callback(new Error("请输入确认密码"));
  } else if (value !== recoverForm.value.password) {
    callback(new Error("密码和确认密码不同"));
  } else {
    callback();
  }
};
const recoverRules1 = reactive<FormRules<typeof recoverForm>>({
  username: [{ validator: validUsername, trigger: "blur" }],
});
const recoverRules2 = reactive<FormRules<typeof recoverForm>>({
  verifyCode: [{ validator: validVerifyCode, trigger: "blur" }],
  password: [{ validator: validatePassword, trigger: "blur" }],
  confirmedPassword: [
    { validator: validateConfirmedPassword, trigger: "blur" },
  ],
});
</script>

<style scoped lang="scss">
.login-card {
  width: 400px;
  > .el-card {
    border-radius: 12px;
  }
}
</style>
