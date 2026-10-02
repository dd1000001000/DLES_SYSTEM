import $http from "../../util/request";
import type { changePassword, LLMConfigForm } from "../type/settings-type";

export const changePassowrd = async (form: changePassword) => {
  const res = await $http.post("/settings/change_password", form);
  return res.data;
};

export const uploadAvatar = async (avatar: File) => {
  const formData = new FormData();
  formData.append("avatar", avatar);
  const res = await $http.post("/settings/upload_avatar", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
};

export const getLLMConfig = async () => {
  const res = await $http.get("/settings/llm_config");
  return res.data;
};

export const saveLLMConfig = async (form: LLMConfigForm) => {
  const res = await $http.post("/settings/llm_config", form);
  return res.data;
};

export const testLLMConfig = async (form: LLMConfigForm) => {
  const res = await $http.post("/settings/llm_config/test", form);
  return res.data;
};
