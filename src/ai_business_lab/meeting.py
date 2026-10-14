"""会議の進行・保存。エラー時は安全停止し、そこまでの記録を必ず保存する。"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import prompts
from .budget import BudgetExceeded, BudgetTracker
from .clients import AnthropicClient, ApiError, MockClient, OpenAIClient, Reply
from .config import MAX_ROUNDS, ROOT, Config

ROLE_LABEL = {"ceo": "CEO (OpenAI)", "cto": "CTO (Claude)"}


class ModeError(Exception):
    pass


def build_clients(cfg: Config, real_flag: bool):
    """実APIは (USE_MOCK=false) かつ (--real 指定) かつ (両キー設定済み) の時だけ。"""
    if not real_flag or cfg.use_mock_env:
        return MockClient("openai", "ceo"), MockClient("anthropic", "cto"), "MOCK"
    missing = [n for n, k in (("OPENAI_API_KEY", cfg.openai_key), ("ANTHROPIC_API_KEY", cfg.anthropic_key)) if not k]
    if missing:
        raise ModeError(f".env に {', '.join(missing)} が設定されていません。実APIモードを開始できません。")
    return OpenAIClient(cfg.openai_key, cfg.openai_model), AnthropicClient(cfg.anthropic_key, cfg.anthropic_model), "REAL"


@dataclass
class Turn:
    round_no: int
    role: str
    reply: Reply


@dataclass
class Result:
    mode: str
    theme: str
    started: str
    status: str = "running"  # completed / stopped
    stop_reason: str = ""
    turns: list[Turn] = field(default_factory=list)
    final_raw: str = ""
    final_proposal: dict | None = None
    final_source: str = ""


def _history_text(turns: list[Turn]) -> str:
    return "\n\n".join(f"[ラウンド{t.round_no} {ROLE_LABEL[t.role]}]\n{t.reply.text}" for t in turns)


def _parse_json(text: str) -> dict | None:
    t = text.strip()
    if t.startswith("```"):  # コードフェンスが付いても読めるように
        t = t.strip("`")
        t = t[4:] if t.lower().startswith("json") else t
    try:
        data = json.loads(t)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def run_meeting(cfg: Config, theme: str, real_flag: bool, log: logging.Logger) -> tuple[Result, BudgetTracker]:
    ceo, cto, mode = build_clients(cfg, real_flag)
    budget = BudgetTracker(
        limit_usd=cfg.max_budget_usd,
        jpy_per_usd=cfg.jpy_per_usd,
        prices={"openai": (cfg.openai_in, cfg.openai_out), "anthropic": (cfg.anthropic_in, cfg.anthropic_out)},
    )
    res = Result(mode=mode, theme=theme, started=datetime.now().isoformat(timespec="seconds"))
    log.info("会議開始 mode=%s theme=%s", mode, theme)

    def call(client, system: str, user: str) -> Reply:
        budget.check_before_call(client.provider, system + user, cfg.max_output_tokens)
        r = client.chat(system, user, cfg.max_output_tokens)
        budget.record(client.provider, r.input_tokens, r.output_tokens)
        log.info("%s 応答 source=%s in=%d out=%d 累計推定=%.1f円", client.provider, r.source,
                 r.input_tokens, r.output_tokens, budget.spent_usd * cfg.jpy_per_usd)
        return r

    try:
        for rnd in range(1, MAX_ROUNDS + 1):
            for role, client, system in (("ceo", ceo, prompts.CEO_SYSTEM), ("cto", cto, prompts.CTO_SYSTEM)):
                user = prompts.turn_prompt(theme, rnd, role, _history_text(res.turns))
                res.turns.append(Turn(rnd, role, call(client, system, user)))
        # 往復(3回)とは別の「取りまとめ」1回。CEOが最終提案JSONを作る。
        final = call(ceo, prompts.FINAL_SYSTEM, prompts.final_prompt(theme, _history_text(res.turns)))
        res.final_raw, res.final_source = final.text, final.source
        res.final_proposal = _parse_json(final.text)
        if res.final_proposal is None:
            res.status, res.stop_reason = "completed", "最終提案がJSONとして解析できなかったため、原文を保存しました"
            log.warning(res.stop_reason)
        else:
            res.status = "completed"
    except BudgetExceeded as e:
        res.status, res.stop_reason = "stopped", str(e)
        log.error("予算停止: %s", e)
    except ApiError as e:
        res.status, res.stop_reason = "stopped", f"APIエラー: {e}"
        log.error("APIエラーで安全停止: %s", e)
    except Exception as e:  # 想定外でも記録を残して止める
        res.status, res.stop_reason = "stopped", f"想定外のエラー: {type(e).__name__}: {e}"
        log.exception("想定外のエラーで安全停止")
    return res, budget


def save_outputs(res: Result, budget: BudgetTracker, out_dir: Path, stamp: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    banner = (
        "🟡 **【MOCKモード】これはAPIを使わないサンプル応答です。実際の市場調査・AI応答ではありません。**"
        if res.mode == "MOCK"
        else "🟢 **【REALモード】実際のAPI応答です。ただし事実・数値は必ず人間が検証してください。**"
    )
    lines = [f"# AI Business Lab 会議記録", "", banner, "",
             f"- 開始: {res.started}", f"- テーマ: {res.theme}", f"- 状態: {res.status}"]
    if res.stop_reason:
        lines.append(f"- 備考/停止理由: {res.stop_reason}")
    lines += ["", "> 収益を保証するものではありません。需要が未確認の事項は仮説です。", ""]
    for t in res.turns:
        lines += [f"## ラウンド{t.round_no} / {ROLE_LABEL[t.role]}  `[{t.reply.source}: {t.reply.model}]`", "", t.reply.text, ""]
    if res.final_raw:
        lines += [f"## 最終提案(CEO取りまとめ)  `[{res.final_source}]`", "", "```json", res.final_raw, "```", ""]
    s = budget.summary()
    lines += ["## 使用量と推定料金", "", f"- 推定合計: **{s['estimated_total_jpy']}円** (上限 {s['limit_jpy']}円)", ""]
    for k, v in s["providers"].items():
        lines.append(f"- {k}: {v['calls']}回 / 入力{v['input_tokens']} / 出力{v['output_tokens']}トークン / 約${v['estimated_usd']}")
    lines += ["", f"_{s['note']}_", ""]
    md_path = out_dir / f"meeting_{stamp}.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")

    proposal = {
        "mode": res.mode,
        "is_mock": res.mode == "MOCK",
        "status": res.status,
        "stop_reason": res.stop_reason,
        "theme": res.theme,
        "started": res.started,
        "proposal": res.final_proposal,
        "proposal_raw_if_unparsed": None if res.final_proposal else (res.final_raw or None),
        "usage": s,
        "disclaimer": "収益を保証するものではありません。需要が未確認の事項は仮説です。",
    }
    json_path = out_dir / f"proposal_{stamp}.json"
    json_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path


def make_logger(stamp: str, log_dir: Path | None = None) -> logging.Logger:
    log_dir = log_dir or ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"ai_business_lab.{stamp}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    fh = logging.FileHandler(log_dir / f"run_{stamp}.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    return logger
