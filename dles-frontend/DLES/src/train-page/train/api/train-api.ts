import axios from "axios";
import { useUserInofStore } from "../../../init-page/store/userInfo";
import $http from "../../../util/request";
import type { DeleteForm, EvaluateParas } from "../type/train-type";
import { ElMessage } from "element-plus";

export const clearCase = async (uuid: string) => {
  const res = await $http.post(`/train/temp_file/clear_case/${uuid}`);
  return res.data;
};

export const getInfo = async (uuid: string) => {
  const res = await $http.get(`/train/temp_file/${uuid}`);
  return res.data;
};

export const deleteCsv = async (deleteForm: DeleteForm) => {
  const res = await $http.post(`/train/temp_file/delete_csv`, deleteForm);
  return res.data;
};

export const evaluate_train = async (
  uuid: string,
  evaluateParas: EvaluateParas,
) => {
  const res = await $http.post(
    `/train/temp_file/evaluate/${uuid}`,
    evaluateParas,
  );
  return res.data;
};

export const uploadCsv = async (uuid: string, csvFile: File) => {
  try {
    const userStore = useUserInofStore();
    const jwtToken = localStorage.getItem(userStore.getStorageName);
    const formData = new FormData();
    formData.append("csvFile", csvFile);
    const res = await axios({
      method: "post",
      url: `http://127.0.0.1:8080/train/temp_file/upload_csv/${uuid}`,
      data: formData,
      headers: {
        "Content-Type": "multipart/form-data",
        Authorization: `Bearer ${jwtToken}`,
      },
    });
    return res.data;
  } catch (e) {
    ElMessage.warning((e as any).response.data.message);
    return { message: (e as any).response.data.message };
  }
};
