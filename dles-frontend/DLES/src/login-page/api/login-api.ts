import $http from "../../util/request";
import type {
  SendEmail,
  UserRegister,
  UserLogin,
  UserRecover,
} from "../type/login-type";

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

export const userLogout = async () => {
  const res = await $http.post("/login/logout");
  return res.data;
};

export const userInfo = async () => {
  const res = await $http.post("/login/user/me");
  return res.data;
};

export const userLogin = async (form: UserLogin) => {
  const res = await $http.post(
    "/login/login",
    new URLSearchParams({ username: form.username, password: form.password }),
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } },
  );
  return res.data;
};
