import axios from "axios";
import $http from "../../util/request";
import { useUserInofStore } from "../store/userInfo";
import { ElMessage } from "element-plus";
import type { changePassword } from "../type/settings-type";

export const changePassowrd = async (form: changePassword) => {
  const res = await $http.post("/settings/change_password", form);
  return res.data;
};

export const uploadAvatar = async (avatar: File) => {
  try {
    const userStore = useUserInofStore();
    const jwtToken = localStorage.getItem(userStore.getStorageName);
    const formData = new FormData();
    formData.append("avatar", avatar);
    const res = await axios({
      method: "post",
      url: "http://127.0.0.1:8080/settings/upload_avatar",
      data: formData,
      headers: {
        "Content-Type": "multipart/form-data",
        Authorization: `Bearer ${jwtToken}`,
      },
    });
    return res.data;
  } catch (e) {
    ElMessage.warning((e as any).response.data.detail);
    return { message: (e as any).response.data.detail };
  }
};
