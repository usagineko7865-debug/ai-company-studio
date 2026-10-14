"""AIクライアント。モック / 実API を同じ形で扱う。標準ライブラリ(urllib)のみ使用。

実API版は「通信するのはOpenAI/Anthropicの公式エンドポイントのみ」。
自動リトライはしない(意図しない二重課金を防ぐため)。
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

TIMEOUT_SEC = 90


class ApiError(Exception):
    pass


@dataclass
class Reply:
    text: str
    input_tokens: int
    output_tokens: int
    source: str  # "MOCK" or "REAL"
    model: str


def _post_json(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # APIキーがメッセージに混ざらないよう、本文は先頭のみ・ヘッダは出さない
        detail = e.read().decode("utf-8", "replace")[:300]
        raise ApiError(f"HTTP {e.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise ApiError(f"通信エラー: {getattr(e, 'reason', e)}") from None


class OpenAIClient:
    provider = "openai"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def chat(self, system: str, user: str, max_tokens: int) -> Reply:
        data = _post_json(
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            {
                "model": self.model,
                "max_completion_tokens": max_tokens,
                # Luna の推論トークンも出力枠・料金に含まれるため、初回はOFFにする。
                "reasoning_effort": "none",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        try:
            text = data["choices"][0]["message"]["content"] or ""
            if not text.strip():
                raise ApiError("OpenAIの応答が空でした")
            u = data.get("usage", {})
            return Reply(text, u.get("prompt_tokens", 0), u.get("completion_tokens", 0), "REAL", self.model)
        except (KeyError, IndexError, TypeError):
            raise ApiError("OpenAIの応答形式が想定と異なります") from None


class AnthropicClient:
    provider = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def chat(self, system: str, user: str, max_tokens: int) -> Reply:
        data = _post_json(
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            {
                "model": self.model,
                "max_tokens": max_tokens,
                "system": system,
                # Haiku 5.5 は思考(thinking)が初期ONで、思考分も出力料金・max_tokensに含まれる。
                # 初回テストの費用と応答長を読みやすくするため、思考をOFFにする。
                "thinking": {"type": "disabled"},
                "messages": [{"role": "user", "content": user}],
            },
        )
        try:
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
            if not text.strip():
                raise ApiError("Anthropicの応答が空でした")
            u = data.get("usage", {})
            return Reply(text, u.get("input_tokens", 0), u.get("output_tokens", 0), "REAL", self.model)
        except (KeyError, TypeError):
            raise ApiError("Anthropicの応答形式が想定と異なります") from None


class MockClient:
    """APIを呼ばない固定応答。ネットワーク通信は一切しない。"""

    def __init__(self, provider: str, role: str):
        self.provider, self.role = provider, role
        self.model = f"mock-{provider}"

    def chat(self, system: str, user: str, max_tokens: int) -> Reply:
        from .mock_data import mock_reply

        text = mock_reply(self.role, user)
        # モックでも予算ロジックを試せるよう、トークン数は文字数から推定
        return Reply(text, len(system + user), len(text), "MOCK", self.model)
