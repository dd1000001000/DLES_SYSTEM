import { uploadAvatar, changePassowrd } from "../api/sttings-api";

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
}
