<template>
  <div v-if="tableChose" class="table-area">
    <el-table :data="tableData" border style="width: 100%">
      <el-table-column
        v-for="index in tableKeys.length"
        :key="index"
        :prop="tableKeys[index - 1]"
        :label="tableKeys[index - 1]"
        min-width="150"
      />
    </el-table>
  </div>
  <div v-else style="height: calc(100vh - 110px)">
    <el-empty description="您还没上传表格" />
  </div>
</template>

<script lang="ts">
export default {
  name: "EnhanceMain",
};
</script>

<script setup lang="ts">
import { ref, watch, type Ref } from "vue";

const tableKeys: Ref<string[]> = ref([]);
function getTableKeys() {
  if (tableData.value.length === 0) return;
  const keys = Object.keys(tableData.value[0]);
  tableKeys.value = keys;
}

const props = defineProps<{
  tableData: object[];
  tableChose: boolean;
}>();

const emit = defineEmits(["update:tableData", "update:tableChose"]);

const tableData: Ref<object[]> = ref([]);

watch(
  () => props.tableData,
  (newVal) => {
    tableData.value = newVal;
    getTableKeys();
  },
);

watch(
  () => tableData.value,
  (newVal) => {
    emit("update:tableData", newVal);
  },
);
</script>

<style scoped lang="scss">
.table-area {
  height: calc(100vh - 110px);
  margin-left: 30px;
  display: flex;
  flex-direction: column;
}
</style>
