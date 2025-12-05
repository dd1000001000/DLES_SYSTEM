import axios from "axios";
import $http from "../../util/request";
import type {
  SendEmail,
  UserRegister,
  UserLogin,
  UserRecover,
} from "../type/login-type";
import { stringify } from "../../util/stingfy";
import { ElMessage } from "element-plus";

export const sendVerifyCode = async (form: SendEmail) => {
  const res = await $http.post("/login/send_verify_code", form);
  return res.data;
};

export const userRegister = async (form: UserRegister) => {
  const res = await $http.post("/login/register", form);
  return res.data;
};

export const userRecover = async (form: UserRecover) => {
  const res = await $http.post("/login/recover", form);
  return res.data;
};

export const userInfo = async () => {
  const res = await $http.post("/login/user/me");
  return res.data;
};

export const userLogin = async (form: UserLogin) => {
  try {
    const res = await axios({
      method: "post",
      url: "http://127.0.0.1:8080/login/login",
      data: {
        username: form.username,
        password: form.password,
      },
      transformRequest: [
        function (data) {
          return stringify(data);
        },
      ],
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });
    return res.data;
  } catch (e) {
    ElMessage.warning((e as any).response.data.detail);
    return { message: (e as any).response.data.detail };
  }
};
