"""
llm_client — OpenAI 兼容协议的 LLM 客户端（使用 requests 库）。

设计原则：
- 仅依赖 requests 库，不引入 openai SDK
- 走标准 OpenAI Chat Completions 协议（POST {api_url}/chat/completions）
- 错误处理：非 200 抛异常带状态码和响应体；超时抛异常
- 默认配置从环境变量读，env 缺失时回退到硬编码默认值

用法：
    from dg_nl2sql.llm_client import LLMClient
    client = LLMClient()  # 用环境变量 / 默认配置
    answer = client.chat("你是助手", "你好")
"""
from __future__ import annotations

import os
import time
from typing import Any

import requests


DEFAULT_API_KEY = "__REDACTED_API_KEY__"
DEFAULT_API_URL = "__REDACTED_API_URL__"
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
DEFAULT_TIMEOUT = 30


class LLMClient:
    """OpenAI 兼容协议 LLM 客户端。

    Attributes:
        api_key: API 密钥
        api_url: API base URL（不含 /chat/completions 后缀）
        model: 模型名
        timeout: 请求超时秒数
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.api_key = api_key or os.getenv("NL2SQL_API_KEY", DEFAULT_API_KEY)
        self.api_url = (api_url or os.getenv("NL2SQL_API_URL", DEFAULT_API_URL)).rstrip("/")
        self.model = model or os.getenv("NL2SQL_MODEL", DEFAULT_MODEL)
        self.timeout = timeout
        # 复用 session 提升连接效率
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "dg-demo-nl2sql/1.0",
            }
        )

    # ── 公共 API ────────────────────────────────────────────────────────────

    def chat(self, system_prompt: str, user_message: str) -> str:
        """调用 chat completions 接口，返回模型回复文本。

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息

        Returns:
            模型返回的文本内容

        Raises:
            requests.Timeout: 请求超时
            LLMError: 非 200 状态码或响应解析失败
        """
        url = f"{self.api_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
        }
        try:
            resp = self._session.post(url, json=payload, timeout=self.timeout)
        except requests.Timeout as e:
            raise LLMError(
                f"LLM 请求超时（{self.timeout}s）: {e}"
            ) from e
        except requests.RequestException as e:
            raise LLMError(f"LLM 网络错误: {e}") from e

        if resp.status_code != 200:
            snippet = (resp.text or "")[:500]
            raise LLMError(
                f"LLM 非 200 响应: status={resp.status_code} body={snippet}"
            )

        try:
            data = resp.json()
        except ValueError as e:
            raise LLMError(f"LLM 响应非 JSON: {e}; body={resp.text[:200]}") from e

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise LLMError(f"LLM 响应结构异常: {e}; data={data}") from e

        return content if isinstance(content, str) else str(content)

    def ping(self) -> bool:
        """简单可达性检查（发 1 token 短消息）。"""
        try:
            self.chat("ping", "ping")
            return True
        except LLMError:
            return False


class LLMError(RuntimeError):
    """LLM 调用失败（网络/状态码/响应解析错误）。"""


# ── 便利函数 ────────────────────────────────────────────────────────────────

_default_client: LLMClient | None = None


def get_default_client() -> LLMClient:
    """获取（懒加载）全局默认 LLM 客户端。"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


__all__ = ["LLMClient", "LLMError", "get_default_client"]


if __name__ == "__main__":
    # 简单连通性测试
    c = LLMClient()
    t0 = time.time()
    try:
        out = c.chat("你是一个简洁的助手。", "用一句话介绍 DuckDB。")
        print(f"OK ({time.time()-t0:.2f}s): {out}")
    except LLMError as e:
        print(f"FAIL: {e}")
