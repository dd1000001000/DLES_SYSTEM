import axios from "axios";
import { ElMessage } from "element-plus";
import router from "../router";
import { useUserInofStore } from "../init-page/store/userInfo";
import { API_BASE_URL } from "./config";

// 创建axios实例
const $http = axios.create({
  baseURL: API_BASE_URL,
  // 登录凭证在 httpOnly Cookie 里，由浏览器自动携带，前端代码读不到
  withCredentials: true,
  timeout: 600000,
  headers: {
    "content-type": "application/json; charset=utf-8",
  },
});

/**
 * 从错误响应中取出可以展示给用户的文字。
 * 后端自己返回的错误是 { message }，FastAPI 抛出的 HTTPException 是 { detail }
 */
export const getErrorMessage = (error: any): string => {
  const data = error?.response?.data;
  if (typeof data === "string" && data) return data;
  if (typeof data?.message === "string") return data.message;
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail)) {
    return data.detail.map((item: any) => item.msg).join("；");
  }
  return error?.message ?? "未知错误";
};

// 响应拦截器：出错时不抛异常，统一返回 { data: { message } }，调用方用 "message" in res 判断
$http.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    return { data: { message: ResponseProcessing(error) } };
  },
);

/**
 * 响应处理，返回要展示给用户的错误信息
 * @param error
 */
const ResponseProcessing = (error: any): string => {
  if (!error.response) {
    const message = "无法连接到服务器，请检查网络或确认后端已启动！";
    ElMessage.error(message);
    return message;
  }
  const serverMessage = getErrorMessage(error);
  switch (error.response.status) {
    case 401: {
      const url: string = error.config?.url ?? "";
      // 登录时密码错误也是 401，直接提示后端给的原因
      if (url.endsWith("/login/login")) {
        ElMessage.warning(serverMessage);
        return serverMessage;
      }
      // 查询当前用户（路由守卫、页面初始化用）返回 401 只说明还没登录，不弹提示，由调用方处理
      if (url.endsWith("/login/user/me")) {
        return "未登录";
      }
      const message = "您的会话已过期，请重新登录！";
      ElMessage.warning(message);
      useUserInofStore().clearUserInfo();
      router.push("/login/login");
      return message;
    }
    case 404:
      ElMessage.warning("接口不存在，请检查接口地址是否正确！");
      return "接口不存在";
    case 500:
      ElMessage.warning("内部服务器错误，请联系系统管理员！");
      return serverMessage;
    default:
      ElMessage.warning(serverMessage);
      return serverMessage;
  }
};

export default $http;
