import axios from "axios";
import { ElMessage } from "element-plus";
import router from "../router";
import { useUserInofStore } from "../init-page/store/userInfo";

// 创建axios实例
const $http = axios.create({
  baseURL: "http://127.0.0.1:8080",
  withCredentials: true,
  timeout: 600000,
  headers: {
    "content-type": "application/json; charset=utf-8",
  },
});

// 请求拦截器
$http.interceptors.request.use(
  (config) => {
    const userInfoStore = useUserInofStore();
    const token = localStorage.getItem(userInfoStore.getStorageName);
    if (token) {
      config.headers["Authorization"] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// 响应拦截器
$http.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    ResponseProcessing(error);
    return {
      data: { message: error.response.data.message },
    };
  },
);

/**
 * 响应处理
 * @param error
 * @returns
 */
const ResponseProcessing = (error: any) => {
  if (error.response) {
    switch (error.response.status) {
      case 401:
        // Token 过期或无效
        ElMessage.warning("您的会话已过期，请重新登录！");
        // 清除失效的 Token
        const userInfoStore = useUserInofStore();
        localStorage.removeItem(userInfoStore.getStorageName);
        // 重定向到登录页面
        router.push("/login/login");
        break;
      case 404:
        ElMessage.warning("接口不存在，请检查接口地址是否正确！");
        break;
      case 500:
        ElMessage.warning("内部服务器错误，请联系系统管理员！");
        break;
      default:
        // 返回接口返回的错误信息
        ElMessage.warning(error.response.data);
        return Promise.reject(error.response.data);
    }
  } else {
    ElMessage.error("遇到跨域错误，请设置代理或者修改后端允许跨域访问！");
  }
};

export default $http;
