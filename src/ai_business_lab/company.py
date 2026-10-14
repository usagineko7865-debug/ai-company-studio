"""Phase 1 の会社情報と事業案を、秘密情報を含めずローカル保存する。"""
from __future__ import annotations

import json
import shutil
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
    template_title: str = ""
    value_proposition: str = ""
    proven_outcome: str = ""
    evidence: str = ""
    repeatable_steps: str = ""
    failure_conditions: str = ""
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


def export_company_template(state: CompanyState) -> dict:
    """秘密情報を含めず、再現可能な会社テンプレートとして書き出す。"""
    return {
        "schema": "ai-company-template",
        "schema_version": 1,
        "template": {
            "title": state.template_title or state.company_name,
            "value_proposition": state.value_proposition,
            "proven_outcome": state.proven_outcome,
            "evidence": state.evidence,
            "repeatable_steps": state.repeatable_steps,
            "failure_conditions": state.failure_conditions,
        },
        "company": {
            "company_name": state.company_name,
            "mission": state.mission,
            "customer": state.customer,
            "operating_budget_jpy": state.operating_budget_jpy,
        },
        "projects": [asdict(project) for project in state.projects],
        "disclaimer": "Past results do not guarantee future outcomes.",
    }


def import_company_template(payload: dict, current: CompanyState) -> CompanyState:
    """外部テンプレートを長さ制限付きで検証し、秘密設定を引き継がない。"""
    if payload.get("schema") != "ai-company-template" or payload.get("schema_version") != 1:
        raise ValueError("対応していない会社テンプレートです。")
    template = payload.get("template") or {}
    company = payload.get("company") or {}
    raw_projects = payload.get("projects") or []
    if not isinstance(template, dict) or not isinstance(company, dict) or not isinstance(raw_projects, list):
        raise ValueError("会社テンプレートの形式が正しくありません。")
    clean = lambda value, limit: str(value or "")[:limit]
    projects = []
    for item in raw_projects[:50]:
        if not isinstance(item, dict):
            continue
        projects.append(Project(clean(item.get("title"), 80) or "名称未定",
                                clean(item.get("summary"), 30_000), clean(item.get("status"), 30) or "検討中"))
    return CompanyState(
        company_name=clean(company.get("company_name"), 80) or current.company_name,
        mission=clean(company.get("mission"), 500), customer=clean(company.get("customer"), 500),
        operating_budget_jpy=max(0, min(int(company.get("operating_budget_jpy") or 0), 1_000_000_000)),
        ui_theme=current.ui_theme, owner_name=current.owner_name,
        gpt_name=current.gpt_name, claude_name=current.claude_name,
        template_title=clean(template.get("title"), 120),
        value_proposition=clean(template.get("value_proposition"), 2_000),
        proven_outcome=clean(template.get("proven_outcome"), 4_000),
        evidence=clean(template.get("evidence"), 8_000),
        repeatable_steps=clean(template.get("repeatable_steps"), 12_000),
        failure_conditions=clean(template.get("failure_conditions"), 4_000), projects=projects)


def backup_state(path: Path = STATE_PATH) -> Path | None:
    if not path.exists():
        return None
    backup = path.with_name("company_state.backup.json")
    shutil.copy2(path, backup)
    return backup
