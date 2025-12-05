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
import { reactive, ref } from "vue";
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
const validatePassword = (rule: any, value: any, callback: any) => {
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
const validateConfirmedPassword = (rule: any, value: any, callback: any) => {
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
        localStorage.setItem(userStore.getStorageName, res.access_token);
        ElMessage.success("修改密码成功！");
        changePasswordForm.value.oldPassword = "";
        changePasswordForm.value.password = "";
        changePasswordForm.value.confirmedPassword = "";
      }
    }
  });
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
