"""依存パッケージ不要のローカルWeb版サーバー。127.0.0.1だけで待ち受ける。"""
from __future__ import annotations

import json
import mimetypes
import os
import threading
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .budget import BudgetTracker
from .clients import AnthropicClient, MockClient, OpenAIClient
from .company import (Project, backup_state, export_company_template,
                      import_company_template, load_state, save_state)
from .config import BUNDLE_ROOT, load_config
from .prompts import CEO_SYSTEM, CTO_SYSTEM

WEB_ROOT = BUNDLE_ROOT / "web"
LANGUAGE_NAMES = {
    "ja": "Japanese",
    "en": "English",
    "zh-CN": "Simplified Chinese",
    "pt-BR": "Brazilian Portuguese",
    "es": "Spanish",
}
LOCALIZED_MOCK = {
    "en": (
        "Let's narrow this into one small offer, define the customer, and test demand before building too much.",
        "I agree with a small test. Next, write one clear promise, a price hypothesis, and a measurable success condition.",
    ),
    "zh-CN": (
        "先把想法缩小成一个简单的产品，明确目标客户，并在投入开发前验证需求。",
        "我赞成先做小规模测试。下一步请确定核心承诺、价格假设和可衡量的成功标准。",
    ),
    "pt-BR": (
        "Vamos transformar a ideia em uma oferta simples, definir o cliente e validar a demanda antes de construir demais.",
        "Concordo com um teste pequeno. Agora defina uma promessa clara, uma hipótese de preço e um critério mensurável de sucesso.",
    ),
    "es": (
        "Convirtamos la idea en una oferta sencilla, definamos al cliente y validemos la demanda antes de construir demasiado.",
        "Estoy de acuerdo con una prueba pequeña. Define una promesa clara, una hipótesis de precio y un criterio medible de éxito.",
    ),
}


class Handler(BaseHTTPRequestHandler):
    server_version = "AICompanyStudio/1.0"

    def log_message(self, fmt, *args):
        return

    def _json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def _body(self):
        size = min(int(self.headers.get("Content-Length", 0)), 100_000)
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/bootstrap":
            cfg, state = load_config(), load_state()
            return self._json({"company": asdict(state), "api_budget": cfg.max_budget_jpy,
                               "keys_ready": bool(cfg.openai_key and cfg.anthropic_key and not cfg.use_mock_env)})
        if path == "/api/template/export":
            raw = json.dumps(export_company_template(load_state()), ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="ai-company-template.json"')
            self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        rel = "index.html" if path == "/" else path.lstrip("/")
        target = (WEB_ROOT / rel).resolve()
        if WEB_ROOT.resolve() not in target.parents and target != WEB_ROOT.resolve():
            return self._json({"error": "not found"}, 404)
        if not target.is_file(): return self._json({"error": "not found"}, 404)
        raw = target.read_bytes(); self.send_response(200)
        self.send_header("Content-Type", (mimetypes.guess_type(target.name)[0] or "application/octet-stream") + "; charset=utf-8")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_POST(self):
        try: body = self._body()
        except Exception: return self._json({"error": "invalid request"}, 400)
        path = urlparse(self.path).path
        if path == "/api/company":
            state = load_state(); state.company_name = str(body.get("company_name", ""))[:80] or state.company_name
            state.mission = str(body.get("mission", ""))[:500]; state.customer = str(body.get("customer", ""))[:500]
            state.operating_budget_jpy = max(0, int(body.get("operating_budget_jpy", 0)))
            save_state(state); return self._json(asdict(state))
        if path == "/api/project":
            state = load_state(); state.projects.append(Project(str(body.get("title", "名称未定"))[:80], str(body.get("summary", ""))[:30_000]))
            save_state(state); return self._json([asdict(p) for p in state.projects])
        if path == "/api/template":
            state = load_state()
            for key, limit in (("template_title", 120), ("value_proposition", 2_000),
                               ("proven_outcome", 4_000), ("evidence", 8_000),
                               ("repeatable_steps", 12_000), ("failure_conditions", 4_000)):
                setattr(state, key, str(body.get(key, ""))[:limit])
            save_state(state); return self._json(asdict(state))
        if path == "/api/template/import":
            state = load_state()
            try: imported = import_company_template(body, state)
            except (ValueError, TypeError) as exc: return self._json({"error": str(exc)}, 400)
            backup_state(); save_state(imported); return self._json(asdict(imported))
        if path == "/api/chat": return self._chat(body)
        return self._json({"error": "not found"}, 404)

    def _event(self, data):
        self.wfile.write((json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")); self.wfile.flush()

    def _chat(self, body):
        message = str(body.get("message", "")).strip()[:20_000]; real = bool(body.get("real"))
        lang = str(body.get("lang", "ja")); reply_language = LANGUAGE_NAMES.get(lang, "Japanese")
        if not message: return self._json({"error": "message required"}, 400)
        cfg, company = load_config(), load_state()
        if real and (cfg.use_mock_env or not cfg.openai_key or not cfg.anthropic_key):
            return self._json({"error": ".env のAPIキーと USE_MOCK=false を確認してください。"}, 400)
        clients = ((OpenAIClient(cfg.openai_key, cfg.openai_model), AnthropicClient(cfg.anthropic_key, cfg.anthropic_model))
                   if real else (MockClient("openai", "ceo"), MockClient("anthropic", "cto")))
        budget = BudgetTracker(cfg.max_budget_usd, cfg.jpy_per_usd,
            {"openai": (cfg.openai_in, cfg.openai_out), "anthropic": (cfg.anthropic_in, cfg.anthropic_out)})
        self.send_response(200); self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store"); self.end_headers()
        try:
            if not real and lang in LOCALIZED_MOCK:
                gpt_text, claude_text = LOCALIZED_MOCK[lang]
                self._event({"type": "gpt", "text": gpt_text})
                self._event({"type": "claude", "text": claude_text, "estimated_jpy": 0})
                return
            limit = min(cfg.max_output_tokens, 500); gpt, claude = clients
            language_rule = f"Reply only in {reply_language}."
            prompt = f"{language_rule}\n会社目的: {company.mission}\n顧客: {company.customer}\n\n社長の発言:\n{message}"
            budget.check_before_call("openai", CEO_SYSTEM + prompt, limit); a = gpt.chat(CEO_SYSTEM, prompt, limit)
            budget.record("openai", a.input_tokens, a.output_tokens); self._event({"type": "gpt", "text": a.text})
            cp = prompt + f"\n\n[{company.gpt_name}]\n{a.text}\n\n{language_rule} 批判的に検証し、具体的な次の行動を提案してください。"
            budget.check_before_call("anthropic", CTO_SYSTEM + cp, limit); b = claude.chat(CTO_SYSTEM, cp, limit)
            budget.record("anthropic", b.input_tokens, b.output_tokens)
            self._event({"type": "claude", "text": b.text, "estimated_jpy": budget.summary()["estimated_total_jpy"]})
        except Exception as exc:
            self._event({"type": "error", "message": str(exc)})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    threading.Timer(0.7, lambda: webbrowser.open("http://127.0.0.1:8765")).start()
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__ == "__main__": main()
