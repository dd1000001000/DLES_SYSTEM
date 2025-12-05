import {
  sendVerifyCode,
  userRegister,
  userLogin,
  userInfo,
  userRecover,
} from "../api/login-api";

export class LoginService {
  async sendVerifyCode(email: string, type: "register" | "recover") {
    const res = await sendVerifyCode({ email: email, type: type });
  }
  async userRegister(email: string, verify_code: string, password: string) {
    const res = await userRegister({
      email: email,
      verify_code: verify_code,
      password: password,
    });
    return res;
  }
  async userLogin(username: string, password: string) {
    const res = await userLogin({ username: username, password: password });
    return res;
  }
  async getUserInfo() {
    const res = await userInfo();
    return res;
  }
  async userRecover(email: string, verify_code: string, new_password: string) {
    const res = await userRecover({
      email: email,
      verify_code: verify_code,
      new_password: new_password,
    });
    return res;
  }
}
