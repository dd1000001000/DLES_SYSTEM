# -*- coding: utf-8 -*-
import threading

from database.database import Database
from enhance.LLM.llm_client import LLMClient, LLMConfig, LLMNotConfiguredError, validate_base_url
from utils.crypto import decrypt_text, encrypt_text

_table_lock = threading.Lock()
_table_ready = False


def _ensure_table():
    # 已有的数据库升级后不需要手动建表，第一次用到时自动创建
    global _table_ready
    if _table_ready:
        return
    with _table_lock:
        if _table_ready:
            return
        with Database() as db:
            db.execute_update(
                "CREATE TABLE IF NOT EXISTS user_llm_config ("
                " username VARCHAR(255) PRIMARY KEY,"
                " base_url VARCHAR(512) NOT NULL,"
                " api_key_encrypted TEXT NOT NULL,"
                " chat_model VARCHAR(255) NOT NULL,"
                " strategy_model VARCHAR(255) NOT NULL DEFAULT '',"
                " code_model VARCHAR(255) NOT NULL DEFAULT ''"
                ");")
        _table_ready = True


def _load_row(username: str):
    _ensure_table()
    with Database() as db:
        rows = db.execute_query("SELECT * FROM user_llm_config WHERE username=%s;", (username,))
    return rows[0] if rows else None


def get_llm_config(username: str) -> LLMConfig:
    """取出用户保存的模型配置，供各个调用大模型的功能使用"""
    row = _load_row(username)
    if row is None:
        raise LLMNotConfiguredError('还没有配置模型，请先在“设置 → 模型配置”中填写模型端点和 API Key')
    return LLMConfig(
        base_url=row['base_url'],
        api_key=decrypt_text(row['api_key_encrypted']),
        chat_model=row['chat_model'],
        strategy_model=row['strategy_model'],
        code_model=row['code_model'],
    )


def mask_api_key(api_key: str) -> str:
    if len(api_key) <= 10:
        return '*' * len(api_key)
    return f'{api_key[:3]}{"*" * 8}{api_key[-4:]}'


def get_llm_config_view(username: str) -> dict:
    """返回给前端的配置：API Key 只给脱敏后的样子，永远不把明文发回浏览器"""
    row = _load_row(username)
    if row is None:
        return {'configured': False, 'base_url': '', 'api_key_masked': '',
                'chat_model': '', 'strategy_model': '', 'code_model': ''}
    try:
        masked = mask_api_key(decrypt_text(row['api_key_encrypted']))
    except RuntimeError:
        masked = '（需要重新填写）'
    return {'configured': True, 'base_url': row['base_url'], 'api_key_masked': masked,
            'chat_model': row['chat_model'], 'strategy_model': row['strategy_model'],
            'code_model': row['code_model']}


def build_config(username: str, base_url: str, api_key: str, chat_model: str,
                 strategy_model: str, code_model: str) -> LLMConfig:
    """把表单内容整理成配置；api_key 留空表示沿用已保存的"""
    base_url = validate_base_url(base_url)
    if not chat_model.strip():
        raise ValueError('请填写模型名称')
    if not api_key.strip():
        row = _load_row(username)
        if row is None:
            raise ValueError('请填写 API Key')
        api_key = decrypt_text(row['api_key_encrypted'])
    return LLMConfig(base_url=base_url, api_key=api_key.strip(), chat_model=chat_model.strip(),
                     strategy_model=strategy_model.strip(), code_model=code_model.strip())


def save_llm_config(username: str, config: LLMConfig) -> None:
    _ensure_table()
    with Database() as db:
        db.execute_update(
            "INSERT INTO user_llm_config (username, base_url, api_key_encrypted, chat_model, strategy_model, code_model)"
            " VALUES (%s, %s, %s, %s, %s, %s)"
            " ON DUPLICATE KEY UPDATE base_url=VALUES(base_url), api_key_encrypted=VALUES(api_key_encrypted),"
            " chat_model=VALUES(chat_model), strategy_model=VALUES(strategy_model), code_model=VALUES(code_model);",
            (username, config.base_url, encrypt_text(config.api_key), config.chat_model,
             config.strategy_model, config.code_model))


def test_llm_config(config: LLMConfig) -> str:
    """向模型发一个最小的请求，验证端点、Key 和模型名是否可用"""
    client = LLMClient(config, config.chat_model)
    reply, _, _ = client.ask_one('你是一个连通性测试助手。', '请只回复：ok', output_json=False, max_tokens=16)
    return reply.strip()[:100]
