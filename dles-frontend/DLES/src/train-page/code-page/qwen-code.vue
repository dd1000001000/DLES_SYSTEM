<template>
  <div>
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <el-button
            type="info"
            round
            :icon="Back"
            style="float: left; margin-left: 10px"
            @click="router.push('/train')"
          />
          <img
            src="https://cdn.luogu.com.cn/upload/image_hosting/uk25g5j9.png"
            height="30"
            style="display: inline-block; vertical-align: middle"
          />
          <h3
            style="
              display: inline-block;
              margin: 0 0 0 10px;
              vertical-align: middle;
            "
          >
            AI帮写
          </h3>
        </div>
      </template>
      <div class="code-tool">
        <el-button-group class="button-group">
          <el-button
            size="small"
            type="primary"
            :icon="CopyDocument"
            @click="copyToClipboard(codeText)"
          />
          <el-button
            size="small"
            :type="isUserInputShow ? 'danger' : 'success'"
            :icon="isUserInputShow ? 'Close' : 'ChatDotRound'"
            @click="isUserInputShow = !isUserInputShow"
          />
        </el-button-group>
      </div>
      <div class="code-container">
        <textarea
          v-if="isEdit"
          ref="codeEditor"
          v-model="codeText"
          class="code-editor"
          placeholder="请输入代码，AI生成的代码也会在此显示。"
          @blur="isEdit = false"
          style="resize: none"
        />
        <!-- pre 标签和内容内不能有回车 -->
        <pre
          v-else
          class="code-display"
          @click="changeEditState"
        ><code class="language-javascript" v-html="highlightedCode"/>
        </pre>
      </div>
    </el-card>
    <div v-if="isUserInputShow" class="user-input">
      <el-card class="input-card" body-class="input-inner" shadow="hover">
        <el-input
          ref="userInputRef"
          v-model="userInput"
          :autosize="{ minRows: 2, maxRows: 4 }"
          type="textarea"
          placeholder="请输入您的代码编写要求。"
          resize="none"
        />
        <div class="tools-bar">
          <el-button
            class="submit-button"
            type="info"
            circle
            :icon="Top"
            :loading="buttonLoading"
            :disabled="userInput.trim() === ''"
            @click="generateCode"
          />
        </div>
      </el-card>
      <div style="font-size: 12px; color: red">内容由AI生成，请谨慎甄别</div>
    </div>
  </div>
</template>

<script lang="ts">
export default {
  name: "QwenCode",
};
</script>

<script lang="ts" setup>
import { ref, computed, onMounted, nextTick } from "vue";
import {
  Top,
  CopyDocument,
  Back,
  Close,
  ChatDotRound,
} from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { CodeService } from "./service/code-service";
import { useRouter } from "vue-router";
import hljs from "highlight.js";
import "highlight.js/styles/github.css";

const router = useRouter();
const codeService = new CodeService();

const userInput = ref("");
const codeText = ref("");
const isEdit = ref(false);
const buttonLoading = ref(false);
const isUserInputShow = ref(true);
const codeEditor = ref<HTMLTextAreaElement | null>(null);

// 计算属性，返回高亮后的代码
const highlightedCode = computed(() => {
  if (!codeText.value.trim()) return "请输入代码，AI生成的代码也会在此显示。";
  try {
    return hljs.highlight(codeText.value, { language: "javascript" }).value;
  } catch (e) {
    return codeText.value;
  }
});

async function generateCode() {
  buttonLoading.value = true;
  const userInputCopy = userInput.value;
  userInput.value = "";
  const res = await codeService.generateCode(codeText.value, userInputCopy);
  if (!("message" in res)) {
    codeText.value = res["code"];
    buttonLoading.value = false;
    ElMessage({
      message: "AI帮写代码生成成功",
      type: "success",
    });
  } else {
    buttonLoading.value = false;
  }
}

function changeEditState() {
  isEdit.value = !isEdit.value;
  if (isEdit.value) {
    nextTick(() => {
      codeEditor.value?.focus();
    });
  }
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage({
      message: "复制代码到剪贴板成功",
      type: "success",
    });
  } catch (err) {
    ElMessage({
      message: "复制代码到剪贴板失败",
      type: "error",
    });
  }
}
</script>

<style scoped lang="scss">
.code-tool {
  .button-group {
    margin-left: calc(99% - 80px);
  }
}

.main-card {
  background-color: rgb(250, 250, 250);

  .code-container {
    margin-top: 10px;
    height: calc(100vh - 250px);
    position: relative;
    text-align: left;
    margin-right: 20px;

    .code-editor,
    .code-display {
      width: 100%;
      height: 100%;
      padding: 10px;
      font-size: 14px;
      line-height: 1.5;
      border: 1px solid #ddd;
      border-radius: 4px;
      background-color: #f8f8f8;
      white-space: pre;
      overflow: auto;
    }

    .code-display {
      cursor: pointer;
      &:hover {
        background-color: #f0f0f0;
      }
    }

    pre {
      margin: 0;
    }
  }

  ::v-deep .el-card__header {
    padding: 10px;
  }
  ::v-deep .el-card__body {
    padding: 10px 20px 0px 20px;
    height: calc(100vh - 185px);
  }
}

.user-input {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-40%);
  display: flex;
  flex-direction: column;
  align-items: center;
  .input-card {
    border-radius: 20px;
    width: 780px;
    ::v-deep .input-inner {
      padding: 0;
      .tools-bar {
        display: flex;
        flex-direction: row;
        margin-bottom: 10px;
        .submit-button {
          margin-left: auto;
          margin-right: 15px;
        }
      }
    }
    ::v-deep .el-textarea__inner {
      word-break: break-all;
      font-size: 16px;
      box-shadow: none;
    }
  }
}
</style>
