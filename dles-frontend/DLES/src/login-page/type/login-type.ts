export interface SendEmail {
  email: string;
  type: "register" | "recover";
}

export interface UserLogin {
  username: string;
  password: string;
}

export interface UserRegister {
  email: string;
  verify_code: string;
  password: string;
}

export interface UserRecover {
  email: string;
  verify_code: string;
  new_password: string;
}
