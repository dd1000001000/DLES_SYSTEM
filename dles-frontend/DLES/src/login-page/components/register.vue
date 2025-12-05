<template>
  <div class="login-card">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">注册账号</div>
      </template>
      <el-form
        ref="registerFormRef"
        label-width="auto"
        :model="registerForm"
        :rules="registerRules"
      >
        <el-form-item
          label="邮箱"
          prop="username"
          label-position="right"
          required
        >
          <el-input
            v-model="registerForm.username"
            placeholder="请输入邮箱"
            clearable
          />
        </el-form-item>
        <el-form-item
          label="验证码"
          prop="verifyCode"
          label-position="right"
          required
        >
          <el-input
            v-model="registerForm.verifyCode"
            placeholder="请输入邮箱验证码"
            clearable
          >
            <template #append>
              <el-button
                :disabled="isGetCodeButtonDisabled"
                @click="getVerifyCode"
                >{{ buttonText }}</el-button
              >
            </template>
          </el-input>
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
              v-model="registerForm.password"
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
            v-model="registerForm.confirmedPassword"
            placeholder="请输入确认密码"
            clearable
            type="password"
            show-password
          />
        </el-form-item>
      </el-form>
      <div class="login-tools">
        <el-button type="primary" @click="userRegister(registerFormRef)">
          注册
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<script lang="ts">
export default {
  name: "Register",
};
</script>

<script setup lang="ts">
import { reactive, ref } from "vue";
import type { FormInstance, FormRules } from "element-plus";
import { LoginService } from "../service/login-servive";
import { useUserInofStore } from "../../init-page/store/userInfo";
import { useRouter } from "vue-router";
const registerForm = ref({
  username: "",
  verifyCode: "",
  password: "",
  confirmedPassword: "",
});

const loginService = new LoginService();
const userStore = useUserInofStore();
const router = useRouter();

const isGetCodeButtonDisabled = ref(false);
const buttonText = ref("获取验证码");
const registerFormRef = ref<FormInstance>();
function getVerifyCode() {
  registerFormRef.value?.validateField("username", async (valid: boolean) => {
    if (!valid) return;
    isGetCodeButtonDisabled.value = true;
    let countDown = 120;
    buttonText.value = `${countDown}秒后获取`;

    await loginService.sendVerifyCode(registerForm.value.username, "register");

    const timer = setInterval(() => {
      countDown -= 1;
      if (countDown > 0) {
        buttonText.value = `${countDown}秒后获取`;
      } else {
        clearInterval(timer);
        isGetCodeButtonDisabled.value = false;
        buttonText.value = "获取验证码";
      }
    }, 1000);
  });
}
const validUsername = (rule: any, value: any, callback: any) => {
  const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
  if (value === "") {
    callback(new Error("请输入邮箱"));
  } else if (!emailRegex.test(registerForm.value.username)) {
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
  } else if (!passwordRegex.test(registerForm.value.password)) {
    callback(new Error("密码必须6-14位且仅由大小写字母和数字组成"));
  } else {
    if (registerForm.value.confirmedPassword !== "") {
      if (!registerFormRef.value) return;
      registerFormRef.value.validateField("confirmedPassword");
    }
    callback();
  }
};
const validateConfirmedPassword = (rule: any, value: any, callback: any) => {
  if (value === "") {
    callback(new Error("请输入确认密码"));
  } else if (value !== registerForm.value.password) {
    callback(new Error("密码和确认密码不同"));
  } else {
    callback();
  }
};
const registerRules = reactive<FormRules<typeof registerForm>>({
  username: [{ validator: validUsername, trigger: "blur" }],
  verifyCode: [{ validator: validVerifyCode, trigger: "blur" }],
  password: [{ validator: validatePassword, trigger: "blur" }],
  confirmedPassword: [
    { validator: validateConfirmedPassword, trigger: "blur" },
  ],
});
function userRegister(registerFormRef: FormInstance | undefined) {
  if (!registerFormRef) return;
  registerFormRef.validate(async (valid) => {
    if (valid) {
      const res = await loginService.userRegister(
        registerForm.value.username,
        registerForm.value.verifyCode,
        registerForm.value.password,
      );
      if (!("message" in res)) {
        localStorage.setItem(userStore.getStorageName, res.access_token);
        router.push("/home");
      }
    }
  });
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
