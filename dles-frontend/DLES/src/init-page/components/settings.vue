<template>
  <div style="height: 100%">
    <el-card style="max-height: 99%" shadow="hover">
      <template #header>
        <div class="card-header">
          <h2>设置</h2>
        </div>
      </template>
      <el-container>
        <el-aside width="200px">
          <el-anchor
            :container="anchorContainerRef"
            :offset="30"
            @click="handleClick"
          >
            <el-anchor-link href="#changePassword" title="修改密码" />
            <el-anchor-link href="#changeAvatar" title="修改头像" />
            <el-anchor-link href="#llmConfig" title="模型配置" />
            <el-anchor-link href="#back" title="返回" />
          </el-anchor>
        </el-aside>
        <el-main style="max-height: calc(100vh - 120px)">
          <div
            class="main-setting-page"
            ref="anchorContainerRef"
            style="height: calc(100%); overflow-y: auto"
          >
            <div id="changePassword" class="changePassword">
              <el-form
                ref="changePasswordFormRef"
                label-width="auto"
                :model="changePasswordForm"
                :rules="recoverRules"
              >
                <el-form-item label="旧密码" label-position="right" required>
                  <el-input
                    v-model="changePasswordForm.oldPassword"
                    placeholder="请输入旧密码"
                    clearable
                    type="password"
                    show-password
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
                      v-model="changePasswordForm.password"
                      placeholder="请输入密码"
                      clearable
                      type="password"
                      show-password
                  /></el-tooltip>
                </el-form-item>
                <el-form-item
                  label="确认密码"
                  prop="confirmedPassword"
                  label-position="right"
                  required
                >
                  <el-input
                    v-model="changePasswordForm.confirmedPassword"
                    placeholder="请输入确认密码"
                    clearable
                    type="password"
                    show-password
                  />
                </el-form-item>
              </el-form>
              <el-button
                type="primary"
                @click="changePasswordManully(changePasswordFormRef)"
              >
                确认修改
              </el-button>
            </div>
            <el-divider />
            <div id="changeAvatar">
              <el-upload
                class="avatar-uploader"
                action
                :show-file-list="false"
                :before-upload="beforeAvatarUpload"
              >
                <el-image
                  v-if="avatarUrl"
                  style="width: 256px; height: 256px"
                  :src="avatarUrl"
                  fit="fill"
                />
                <el-icon v-else class="avatar-uploader-icon"><Plus /></el-icon>
              </el-upload>
              <br />
              <el-button
                :disabled="avatarUrl == null"
                type="primary"
                @click="uploadAvatar"
              >
                修改头像
              </el-button>
            </div>
            <el-divider />
            <div id="llmConfig" class="llm-config">
              <el-alert
                type="info"
                :closable="false"
                show-icon
                title="表格增强和 AI 写代码会使用这里配置的模型。支持任何兼容 OpenAI 接口的服务（OpenAI、阿里云百炼、DeepSeek、Ollama 等）。"
                style="margin-bottom: 16px"
              />
              <el-form :model="llmForm" label-width="110px">
                <el-form-item label="模型端点" required>
                  <el-input
                    v-model="llmForm.base_url"
                    placeholder="例如 https://api.openai.com/v1"
                    clearable
                  />
                </el-form-item>
                <el-form-item label="API Key" required>
                  <el-input
                    v-model="llmForm.api_key"
                    :placeholder="
                      llmConfigured
                        ? `已保存（${llmKeyMasked}），留空则不修改`
                        : '请输入 API Key'
                    "
                    type="password"
                    show-password
                    autocomplete="off"
                  />
                </el-form-item>
                <el-form-item label="模型名称" required>
                  <el-input
                    v-model="llmForm.chat_model"
                    placeholder="例如 gpt-4o-mini、qwen-plus"
                    clearable
                  />
                </el-form-item>
                <el-form-item label="策略模型">
                  <el-input
                    v-model="llmForm.strategy_model"
                    placeholder="可选，用于生成表格增强策略，留空则使用上面的模型"
                    clearable
                  />
                </el-form-item>
                <el-form-item label="代码模型">
                  <el-input
                    v-model="llmForm.code_model"
                    placeholder="可选，用于 AI 写代码，留空则使用上面的模型"
                    clearable
                  />
                </el-form-item>
              </el-form>
              <el-button
                type="primary"
                :loading="llmSaving"
                @click="saveLLMConfig"
              >
                保存
              </el-button>
              <el-button :loading="llmTesting" @click="testLLMConfig">
                测试连接
              </el-button>
            </div>
            <el-divider />
            <div id="back">
              <el-button type="primary" @click="router.push('/home')">
                返回主页
              </el-button>
              <el-button type="info" @click="router.back()"> 返回 </el-button>
            </div>
          </div>
        </el-main>
      </el-container>
    </el-card>
  </div>
</template>

<script lang="ts">
export default {
  name: "Settings",
};
</script>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import {
  ElMessage,
  type FormRules,
  type FormInstance,
  type UploadRawFile,
} from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import type { UploadProps } from "element-plus";
import { SettingsService } from "../service/settings-service";
import { useUserInofStore } from "../store/userInfo";

const router = useRouter();
const anchorContainerRef = ref<HTMLElement | null>(null);
const handleClick = (e: MouseEvent) => {
  e.preventDefault();
};
const changePasswordForm = ref({
  oldPassword: "",
  password: "",
  confirmedPassword: "",
});
const settingsService = new SettingsService();
const userStore = useUserInofStore();
const changePasswordFormRef = ref<FormInstance>();
const validatePassword = (_rule: any, value: any, callback: any) => {
  const passwordRegex = /^[A-Za-z0-9]{6,14}$/;
  if (value === "") {
    callback(new Error("请输入密码"));
  } else if (!passwordRegex.test(changePasswordForm.value.password)) {
    callback(new Error("密码必须6-14位且仅由大小写字母和数字组成"));
  } else {
    if (changePasswordForm.value.confirmedPassword !== "") {
      if (!changePasswordFormRef.value) return;
      changePasswordFormRef.value.validateField("confirmedPassword");
    }
    callback();
  }
};
const validateConfirmedPassword = (_rule: any, value: any, callback: any) => {
  if (value === "") {
    callback(new Error("请输入确认密码"));
  } else if (value !== changePasswordForm.value.password) {
    callback(new Error("密码和确认密码不同"));
  } else {
    callback();
  }
};
const recoverRules = reactive<FormRules<typeof changePasswordForm>>({
  password: [{ validator: validatePassword, trigger: "blur" }],
  confirmedPassword: [
    { validator: validateConfirmedPassword, trigger: "blur" },
  ],
});
function changePasswordManully(
  changePasswordFormRef: FormInstance | undefined,
) {
  if (!changePasswordFormRef) return;
  changePasswordFormRef.validate(async (valid) => {
    if (valid) {
      const res = await settingsService.changePassowrd(
        changePasswordForm.value.oldPassword,
        changePasswordForm.value.password,
      );
      if (!("message" in res)) {
        ElMessage.success("修改密码成功！");
        changePasswordForm.value.oldPassword = "";
        changePasswordForm.value.password = "";
        changePasswordForm.value.confirmedPassword = "";
      }
    }
  });
}

const llmForm = ref({
  base_url: "",
  api_key: "",
  chat_model: "",
  strategy_model: "",
  code_model: "",
});
const llmConfigured = ref(false);
const llmKeyMasked = ref("");
const llmSaving = ref(false);
const llmTesting = ref(false);

function applyLLMConfig(res: any) {
  llmConfigured.value = res.configured;
  llmKeyMasked.value = res.api_key_masked;
  llmForm.value = {
    base_url: res.base_url,
    api_key: "",
    chat_model: res.chat_model,
    strategy_model: res.strategy_model,
    code_model: res.code_model,
  };
}
onMounted(async () => {
  const res = await settingsService.getLLMConfig();
  if (!("message" in res)) applyLLMConfig(res);
});
async function saveLLMConfig() {
  llmSaving.value = true;
  try {
    const res = await settingsService.saveLLMConfig(llmForm.value);
    if (!("message" in res)) {
      applyLLMConfig(res);
      ElMessage.success("保存模型配置成功！");
    }
  } finally {
    llmSaving.value = false;
  }
}
async function testLLMConfig() {
  llmTesting.value = true;
  try {
    const res = await settingsService.testLLMConfig(llmForm.value);
    if (!("message" in res)) {
      ElMessage.success(`连接成功，模型回复：${res.reply}`);
    }
  } finally {
    llmTesting.value = false;
  }
}

const avatarFile = ref<UploadRawFile | null>(null);
const avatarUrl = ref<string | null>(null);

const beforeAvatarUpload: UploadProps["beforeUpload"] = (rawFile) => {
  if (rawFile.type !== "image/jpeg" && rawFile.type !== "image/png") {
    ElMessage.error("头像必须是jpg格式或者是png格式！");
    return false;
  } else if (rawFile.size / 1024 / 1024 > 10) {
    ElMessage.error("头像大小不能超过10MB！");
    return false;
  }
  avatarFile.value = rawFile;
  avatarUrl.value = URL.createObjectURL(rawFile);
  return true;
};
async function uploadAvatar() {
  if (avatarFile.value) {
    const avatar: File =
      avatarFile.value instanceof File
        ? avatarFile.value
        : new File([avatarFile.value], avatarFile.value.name, {
            type: avatarFile.value.type,
          });
    const res = await settingsService.uploadAvatar(avatar);
    if (!("message" in res)) {
      userStore.setAvatar(res.avatar_path);
      ElMessage.success("修改头像成功！");
      avatarFile.value = null;
      avatarUrl.value = null;
    }
  }
}
</script>

<style scoped lang="scss">
.main-setting-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  > .changePassword {
    width: 300px;
  }
  > .llm-config {
    width: 600px;
  }
}

.avatar-uploader {
  width: 256px;
  height: 256px;
  border: 1px dashed var(--el-border-color);
  .el-icon.avatar-uploader-icon {
    font-size: 28px;
    color: #8c939d;
    width: 256px;
    height: 256px;
    text-align: center;
  }
}
.avatar-uploader:hover {
  border-color: var(--el-color-primary);
}

.el-card {
  ::v-deep.el-card__body {
    height: 100%;
  }
}
</style>
