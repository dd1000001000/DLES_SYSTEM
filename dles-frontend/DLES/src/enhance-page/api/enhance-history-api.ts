import $http from "../../util/request";
import type { addForm, changeForm } from "../type/enhance-history-tree-type";
import type { Dialogue } from "../type/enhance-dialouge-type";
import { v4 as uuidv4 } from "uuid";

export const getEnhanceHistory = async (username: string) => {
  const res = await $http.get(`/enhance/enhance_history/${username}`);
  return res.data;
};

export const getDetailedInfo = async (username: string, nodeId: number) => {
  const res = await $http.get(
    `/enhance/enhance_history/${username}/info/${nodeId}`,
  );
  return res.data;
};

export const addFolder = async (username: string, addForm: addForm) => {
  const res = await $http.post(
    `/enhance/enhance_history/${username}/add`,
    addForm,
  );
  return res.data;
};

export const changeFolderName = async (
  username: string,
  changeForm: changeForm,
) => {
  const res = await $http.post(
    `/enhance/enhance_history/${username}/change`,
    changeForm,
  );
  return res.data;
};

export const deleteFolders = async (
  username: string,
  deleteIds: Array<number>,
) => {
  const res = await $http.post(
    `/enhance/enhance_history/${username}/delete`,
    deleteIds,
  );
  return res.data;
};

export const getCase = async (username: string, nodeId: number) => {
  const res = await $http.get(`enhance/enhance_history/${username}/${nodeId}`);
  return res.data;
};

export const initCase = async (
  username: string,
  faNodeId: number,
  csvFile: File,
) => {
  const formData = new FormData();
  formData.append("csvFile", csvFile);
  const res = await $http.post(
    `/enhance/enhance_history/${username}/init/${faNodeId}`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } },
  );
  return res.data;
};

export const excuteEnhance = async (
  username: string,
  enhanceId: number,
  dialogues: Dialogue[],
) => {
  const res = await $http.post(
    `/enhance/enhance_main/${username}/${enhanceId}`,
    dialogues,
  );
  return res.data;
};

export const downloadCsv = async (username: string, enhanceId: number) => {
  const res = await $http({
    method: "get",
    url: `/enhance/enhance_history/download/${username}/${enhanceId}`,
    responseType: "blob",
  });
  let filename = uuidv4() + ".csv";
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
  return res.data;
};
