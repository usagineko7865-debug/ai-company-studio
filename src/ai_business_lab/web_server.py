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
from .company import Project, load_state, save_state
from .config import ROOT, load_config
from .prompts import CEO_SYSTEM, CTO_SYSTEM

WEB_ROOT = ROOT / "web"


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
        if path == "/api/chat": return self._chat(body)
        return self._json({"error": "not found"}, 404)

    def _event(self, data):
        self.wfile.write((json.dumps(data, ensure_ascii=False) + "\n").encode("utf-8")); self.wfile.flush()

    def _chat(self, body):
        message = str(body.get("message", "")).strip()[:20_000]; real = bool(body.get("real"))
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
            limit = min(cfg.max_output_tokens, 500); gpt, claude = clients
            prompt = f"会社目的: {company.mission}\n顧客: {company.customer}\n\n社長の発言:\n{message}"
            budget.check_before_call("openai", CEO_SYSTEM + prompt, limit); a = gpt.chat(CEO_SYSTEM, prompt, limit)
            budget.record("openai", a.input_tokens, a.output_tokens); self._event({"type": "gpt", "text": a.text})
            cp = prompt + f"\n\n[{company.gpt_name}]\n{a.text}\n\n批判的に検証し、具体的な次の行動を提案してください。"
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
