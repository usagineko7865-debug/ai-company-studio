"""設定の読み込み。.env を自前で読む(外部パッケージ不要)。"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_ROUNDS = 3  # 会議の最大往復数(固定。設定で増やせない)


def load_env(path: Path | None = None) -> None:
    """.env を読み、未設定の環境変数だけ設定する。"""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    use_mock_env: bool
    openai_key: str
    anthropic_key: str
    openai_model: str
    anthropic_model: str
    max_budget_jpy: float
    jpy_per_usd: float
    openai_in: float
    openai_out: float
    anthropic_in: float
    anthropic_out: float
    max_output_tokens: int

    @property
    def max_budget_usd(self) -> float:
        return self.max_budget_jpy / self.jpy_per_usd


def load_config() -> Config:
    load_env()
    return Config(
        use_mock_env=os.environ.get("USE_MOCK", "true").strip().lower() != "false",
        openai_key=os.environ.get("OPENAI_API_KEY", "").strip(),
        anthropic_key=os.environ.get("ANTHROPIC_API_KEY", "").strip(),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-6-luna"),
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5"),
        max_budget_jpy=_float("MAX_BUDGET_JPY", 50),
        jpy_per_usd=_float("JPY_PER_USD", 155) or 155,
        openai_in=_float("OPENAI_INPUT_USD_PER_M", 0.10),
        openai_out=_float("OPENAI_OUTPUT_USD_PER_M", 0.50),
        anthropic_in=_float("ANTHROPIC_INPUT_USD_PER_M", 0.10),
        anthropic_out=_float("ANTHROPIC_OUTPUT_USD_PER_M", 0.50),
        max_output_tokens=_int("MAX_OUTPUT_TOKENS", 900),
    )
