import $http from "../../../util/request";
import type { DeleteForm, EvaluateParas } from "../type/train-type";

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
  const formData = new FormData();
  formData.append("csvFile", csvFile);
  const res = await $http.post(`/train/temp_file/upload_csv/${uuid}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};
