"""Phase 1 の会社情報と事業案を、秘密情報を含めずローカル保存する。"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import ROOT

STATE_PATH = ROOT / "data" / "company_state.json"


@dataclass
class Project:
    title: str
    summary: str
    status: str = "検討中"


@dataclass
class CompanyState:
    company_name: str = "My AI Company"
    mission: str = "AIと一緒に、小さく検証して事業を育てる"
    customer: str = "これから副業・小規模事業を始めたい人"
    operating_budget_jpy: int = 1000
    ui_theme: str = "シンプル"
    owner_name: str = "あなた"
    gpt_name: str = "チャッピー CEO"
    claude_name: str = "Claude CTO"
    projects: list[Project] = field(default_factory=list)


def load_state(path: Path = STATE_PATH) -> CompanyState:
    if not path.exists():
        return CompanyState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["projects"] = [Project(**p) for p in data.get("projects", [])]
        return CompanyState(**data)
    except (OSError, ValueError, TypeError):
        return CompanyState()


def save_state(state: CompanyState, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")
