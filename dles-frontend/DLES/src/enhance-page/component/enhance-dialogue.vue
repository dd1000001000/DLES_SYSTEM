<template>
  <div>
    <el-card class="dialouge-main" body-class="dialouge-main-inner">
      <el-scrollbar height="calc(100% - 130px)">
        <div class="dialouge">
          <div
            v-for="index in dialogue.length"
            :key="index"
            :class="
              dialogue[index - 1].role === 'user'
                ? 'user-message'
                : 'assistant-message'
            "
          >
            <el-avatar
              v-if="dialogue[index - 1].role === 'assistant'"
              src="https://cdn.luogu.com.cn/upload/image_hosting/oihs1yt0.png"
              :size="35"
              fit="contain"
            />
            <el-avatar
              v-else
              :src="
                userInfoStore.avatarUrl
                  ? `http://localhost:8080/avatars/${userInfoStore.avatarUrl}`
                  : 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'
              "
              :size="35"
            />
            <el-card
              class="message-card"
              body-class="message-card-inner"
              shadow="hover"
            >
              {{ dialogue[index - 1].content }}
            </el-card>
          </div>
        </div>
      </el-scrollbar>
      <div class="text-input">
        <el-card shadow="hover" style="border-radius: 10px">
          <el-input
            v-model="userInput"
            :autosize="{ minRows: 2, maxRows: 4 }"
            type="textarea"
            placeholder="请输入您的表格增强要求，如果您需要开始增强表格，请输入“开始增强”。"
            resize="none"
            :disabled="inputDisabled"
          />
          <div class="tools-bar">
            <!-- v-if="empty" -->
            <div class="left-tools-bar">
              <el-tooltip
                content="请在左侧历史记录位置上传或选择表格"
                placement="top-start"
              >
                <el-button v-if="!tableChose" class="tool-button" type="danger">
                  请您上传表格
                  <el-icon><DocumentAdd /></el-icon>
                </el-button>
              </el-tooltip>
              <el-button
                v-if="tableChose"
                class="tool-button"
                type="success"
                @click="
                  enhanceHistoryService.downloadCsv(
                    userInfoStore.getUserName,
                    Number(id),
                  )
                "
              >
                下载当前表格
                <el-icon><DocumentChecked /></el-icon>
              </el-button>
            </div>
            <img
              src="https://cdn.luogu.com.cn/upload/image_hosting/qjymkvv3.png"
              height="30"
              style="display: inline-block; vertical-align: middle"
            />
            <el-button
              class="submit-button"
              type="info"
              circle
              :icon="Top"
              @click="startEnhance"
              :disabled="userInput.trim() === '' || !tableChose"
            />
          </div>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script lang="ts">
export default {
  name: "EnhanceDialogue",
};
</script>

<script setup lang="ts">
import { computed, ref, watch, type Ref } from "vue";
import { MagicStick, Top, DocumentChecked } from "@element-plus/icons-vue";
import type { Dialogue } from "../type/enhance-dialouge-type";
import { useUserInofStore } from "../../init-page/store/userInfo";
import { useRoute } from "vue-router";
import { EnhanceHistoryService } from "../service/enhance-history-service";

const enhanceHistoryService = new EnhanceHistoryService();
const userInfoStore = useUserInofStore();
const route = useRoute();

const id = computed(() => route.params.id);

const props = defineProps<{
  dialogue: Dialogue[];
  tableChose: boolean;
}>();

const emit = defineEmits(["update:dialogue", "update:tableChose"]);

const dialogue: Ref<Dialogue[]> = ref([]);

watch(
  () => props.dialogue,
  (newVal) => {
    dialogue.value = newVal;
  },
);

watch(
  () => dialogue.value,
  (newVal) => {
    emit("update:dialogue", newVal);
  },
);

async function startEnhance() {
  const isIdValid = /^\d+$/.test(id.value as string);
  if (!isIdValid) return;
  dialogue.value.push({ role: "user", content: userInput.value });
  userInput.value = "";
  inputDisabled.value = true;
  const copiedDialogue: Ref<Dialogue[]> = ref([]);
  copiedDialogue.value = JSON.parse(JSON.stringify(dialogue.value));
  dialogue.value.push({ role: "assistant", content: "Qwen 正在思考。。。" });
  const res = await enhanceHistoryService.excuteEnhance(
    userInfoStore.getUserName,
    Number(id.value),
    copiedDialogue.value,
  );
  inputDisabled.value = false;
  if (!("message" in res)) {
    location.reload();
  } else {
    setTimeout(() => {
      location.reload();
    }, 3000);
  }
}

const userInput = ref("");
const inputDisabled = ref(false);
</script>

<style scoped lang="scss">
.dialouge-main {
  .dialouge {
    height: calc(100% - 130px);
    .user-message {
      display: flex;
      flex-direction: row-reverse;
      justify-content: flex-start;
      margin-right: 20px;
      .message-card {
        ::v-deep .message-card-inner {
          background-color: rgb(45, 101, 247);
          color: white;
        }
      }
    }
    .assistant-message {
      display: flex;
      flex-direction: row;
      justify-content: flex-start;
      .message-card {
        ::v-deep .message-card-inner {
          background-color: rgb(240, 240, 240);
        }
      }
    }
    .user-message,
    .assistant-message {
      gap: 5px;
      margin-top: 8px;
      .message-card {
        border-radius: 15px;
        max-width: 225px;
        ::v-deep .message-card-inner {
          padding: 10px;
          word-wrap: break-word;
          word-break: break-word;
          white-space: pre-wrap;
          text-align: left;
        }
      }
    }
  }
  ::v-deep .dialouge-main-inner {
    padding: 10px 0 10px 20px;
    height: calc(100vh - 123px);
  }
  .text-input {
    width: 310px;
    position: absolute;
    bottom: 5px;
    .el-card {
      .tools-bar {
        margin-top: 5px;
        margin-bottom: 5px;
        display: flex;
        flex-direction: row;
        gap: 5px;
        .left-tools-bar {
          display: flex;
          flex-direction: row;
          gap: 5px;
          margin-left: 5px;
        }
        .submit-button {
          margin-left: auto;
          margin-right: 5px;
        }
        .tool-button {
          margin: 0;
          border-radius: 12px;
          padding: 8px;
        }
      }
    }
    ::v-deep .el-card__body {
      padding: 0px;
    }
    ::v-deep .el-textarea__inner {
      box-shadow: none;
    }
  }
}
</style>
