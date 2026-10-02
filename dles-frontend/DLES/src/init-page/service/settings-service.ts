import {
  uploadAvatar,
  changePassowrd,
  getLLMConfig,
  saveLLMConfig,
  testLLMConfig,
} from "../api/sttings-api";
import type { LLMConfigForm } from "../type/settings-type";

export class SettingsService {
  async uploadAvatar(avatar: File) {
    const res = await uploadAvatar(avatar);
    return res;
  }
  async changePassowrd(old_password: string, new_passowrd: string) {
    const res = await changePassowrd({
      old_password: old_password,
      new_password: new_passowrd,
    });
    return res;
  }
  async getLLMConfig() {
    const res = await getLLMConfig();
    return res;
  }
  async saveLLMConfig(form: LLMConfigForm) {
    const res = await saveLLMConfig(form);
    return res;
  }
  async testLLMConfig(form: LLMConfigForm) {
    const res = await testLLMConfig(form);
    return res;
  }
}
