<template>
  <div>
    <div class="tools-bar">
      <el-input v-model="filterName" placeholder="请输入记录名称" clearable>
        <template #append>
          <el-button
            :icon="Search"
            @click="historyTreeRef?.filter(filterName)"
          />
        </template>
      </el-input>
      <el-popconfirm
        title="你确定要删除所有选中的文件夹/文件（和子文件夹/文件）吗？"
        confirm-button-text="确定"
        cancel-button-text="取消"
        icon-color="red"
        @confirm="batchDelete"
        :icon="InfoFilled"
      >
        <template #reference>
          <el-button type="danger">
            删除
            <el-icon><Delete /> </el-icon>
          </el-button>
        </template>
      </el-popconfirm>
    </div>
    <el-scrollbar height="calc(100vh - 160px)">
      <div class="history-tree">
        <el-tree
          ref="historyTreeRef"
          :data="historyTreeData"
          show-checkbox
          :filter-node-method="filterNode"
          empty-text="没有记录"
          @node-contextmenu="openTreeMenu"
          @node-collapse="closeTreeMenu"
          default-expand-all
          check-strictly
        >
          <template #default="{ node, data }">
            {{ node.label }}
            <el-icon v-if="data.isFile"><Document /></el-icon>
            <el-icon v-else><Folder /></el-icon>
          </template>
        </el-tree>
      </div>
    </el-scrollbar>
    <div v-if="treeMenuState.menuShow" class="tree-menu">
      <el-button-group>
        <el-button
          type="success"
          :icon="Plus"
          size="small"
          :disabled="!treeMenuState.allowAddFolder"
          @click="openAddFolder"
        />
        <el-button
          type="danger"
          :icon="Delete"
          size="small"
          :disabled="!treeMenuState.allowDeleteOrEditname"
          @click="openDeleteFolder"
        />
        <el-button
          type="primary"
          :icon="Edit"
          size="small"
          :disabled="!treeMenuState.allowDeleteOrEditname"
          @click="openEditFolder"
        />
        <!-- <el-button
          type="info"
          :icon="ZoomIn"
          size="small"
          @click="openDetailFolder"
        /> -->
        <el-button
          type="warning"
          :icon="Link"
          size="small"
          :disabled="!treeMenuState.allowAddFolder"
          @click="openUploadFile"
        />
        <el-button
          :icon="DArrowRight"
          size="small"
          :disabled="!treeMenuState.allowContinue"
          @click="gotoCase"
        />
      </el-button-group>
    </div>
    <!-- 添加文件夹 -->
    <el-dialog v-model="isAddFolderDialougeOpen" title="添加文件夹">
      <el-input
        v-model="newFolderName"
        placeholder="请输入新的文件夹名称"
        clearable
      >
        <template #append>
          <el-button :icon="Check" @click="confirmAddFolder" />
        </template>
      </el-input>
    </el-dialog>
    <!-- 删除文件夹 -->
    <el-dialog v-model="isDeleteFolderDialougeOpen" title="删除文件夹">
      <p>你确定要删除该文件夹/文件及其子文件夹/文件吗（不可恢复！）</p>
      <div
        style="
          display: flex;
          flex-direction: row;
          gap: 20px;
          justify-content: center;
        "
      >
        <el-button type="success" @click="confirmDeleteOneFolder">
          确定<el-icon><Check /></el-icon>
        </el-button>
        <el-button type="danger" @click="isDeleteFolderDialougeOpen = false">
          取消
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </el-dialog>
    <!-- 修改文件夹名称 -->
    <el-dialog v-model="isEditFolderDialougeOpen" title="修改文件夹名称">
      <el-input
        v-model="editFolderName"
        placeholder="请输入新的文件夹名称"
        clearable
      >
        <template #append>
          <el-button :icon="Check" @click="confirmEditFolderName" />
        </template>
      </el-input>
    </el-dialog>
    <!-- 用例详细信息 -->
    <el-dialog v-model="isDetailDialougeOpen" title="文件夹/文件详细信息">
      <div style="display: flex; justify-content: center">
        <el-form :model="historyInfo">
          <el-form-item label="名称：">
            {{ historyInfo.name }}
          </el-form-item>
          <el-form-item label="创建时间：">
            {{ historyInfo.createTime }}
          </el-form-item>
          <el-form-item label="更改时间：">
            {{ historyInfo.lastEditTime }}
          </el-form-item>
        </el-form>
      </div>
    </el-dialog>

    <el-dialog v-model="isUploadDialogueVisible" title="上传文件">
      <el-upload
        drag
        action
        :show-file-list="false"
        :before-upload="beforeCsvUpload"
        :http-request="confirmUploadCsv"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽上传 或者 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">自动上传 csv 文件</div>
        </template>
      </el-upload>
    </el-dialog>
  </div>
</template>

<script lang="ts">
export default {
  name: "HistoryTree",
};
</script>

<script setup lang="ts">
//1228280263@qq.com/aaa/bbb/ccc/{dialouge.txt,table.txt}
import { nextTick, onMounted, onUnmounted, ref, type Ref } from "vue";
import {
  Search,
  Plus,
  Delete,
  Edit,
  ZoomIn,
  Check,
  DArrowRight,
  InfoFilled,
  Link,
} from "@element-plus/icons-vue";
import { ElMessage, ElTree, type UploadRawFile } from "element-plus";
import { EnhanceHistoryService } from "../service/enhance-history-service";
import { useUserInofStore } from "../../init-page/store/userInfo";
import { useRouter } from "vue-router";
import type { UploadProps } from "element-plus";

const router = useRouter();
const enhanceHistoryService = new EnhanceHistoryService();
const userStore = useUserInofStore();

onMounted(() => {
  document.addEventListener("click", handleCloseTreeMenu);
  setTimeout(async () => {
    // 延迟 1 秒后执行 确保用户信息加载完成
    const res = await enhanceHistoryService.getEnhanceHistory(
      userStore.getUserName,
    );
    historyTreeData.value.push(res["history_tree"]);
  }, 1000);
});

onUnmounted(() => {
  document.removeEventListener("click", handleCloseTreeMenu);
});

async function updateHistoryTree() {
  const res = await enhanceHistoryService.getEnhanceHistory(
    userStore.getUserName,
  );
  historyTreeData.value[0] = res["history_tree"];
}

const filterName = ref("");
const historyTreeRef = ref<InstanceType<typeof ElTree>>();
const filterNode = (value: string, data: any) => {
  if (!value) return true;
  return data.label.includes(value);
};
const historyTreeData: Ref<Array<any>> = ref([]);
const treeMenuState = ref({
  menuShow: false,
  allowAddFolder: false,
  allowDeleteOrEditname: false,
  allowContinue: false,
  currentNode: null,
});
function handleCloseTreeMenu(event: MouseEvent) {
  const treeMenu = document.querySelector(".tree-menu");
  if (treeMenu && !treeMenu.contains(event.target as Node)) closeTreeMenu();
}
function openTreeMenu(event: any, data: any, node: any, target: any) {
  treeMenuState.value.currentNode = data;
  treeMenuState.value.menuShow = true;
  if (data.isFile) treeMenuState.value.allowAddFolder = false;
  else treeMenuState.value.allowAddFolder = true;
  if (data.disabled) treeMenuState.value.allowDeleteOrEditname = false;
  else treeMenuState.value.allowDeleteOrEditname = true;
  if (data.isFile) treeMenuState.value.allowContinue = true;
  else treeMenuState.value.allowContinue = false;
  nextTick(() => {
    document
      .querySelector(".tree-menu")!
      .setAttribute(
        "style",
        `top:${event.clientY + 10}px;left:${event.clientX + 10}px;`,
      );
  });
}
function closeTreeMenu() {
  // treeMenuState.value.currentNode = null;
  treeMenuState.value.menuShow = false;
}

const isAddFolderDialougeOpen = ref(false);
const newFolderName = ref("");
function openAddFolder() {
  isAddFolderDialougeOpen.value = true;
}
async function confirmAddFolder() {
  if (newFolderName.value.trim().length == 0) return;
  const res = await enhanceHistoryService.addFolder(
    userStore.getUserName,
    (treeMenuState.value.currentNode as any).id,
    newFolderName.value,
  );
  updateHistoryTree();
  newFolderName.value = "";
  isAddFolderDialougeOpen.value = false;
}
const isDeleteFolderDialougeOpen = ref(false);
function openDeleteFolder() {
  isDeleteFolderDialougeOpen.value = true;
}
async function confirmDeleteOneFolder() {
  const res = await enhanceHistoryService.deleteFolders(userStore.getUserName, [
    (treeMenuState.value.currentNode as any).id,
  ]);
  window.location.reload();
  updateHistoryTree();
  isDeleteFolderDialougeOpen.value = false;
}
const isEditFolderDialougeOpen = ref(false);
const editFolderName = ref("");
function openEditFolder() {
  isEditFolderDialougeOpen.value = true;
  editFolderName.value = (treeMenuState.value.currentNode as any).label;
}
async function confirmEditFolderName() {
  if (editFolderName.value.trim().length == 0) return;
  const res = await enhanceHistoryService.changeFolderName(
    userStore.getUserName,
    (treeMenuState.value.currentNode as any).id,
    editFolderName.value,
  );
  updateHistoryTree();
  editFolderName.value = "";
  isEditFolderDialougeOpen.value = false;
}
const isDetailDialougeOpen = ref(false);
const historyInfo = ref({
  name: "",
  createTime: "",
  lastEditTime: "",
});
async function openDetailFolder() {
  const res = await enhanceHistoryService.getDetailedInfo(
    userStore.getUserName,
    (treeMenuState.value.currentNode as any).id,
  );
  historyInfo.value.name = (treeMenuState.value.currentNode as any).label;
  historyInfo.value.createTime = res.info.createTime;
  historyInfo.value.lastEditTime = res.info.lastEditTime;
  isDetailDialougeOpen.value = true;
}

async function batchDelete() {
  const checkedNodes = historyTreeRef.value!.getCheckedNodes(false, false);
  let deleteIds = [];
  for (const node of checkedNodes) deleteIds.push(node.id);
  if (deleteIds.length == 0) return;
  const res = await enhanceHistoryService.deleteFolders(
    userStore.getUserName,
    deleteIds,
  );
  window.location.reload();
  updateHistoryTree();
}

function gotoCase() {
  router.push(`/enhance/${(treeMenuState.value.currentNode as any).id}`);
}

const isUploadDialogueVisible = ref(false);
const csvFile = ref<UploadRawFile | null>(null);
function openUploadFile() {
  isUploadDialogueVisible.value = true;
}

const beforeCsvUpload: UploadProps["beforeUpload"] = (rawFile) => {
  if (rawFile.type !== "text/csv") {
    ElMessage.error("文件必须是csv格式！");
    return false;
  }
  csvFile.value = rawFile;
  return true;
};

async function confirmUploadCsv() {
  if (csvFile.value) {
    const csvfile: File =
      csvFile.value instanceof File
        ? csvFile.value
        : new File([csvFile.value], csvFile.value.name, {
            type: csvFile.value.type,
          });
    const res = await enhanceHistoryService.initCase(
      userStore.getUserName,
      (treeMenuState.value.currentNode as any).id,
      csvfile,
    );
    if (!("message" in res)) {
      ElMessage.success("上传文件成功");
      csvFile.value = null;
      isUploadDialogueVisible.value = false;
      updateHistoryTree();
      router.push(`/enhance/${res.node_id}`);
    }
  }
}
</script>

<style scoped lang="scss">
.tools-bar {
  display: flex;
  flex-direction: row;
}
.history-tree {
  min-width: max-content;
  padding-bottom: 10px;
  padding-right: 10px;
}
.tree-menu {
  position: fixed;
  z-index: 4;
}
</style>
