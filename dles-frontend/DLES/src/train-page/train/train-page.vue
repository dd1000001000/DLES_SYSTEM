<template>
  <div>
    <el-container>
      <el-main>
        <el-upload
          drag
          action
          :show-file-list="false"
          :before-upload="beforeCsvUpload"
          :http-request="confirmUploadCsv"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">拖拽上传 或者<em>点击上传</em></div>
          <template #tip>
            <div class="el-upload__tip">
              自动上传 csv 文件，最多同时上传 5 个
            </div>
          </template>
        </el-upload>
        <el-card
          class="filename-card"
          body-class="filename-card-inner"
          shadow="hover"
        >
          <template #header>
            <h3>已经上传的文件</h3>
          </template>
          <div v-for="index in csvFileList.length" :key="index">
            <el-container style="margin-top: 10px">
              <el-main
                style="
                  padding: 0;
                  white-space: nowrap;
                  overflow: hidden;
                  text-overflow: ellipsis;
                "
              >
                {{ csvFileList[index - 1] }}
              </el-main>
              <el-aside width="100px">
                <el-popconfirm
                  title="确定要删除这个文件吗"
                  placement="right"
                  confirm-button-text="确定"
                  cancel-button-text="取消"
                  @confirm="deleteCsv(csvFileList[index - 1])"
                >
                  <template #reference>
                    <el-button type="danger" plain size="small">删除</el-button>
                  </template>
                </el-popconfirm>
              </el-aside>
            </el-container>
          </div>
        </el-card>
      </el-main>
      <el-aside width="400px">
        <el-card class="paras-card" body-class="paras-card-inner">
          <template #header>
            <h3>训练参数</h3>
          </template>
          <el-form :model="trainParas" label-width="auto" label-position="left">
            <el-form-item label="训练集比例：">
              <el-input-number
                v-model="trainParas.training_set_percentage"
                :min="0.05"
                :max="0.95"
                :precision="2"
                :step="0.01"
              />
            </el-form-item>
            <el-form-item label="文本特征维度：">
              <el-input-number
                v-model="trainParas.text_features_max"
                :min="50"
                :max="500"
              />
            </el-form-item>
            <el-form-item label="类别粒度：">
              <el-input-number
                v-model="trainParas.target_text_keywords"
                :min="3"
                :max="100"
              />
            </el-form-item>
            <el-form-item label="预测列名称：">
              <el-select
                v-model="trainParas.predict_column"
                placeholder="选择一个预测列"
              >
                <el-option
                  v-for="item in columnList"
                  :key="item"
                  :value="item"
                />
              </el-select>
            </el-form-item>
          </el-form>
          <el-button-group class="button-group">
            <el-popconfirm
              title="确定清空用例吗？"
              placement="bottom-start"
              @confirm="clearCase"
              confirm-button-text="确定"
              cancel-button-text="取消"
            >
              <template #reference>
                <el-button type="danger">
                  清空用例
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>

            <el-button
              type="primary"
              @click="excuteEvaluation"
              :disabled="trainParas.predict_column.trim() === ''"
            >
              开始评估
              <el-icon><VideoPlay /></el-icon>
            </el-button>
          </el-button-group>
        </el-card>
        <!-- 骨架屏假渲染 -->
        <el-card style="margin-top: 20px" @click="wowMagic">
          <el-skeleton v-if="clickCount == 0" animated>
            <template #template>
              <el-skeleton-item
                variant="caption"
                style="width: 360px; height: 200px"
              />
              <el-skeleton-item variant="text" />
            </template>
          </el-skeleton>
          <div v-else>
            <video
              src="https://tc.qdqqd.com/K6DxJA.mp4"
              autoplay
              loop
              muted
              style="width: 100%"
            />
            <h5 class="magic-text">训练参数太少不满意？试试AI帮写吧。</h5>
          </div>
        </el-card>
      </el-aside>
    </el-container>

    <el-dialog
      v-model="isDialogVisible"
      :title="`模型评估结果（${evaluateStrategy}）`"
    >
      <canvas ref="chartRef" height="300px"></canvas>
    </el-dialog>
  </div>
</template>

<script lang="ts">
export default {
  name: "TrainPage",
};
</script>

<script lang="ts" setup>
import {
  onBeforeUnmount,
  onMounted,
  ref,
  type Ref,
  watchEffect,
  nextTick,
  computed,
} from "vue";
import { v4 as uuidv4 } from "uuid";
import { ElMessage, type UploadRawFile, type UploadProps } from "element-plus";
import { useRouter } from "vue-router";
import { TrainService } from "./service/train-service";
import {
  Chart,
  LinearScale,
  BarController,
  BarElement,
  CategoryScale,
} from "chart.js";

Chart.register(LinearScale, BarController, BarElement, CategoryScale);

const strageName = "TRAIN_TEMP_UUID4";
const router = useRouter();
const trainService = new TrainService();

onMounted(async () => {
  const lastUuid = localStorage.getItem(strageName);
  if (lastUuid == null) {
    const uuid = uuidv4();
    localStorage.setItem(strageName, uuid);
    const res = await trainService.getInfo(uuid);
    csvFileList.value = res["filenames"];
    columnList.value = res["columns"];
  } else {
    const uuid = lastUuid;
    localStorage.setItem(strageName, uuid);
    const res = await trainService.getInfo(uuid);
    csvFileList.value = res["filenames"];
    columnList.value = res["columns"];
  }
});

const clickCount = ref(0);
function wowMagic() {
  clickCount.value += 1;
  if (clickCount.value >= 2) {
    router.push("/train/code");
  }
}

const trainParas = ref({
  training_set_percentage: 0.8,
  text_features_max: 100,
  target_text_keywords: 50,
  predict_column: "",
});

const csvFileList: Ref<string[]> = ref([]);
const columnList: Ref<string[]> = ref([]);

async function clearCase() {
  try {
    await updateUUID();
    trainParas.value.training_set_percentage = 0.8;
    trainParas.value.text_features_max = 100;
    trainParas.value.target_text_keywords = 50;
    trainParas.value.predict_column = "";
    ElMessage.success("清空用例成功");
  } catch (e) {}
}

async function updateCase() {
  const uuid = localStorage.getItem(strageName);
  const res = await trainService.getInfo(uuid as string);
  csvFileList.value = res["filenames"];
  columnList.value = res["columns"];
  trainParas.value.predict_column = "";
}

async function updateUUID() {
  try {
    const lastUuid = localStorage.getItem(strageName);
    if (lastUuid != null) {
      const res = await trainService.clearCase(lastUuid);
    }
    const uuid = uuidv4();
    localStorage.setItem(strageName, uuid);
    const res = await trainService.getInfo(uuid);
    csvFileList.value = res["filenames"];
    columnList.value = res["columns"];
  } catch (e) {}
}

const csvFile = ref<UploadRawFile | null>(null);

const beforeCsvUpload: UploadProps["beforeUpload"] = (rawFile) => {
  if (csvFileList.value.length >= 5) {
    ElMessage.error("最多只能同时对比5个文件，请删除文件后再上传新的文件");
    return false;
  }
  if (rawFile.type !== "text/csv") {
    ElMessage.error("文件必须是csv格式！");
    return false;
  }
  csvFile.value = rawFile;
  return true;
};

async function deleteCsv(fileName: string) {
  const uuid = localStorage.getItem(strageName);
  const res = await trainService.deleteCsv(uuid as string, fileName);
  if (!("message" in res)) {
    ElMessage.success("删除文件成功");
    updateCase();
  }
}

async function confirmUploadCsv() {
  if (csvFile.value) {
    const csvfile: File =
      csvFile.value instanceof File
        ? csvFile.value
        : new File([csvFile.value], csvFile.value.name, {
            type: csvFile.value.type,
          });
    const uuid = localStorage.getItem(strageName);
    const res = await trainService.uploadCsv(uuid as string, csvfile);
    if (!("message" in res)) {
      ElMessage.success("上传文件成功");
      csvFile.value = null;
      updateCase();
    }
  }
}

const isDialogVisible = ref(false);

// 均方根误差/F1-score
const evaluateStrategy = ref("");
const chartRef = ref<HTMLCanvasElement | null>(null);
let myChart: Chart | null = null;

// 响应式图表数据
const chartData = ref({
  labels: [],
  datasets: [
    {
      label: "模型评估结果",
      data: [],
      backgroundColor: [
        "rgba(255, 99, 132, 0.2)",
        "rgba(255, 159, 64, 0.2)",
        "rgba(255, 205, 86, 0.2)",
        "rgba(75, 192, 192, 0.2)",
        "rgba(54, 162, 235, 0.2)",
      ],
      borderColor: [
        "rgb(255, 99, 132)",
        "rgb(255, 159, 64)",
        "rgb(255, 205, 86)",
        "rgb(75, 192, 192)",
        "rgb(54, 162, 235)",
      ],
      borderWidth: 1,
    },
  ],
});

const chartConfig = {
  type: "bar" as const,
  data: chartData.value,
  options: {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: {
        type: "linear",
        beginAtZero: true,
        max: null,
      },
      x: {
        type: "category",
      },
    },
  },
};

watchEffect(() => {
  if (isDialogVisible.value) {
    nextTick(() => {
      initChart();
    });
  } else {
    destroyChart();
  }
});

function setConfigMax() {
  const score = chartData.value.datasets[0].data;
  let mx = 0;
  for (const c of score) mx = Math.max(mx, c);
  if (mx > 1.0) {
    chartConfig.options.scales.y.max = null;
  } else {
    (chartConfig.options.scales.y.max as any) = 1.0;
  }
  const tempList: Ref<string[]> = ref([]);
  for (const c of csvFileList.value)
    if (c.length > 7) tempList.value.push(c.substring(0, 7) + "...");
    else tempList.value.push(c);
  (chartData.value.labels as string[]) = tempList.value;
}

function initChart() {
  if (!chartRef.value) return;
  if (myChart) {
    myChart.destroy();
  }
  setConfigMax();
  myChart = new Chart(chartRef.value, chartConfig as any);
}

function destroyChart() {
  if (myChart) {
    myChart.destroy();
    myChart = null;
  }
}

onBeforeUnmount(() => {
  destroyChart();
});

async function excuteEvaluation() {
  try {
    const res = await trainService.evaluateTrain(
      localStorage.getItem(strageName) as string,
      trainParas.value,
    );
    chartData.value.datasets[0].data = res["score"];
    console.log(res["type"]);
    evaluateStrategy.value = res["type"] === "string" ? "F1-Score" : "RMSE";
    isDialogVisible.value = true;
  } catch (error) {
    console.log(error);
  }
}
</script>

<style scoped lang="scss">
.filename-card {
  margin-top: 20px;
  ::v-deep .el-card__header {
    padding: 0;
  }
}
.paras-card {
  ::v-deep .el-card__header {
    padding: 0;
  }
  ::v-deep .paras-card-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
  }
}
.button-group {
  margin-top: 20px;
}
.magic-text {
  margin: 0;
}
</style>
