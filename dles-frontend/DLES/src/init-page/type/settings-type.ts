export interface LLMConfigForm {
  base_url: string;
  api_key: string; // 留空表示不修改已保存的 Key
  chat_model: string;
  strategy_model: string;
  code_model: string;
}

export interface changePassword {
  old_password: string;
  new_password: string;
}
