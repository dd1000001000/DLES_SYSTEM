<template>
  <div>
    <el-container style="position: relative">
      <el-button
        class="fold-button"
        :style="{
          position: 'absolute',
          top: '50%',
          left: isHistoryPageShow ? '250px' : '0px',
          transform: `translateX(${isHistoryPageShow ? '95%' : '0'})`,
        }"
        @click="isHistoryPageShow = !isHistoryPageShow"
        :icon="isHistoryPageShow ? ArrowLeft : ArrowRight"
      />
      <el-main style="padding: 0; margin-right: 10px">
        <el-card class="main-card">
          <el-container>
            <el-aside
              v-if="isHistoryPageShow"
              width="250px"
              style="margin-left: 20px; margin-top: 20px"
            >
              <historyTree />
            </el-aside>
            <el-main style="padding: 0; background-color: rgb(245, 245, 245)">
              <enhanceMain
                v-model:tableChose="tableChose"
                v-model:tableData="tableData"
              />
            </el-main>
          </el-container>
        </el-card>
      </el-main>
      <el-aside width="350px">
        <enhanceDialouge
          v-model:dialogue="dialogue"
          v-model:tableChose="tableChose"
        />
      </el-aside>
    </el-container>
  </div>
</template>

<script lang="ts">
export default {
  name: "Enhance",
};
</script>

<script setup lang="ts">
import { ArrowLeft, ArrowRight } from "@element-plus/icons-vue";
import { computed, ref, watch, type Ref } from "vue";
import enhanceMain from "./component/enhance-main.vue";
import enhanceDialouge from "./component/enhance-dialogue.vue";
import historyTree from "./component/history-tree.vue";
import { useRoute, useRouter } from "vue-router";
import type { Dialogue } from "./type/enhance-dialouge-type";
import { EnhanceHistoryService } from "./service/enhance-history-service";
import { useUserInofStore } from "../init-page/store/userInfo";

const enhanceHistoryService = new EnhanceHistoryService();
const userStore = useUserInofStore();
const route = useRoute();
const router = useRouter();
const id = computed(() => route.params.id);
const tableData = ref([]);
const dialogue: Ref<Dialogue[]> = ref([]);
const tableChose = ref(false);

watch(
  () => id.value,
  async (newVal) => {
    const isIdValid = /^\d+$/.test(newVal as string);
    if (isIdValid) {
      setTimeout(async () => {
        const res = await enhanceHistoryService.getCase(
          userStore.getUserName,
          Number(newVal),
        );
        if (!("message" in res)) {
          tableData.value = res.table;
          dialogue.value = res.dialogue;
          tableChose.value = true;
        } else {
          router.push(`/enhance`);
          tableChose.value = false;
        }
      }, 1000);
    } else {
      router.push(`/enhance`);
      tableChose.value = false;
      tableData.value = [];
      dialogue.value = [];
    }
  },
  { immediate: true },
);

const isHistoryPageShow = ref(true);
</script>

<style scoped lang="scss">
.fold-button {
  padding: 8px 3px 8px 3px;
}
.main-card {
  height: 99.5%;
  ::v-deep .el-card__body {
    padding: 0;
  }
}
</style>
