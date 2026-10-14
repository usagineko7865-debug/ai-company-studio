"""API使用量と推定料金の管理。予算超過になる前に停止する。

注意: ここでの料金はあくまで「推定」です。本当の課金上限は
OpenAI / Anthropic 各コンソールの利用上限(Spend limit)で必ず設定してください。
"""
from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceeded(Exception):
    pass


def estimate_tokens(text: str) -> int:
    """粗い見積もり。日本語は1文字≒1トークンとみなし、安全側(多め)に見積もる。"""
    return int(len(text) * 1.0) + 50


@dataclass
class Usage:
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    calls: int = 0


@dataclass
class BudgetTracker:
    limit_usd: float
    jpy_per_usd: float
    prices: dict[str, tuple[float, float]]  # provider -> (入力$/M, 出力$/M)
    usage: dict[str, Usage] = field(default_factory=dict)

    def cost(self, provider: str, in_tok: int, out_tok: int) -> float:
        pin, pout = self.prices.get(provider, (0.0, 0.0))
        return (in_tok * pin + out_tok * pout) / 1_000_000

    @property
    def spent_usd(self) -> float:
        return sum(u.cost_usd for u in self.usage.values())

    def check_before_call(self, provider: str, prompt_text: str, max_out: int) -> None:
        """この呼び出しが最悪ケースで予算を超えるなら、呼ぶ前に止める。"""
        worst = self.cost(provider, estimate_tokens(prompt_text), max_out)
        if self.spent_usd + worst > self.limit_usd:
            raise BudgetExceeded(
                f"予算超過の恐れがあるため停止しました。"
                f"(使用済み推定 {self.spent_usd * self.jpy_per_usd:.1f}円 + "
                f"次回の最大 {worst * self.jpy_per_usd:.1f}円 > 上限 {self.limit_usd * self.jpy_per_usd:.0f}円)"
            )

    def record(self, provider: str, in_tok: int, out_tok: int) -> None:
        u = self.usage.setdefault(provider, Usage(provider))
        u.input_tokens += in_tok
        u.output_tokens += out_tok
        u.calls += 1
        u.cost_usd += self.cost(provider, in_tok, out_tok)

    def summary(self) -> dict:
        return {
            "limit_jpy": round(self.limit_usd * self.jpy_per_usd, 2),
            "estimated_total_jpy": round(self.spent_usd * self.jpy_per_usd, 2),
            "estimated_total_usd": round(self.spent_usd, 6),
            "providers": {
                k: {
                    "calls": u.calls,
                    "input_tokens": u.input_tokens,
                    "output_tokens": u.output_tokens,
                    "estimated_usd": round(u.cost_usd, 6),
                }
                for k, u in self.usage.items()
            },
            "note": "推定値です。正確な請求額は各社の管理画面で確認してください。",
        }
