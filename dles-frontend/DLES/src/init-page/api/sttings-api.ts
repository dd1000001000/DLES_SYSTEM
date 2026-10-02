import $http from "../../util/request";
import type { changePassword } from "../type/settings-type";

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
