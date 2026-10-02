-- Inferred from the SQL statements in the backend code; adjust types if your deployment differs.
CREATE DATABASE IF NOT EXISTS dles_system DEFAULT CHARACTER SET utf8mb4;
USE dles_system;

CREATE TABLE IF NOT EXISTS user (
  username    VARCHAR(255) PRIMARY KEY,
  password    VARCHAR(255) NOT NULL,
  user_type   VARCHAR(32)  NOT NULL DEFAULT 'user',
  avatar_path VARCHAR(255) NULL
);

CREATE TABLE IF NOT EXISTS enhance_history (
  username     VARCHAR(255) PRIMARY KEY,
  history_tree LONGTEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS table_base_info (
  table_id                INT AUTO_INCREMENT PRIMARY KEY,
  table_path              VARCHAR(512) NOT NULL,
  pure_embedding_path     VARCHAR(512) NULL,
  processed_embedding_path VARCHAR(512) NULL
);

-- Per-user model endpoint settings (created automatically on first use if missing).
CREATE TABLE IF NOT EXISTS user_llm_config (
  username          VARCHAR(255) PRIMARY KEY,
  base_url          VARCHAR(512) NOT NULL,
  api_key_encrypted TEXT         NOT NULL,
  chat_model        VARCHAR(255) NOT NULL,
  strategy_model    VARCHAR(255) NOT NULL DEFAULT '',
  code_model        VARCHAR(255) NOT NULL DEFAULT ''
);
