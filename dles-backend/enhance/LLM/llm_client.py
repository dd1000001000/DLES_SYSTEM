# -*- coding: utf-8 -*-
import ipaddress
import json
import os
import socket
from dataclasses import dataclass
from typing import List, Dict, Optional
from urllib.parse import urlparse

import httpx
import openai
from openai import OpenAI


class LLMNotConfiguredError(Exception):
    pass


class LLMError(Exception):
    pass


@dataclass
class LLMConfig:
    """用户自己配置的、兼容 OpenAI 接口的模型服务"""
    base_url: str
    api_key: str
    chat_model: str
    strategy_model: str = ''
    code_model: str = ''

    @property
    def extraction_model(self) -> str:
        return self.chat_model

    @property
    def strategy_model_or_default(self) -> str:
        return self.strategy_model or self.chat_model

    @property
    def code_model_or_default(self) -> str:
        return self.code_model or self.chat_model


def allow_private_endpoints() -> bool:
    return os.getenv('DLES_ALLOW_PRIVATE_LLM_ENDPOINTS', '0') == '1'


def validate_base_url(url: str) -> str:
    """
    校验并规范化用户填写的模型端点。
    后端会替用户向这个地址发请求，如果不加限制，可以被用来探测或攻击服务器所在内网（SSRF），
    所以默认只允许解析到公网地址的端点；本地部署（Ollama、vLLM 等）需要设置 DLES_ALLOW_PRIVATE_LLM_ENDPOINTS=1。
    """
    url = (url or '').strip()
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ValueError('模型端点必须是以 http:// 或 https:// 开头的地址')
    if parsed.username or parsed.password:
        raise ValueError('模型端点里不能包含用户名和密码')
    if not allow_private_endpoints():
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        try:
            addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)}
        except socket.gaierror:
            raise ValueError('无法解析模型端点的域名，请检查地址是否正确')
        for address in addresses:
            if not ipaddress.ip_address(address.split('%')[0]).is_global:
                raise ValueError('模型端点指向内网或本机地址，服务器未允许使用这类地址')
    return url.rstrip('/')


def parse_json_output(text: str):
    """解析大模型返回的 JSON；有的模型会用 ```json 代码块包起来，或在前后多说几句话"""
    text = (text or '').strip()
    if text.startswith('```'):
        lines = text.split('\n')
        lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find('{'), text.rfind('}')
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise LLMError('模型没有按要求返回 JSON，请换一个更强的模型或重试')


class LLMClient:
    def __init__(self, config: LLMConfig, model_name: Optional[str] = None):
        self.config = config
        self.model_name = model_name or config.chat_model
        base_url = validate_base_url(config.base_url)
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=base_url,
            max_retries=1,
            # 不跟随重定向：否则校验过的公网地址可以 302 到内网地址
            http_client=httpx.Client(follow_redirects=False, timeout=httpx.Timeout(600.0, connect=10.0)),
        )

    def _create(self, messages: List[Dict], output_json: bool, max_tokens: Optional[int]):
        params = {'model': self.model_name, 'messages': messages}
        if max_tokens:
            params['max_tokens'] = max_tokens
        try:
            if output_json:
                try:
                    return self.client.chat.completions.create(**params, response_format={"type": "json_object"})
                except openai.BadRequestError:
                    # 有的服务不支持 response_format，提示词里已经要求输出 JSON，去掉参数再试一次
                    pass
            return self.client.chat.completions.create(**params)
        except openai.AuthenticationError:
            raise LLMError('API Key 无效或没有权限，请检查设置中的模型配置')
        except openai.PermissionDeniedError:
            raise LLMError('API Key 没有访问该模型的权限')
        except openai.NotFoundError:
            raise LLMError(f'模型端点或模型名称不存在（模型：{self.model_name}），请检查设置中的模型配置')
        except openai.RateLimitError:
            raise LLMError('模型服务返回请求过多或额度不足，请稍后再试')
        except openai.APITimeoutError:
            raise LLMError('请求模型服务超时')
        except openai.APIConnectionError:
            raise LLMError('无法连接到模型端点，请检查地址是否正确')
        except openai.APIStatusError as e:
            raise LLMError(f'模型服务返回错误（HTTP {e.status_code}）：{str(e.message)[:200]}')

    @staticmethod
    def _content(completion) -> str:
        if not completion.choices or completion.choices[0].message.content is None:
            raise LLMError('模型没有返回内容')
        return completion.choices[0].message.content

    def ask_one(self, prompt: str, user_input: str, output_json=True, max_tokens: Optional[int] = None):
        message = [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': user_input}]
        completion = self._create(message, output_json, max_tokens)
        assistant_output = self._content(completion)
        message.append({'role': 'assistant', 'content': assistant_output})
        return assistant_output, message, completion.model_dump()

    def long_chat(self, chat_history: List[Dict], user_input, output_json=True):
        # 历史里助手的回复可能是解析好的 JSON 对象；必须序列化成 JSON，而不是 str()（那样是单引号的 Python 写法，
        # 模型会跟着输出单引号，之后 json.loads 就解析不了）
        def as_text(content) -> str:
            return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)

        history = [{'role': h['role'], 'content': as_text(h['content'])} for h in chat_history]
        history.append({'role': 'user', 'content': as_text(user_input)})
        completion = self._create(history, output_json, None)
        assistant_output = self._content(completion)
        history.append({'role': 'assistant', 'content': assistant_output})
        return assistant_output, history, completion.model_dump()
