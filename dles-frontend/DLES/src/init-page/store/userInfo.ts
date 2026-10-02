import { defineStore } from "pinia";
import type { userInfo } from "../type/user-type";
export const useUserInofStore = defineStore("userInfo", {
  state: () => ({
    userEmail: "",
    avatarUrl: "",
    userType: "",
  }),
  actions: {
    setUser(userinfo: userInfo) {
      this.userEmail = userinfo.userEmail;
      this.avatarUrl = userinfo.avatarUrl;
      this.userType = userinfo.userType;
    },
    clearUserInfo() {
      this.userEmail = "";
      this.avatarUrl = "";
      this.userType = "";
    },
    setAvatar(avatarPath: string) {
      this.avatarUrl = avatarPath;
    },
  },
  getters: {
    getUserName: (state) => state.userEmail,
    getUserType: (state) => state.userType,
  },
});
