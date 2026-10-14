"""Phase 1: 会社設定・AI役員会・事業案管理をまとめたデスクトップUI。"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from .budget import BudgetTracker
from .clients import AnthropicClient, MockClient, OpenAIClient
from .company import Project, load_state, save_state
from .config import load_config
from .prompts import CEO_SYSTEM, CTO_SYSTEM

THEMES = {
    "シンプル": {"bg": "#f5f7fb", "panel": "#ffffff", "accent": "#2563eb", "text": "#182230"},
    "ダーク": {"bg": "#111827", "panel": "#1f2937", "accent": "#22c55e", "text": "#f9fafb"},
    "高級感": {"bg": "#15130f", "panel": "#252117", "accent": "#d4af37", "text": "#fff8df"},
}


class Phase1App:
    def __init__(self, root):
        self.root, self.state = root, load_state()
        self.events, self.messages = queue.Queue(), []
        self.budget, self.latest_exchange = None, None
        root.title("AI Company Studio — Phase 1")
        root.geometry("1000x720"); root.minsize(820, 620)
        self.style = ttk.Style()
        self._build(); self.apply_theme()

    def _build(self):
        self.header = tk.Frame(self.root, padx=20, pady=14)
        self.header.pack(fill="x")
        self.title = tk.Label(self.header, text=self.state.company_name, font=("Yu Gothic UI", 19, "bold"))
        self.title.pack(side="left")
        self.phase = tk.Label(self.header, text="PHASE 1 会社の土台", font=("Yu Gothic UI", 10, "bold"))
        self.phase.pack(side="right")

        self.tabs = ttk.Notebook(self.root); self.tabs.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.home = tk.Frame(self.tabs); self.board = tk.Frame(self.tabs)
        self.projects = tk.Frame(self.tabs); self.settings = tk.Frame(self.tabs)
        self.tabs.add(self.home, text=" 会社ホーム "); self.tabs.add(self.board, text=" AI役員会 ")
        self.tabs.add(self.projects, text=" 事業案 "); self.tabs.add(self.settings, text=" 見た目・設定 ")
        self._home_tab(); self._board_tab(); self._projects_tab(); self._settings_tab()

    def _entry(self, parent, label, value, row, width=55):
        tk.Label(parent, text=label, font=("Yu Gothic UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=8)
        entry = ttk.Entry(parent, width=width); entry.insert(0, value)
        entry.grid(row=row, column=1, sticky="ew", padx=(15, 0), pady=8); return entry

    def _home_tab(self):
        box = tk.Frame(self.home, padx=35, pady=28); box.pack(fill="both", expand=True)
        tk.Label(box, text="会社の基本情報", font=("Yu Gothic UI", 17, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
        self.company_name = self._entry(box, "会社名", self.state.company_name, 1)
        self.mission = self._entry(box, "会社の目的", self.state.mission, 2)
        self.customer = self._entry(box, "主な顧客", self.state.customer, 3)
        self.company_budget = self._entry(box, "運営予算（円）", str(self.state.operating_budget_jpy), 4)
        ttk.Button(box, text="会社情報を保存", command=self.save_company).grid(row=5, column=1, sticky="e", pady=18)
        tk.Label(box, text="Phase 1では会社の方針と事業案を作ります。公開・販売・購入は行いません。",
                 font=("Yu Gothic UI", 10)).grid(row=6, column=0, columnspan=2, sticky="w", pady=8)
        box.columnconfigure(1, weight=1)

    def _board_tab(self):
        top = tk.Frame(self.board, padx=14, pady=10); top.pack(fill="x")
        tk.Label(top, text="3人の役員会", font=("Yu Gothic UI", 15, "bold")).pack(side="left")
        self.mode = tk.StringVar(value="mock")
        ttk.Radiobutton(top, text="無料練習", variable=self.mode, value="mock").pack(side="right")
        ttk.Radiobutton(top, text="実AI", variable=self.mode, value="real").pack(side="right", padx=12)
        self.chat = tk.Text(self.board, state="disabled", wrap="word", font=("Yu Gothic UI", 11), padx=15, pady=12)
        self.chat.pack(fill="both", expand=True, padx=14)
        for tag, color in (("owner", "#15803d"), ("gpt", "#2563eb"), ("claude", "#c26419"), ("system", "#777777")):
            self.chat.tag_configure(tag, foreground=color, spacing1=5, spacing3=10)
        self._chat_add("system", "意見や事業アイデアを入力してください。AI役員2人が順番に返答します。")
        send = tk.Frame(self.board, padx=14, pady=12); send.pack(fill="x")
        self.input = tk.Text(send, height=4, wrap="word", font=("Yu Gothic UI", 11)); self.input.pack(side="left", fill="x", expand=True)
        right = tk.Frame(send); right.pack(side="left", padx=(10, 0))
        self.send_btn = ttk.Button(right, text="役員会へ送信", command=self.send); self.send_btn.pack(fill="x")
        self.save_idea_btn = ttk.Button(right, text="事業案として保存", command=self.save_idea, state="disabled")
        self.save_idea_btn.pack(fill="x", pady=(8, 0))
        self.board_status = tk.StringVar(value="準備完了")
        tk.Label(self.board, textvariable=self.board_status, anchor="w", padx=16, pady=7).pack(fill="x")

    def _projects_tab(self):
        wrap = tk.Frame(self.projects, padx=22, pady=20); wrap.pack(fill="both", expand=True)
        tk.Label(wrap, text="保存した事業案", font=("Yu Gothic UI", 16, "bold")).pack(anchor="w", pady=(0, 12))
        self.project_list = tk.Listbox(wrap, font=("Yu Gothic UI", 11), height=9)
        self.project_list.pack(fill="x"); self.project_list.bind("<<ListboxSelect>>", self.show_project)
        self.project_detail = tk.Text(wrap, state="disabled", wrap="word", font=("Yu Gothic UI", 10), height=14)
        self.project_detail.pack(fill="both", expand=True, pady=(12, 0)); self.refresh_projects()

    def _settings_tab(self):
        box = tk.Frame(self.settings, padx=35, pady=28); box.pack(fill="both", expand=True)
        tk.Label(box, text="見た目と役職名", font=("Yu Gothic UI", 17, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
        tk.Label(box, text="テーマ", font=("Yu Gothic UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=8)
        self.theme_name = ttk.Combobox(box, values=list(THEMES), state="readonly"); self.theme_name.set(self.state.ui_theme)
        self.theme_name.grid(row=1, column=1, sticky="ew", padx=(15, 0))
        self.owner_name = self._entry(box, "社長の表示名", self.state.owner_name, 2)
        self.gpt_name = self._entry(box, "チャッピーの役職名", self.state.gpt_name, 3)
        self.claude_name = self._entry(box, "Claudeの役職名", self.state.claude_name, 4)
        ttk.Button(box, text="設定を保存して反映", command=self.save_settings).grid(row=5, column=1, sticky="e", pady=18)
        box.columnconfigure(1, weight=1)

    def apply_theme(self):
        theme = THEMES.get(self.state.ui_theme, THEMES["シンプル"])
        self.root.configure(bg=theme["bg"]); self.header.configure(bg=theme["panel"])
        self.title.configure(bg=theme["panel"], fg=theme["text"]); self.phase.configure(bg=theme["panel"], fg=theme["accent"])
        for frame in (self.home, self.board, self.projects, self.settings): frame.configure(bg=theme["bg"])
        self.style.configure("TNotebook", background=theme["bg"])

    def save_company(self):
        try: budget = max(0, int(self.company_budget.get()))
        except ValueError: messagebox.showerror("入力エラー", "運営予算は数字で入力してください。"); return
        self.state.company_name = self.company_name.get().strip() or "My AI Company"
        self.state.mission, self.state.customer, self.state.operating_budget_jpy = self.mission.get().strip(), self.customer.get().strip(), budget
        save_state(self.state); self.title.configure(text=self.state.company_name)
        messagebox.showinfo("保存しました", "会社情報をこのPC内に保存しました。")

    def save_settings(self):
        self.state.ui_theme = self.theme_name.get(); self.state.owner_name = self.owner_name.get().strip() or "あなた"
        self.state.gpt_name = self.gpt_name.get().strip() or "チャッピー CEO"; self.state.claude_name = self.claude_name.get().strip() or "Claude CTO"
        save_state(self.state); self.apply_theme(); messagebox.showinfo("反映しました", "見た目と役職名を変更しました。")

    def _chat_add(self, who, text):
        names = {"owner": self.state.owner_name, "gpt": self.state.gpt_name, "claude": self.state.claude_name}
        self.chat.configure(state="normal")
        self.chat.insert("end", (f"{names[who]}\n{text}\n" if who != "system" else f"{text}\n"), who)
        self.chat.configure(state="disabled"); self.chat.see("end")

    def send(self):
        text = self.input.get("1.0", "end").strip()
        if not text: return
        real = self.mode.get() == "real"; cfg = load_config()
        if real:
            if cfg.use_mock_env or not cfg.openai_key or not cfg.anthropic_key:
                messagebox.showerror("設定エラー", ".env のAPIキーと USE_MOCK=false を確認してください。"); return
            if not messagebox.askyesno("実AIへ送信", f"OpenAIとAnthropicへ送信します。API上限は1実行{cfg.max_budget_jpy:.0f}円です。続けますか？"): return
            clients = OpenAIClient(cfg.openai_key, cfg.openai_model), AnthropicClient(cfg.anthropic_key, cfg.anthropic_model)
        else: clients = MockClient("openai", "ceo"), MockClient("anthropic", "cto")
        if self.budget is None:
            self.budget = BudgetTracker(cfg.max_budget_usd, cfg.jpy_per_usd, {"openai": (cfg.openai_in, cfg.openai_out), "anthropic": (cfg.anthropic_in, cfg.anthropic_out)})
        self.input.delete("1.0", "end"); self._chat_add("owner", text); self.messages.append((self.state.owner_name, text))
        self.send_btn.configure(state="disabled"); self.board_status.set("チャッピーが考えています…")
        threading.Thread(target=self._run_reply, args=(cfg, clients, text), daemon=True).start(); self.root.after(150, self._poll)

    def _run_reply(self, cfg, clients, user_text):
        try:
            history = "\n\n".join(f"[{n}] {t}" for n, t in self.messages)[-10000:]
            limit = min(cfg.max_output_tokens, 500); gpt, claude = clients
            prompt = f"会社目的: {self.state.mission}\n顧客: {self.state.customer}\n\n役員会履歴:\n{history}"
            self.budget.check_before_call("openai", CEO_SYSTEM + prompt, limit); a = gpt.chat(CEO_SYSTEM, prompt, limit)
            self.budget.record("openai", a.input_tokens, a.output_tokens); self.events.put(("gpt", a.text))
            cp = prompt + f"\n\n[{self.state.gpt_name}] {a.text}\nこの意見を批判的に検証し、次の行動を提案してください。"
            self.budget.check_before_call("anthropic", CTO_SYSTEM + cp, limit); b = claude.chat(CTO_SYSTEM, cp, limit)
            self.budget.record("anthropic", b.input_tokens, b.output_tokens); self.events.put(("claude", user_text, a.text, b.text))
        except Exception as exc: self.events.put(("error", str(exc)))

    def _poll(self):
        try: event = self.events.get_nowait()
        except queue.Empty: self.root.after(150, self._poll); return
        if event[0] == "gpt":
            self._chat_add("gpt", event[1]); self.messages.append((self.state.gpt_name, event[1])); self.board_status.set("Claudeが検証しています…"); self.root.after(150, self._poll); return
        self.send_btn.configure(state="normal")
        if event[0] == "error": self.board_status.set("安全停止: " + event[1]); messagebox.showerror("停止しました", event[1]); return
        _, user_text, gpt_text, claude_text = event
        self._chat_add("claude", claude_text); self.messages.append((self.state.claude_name, claude_text))
        self.latest_exchange = (user_text, gpt_text, claude_text); self.save_idea_btn.configure(state="normal")
        self.board_status.set(f"完了 • API推定 {self.budget.summary()['estimated_total_jpy']}円")

    def save_idea(self):
        if not self.latest_exchange: return
        user_text, gpt_text, claude_text = self.latest_exchange
        title = user_text.splitlines()[0][:45] or "名称未定の事業"
        self.state.projects.append(Project(title, f"【社長の提案】\n{user_text}\n\n【CEO】\n{gpt_text}\n\n【CTO】\n{claude_text}"))
        save_state(self.state); self.refresh_projects(); self.tabs.select(self.projects)

    def refresh_projects(self):
        self.project_list.delete(0, "end")
        for i, p in enumerate(self.state.projects, 1): self.project_list.insert("end", f"{i}. [{p.status}] {p.title}")

    def show_project(self, _event=None):
        pick = self.project_list.curselection()
        if not pick: return
        p = self.state.projects[pick[0]]; self.project_detail.configure(state="normal"); self.project_detail.delete("1.0", "end")
        self.project_detail.insert("end", f"{p.title}\n状態: {p.status}\n\n{p.summary}"); self.project_detail.configure(state="disabled")


def main():
    root = tk.Tk(); Phase1App(root); root.mainloop()


if __name__ == "__main__": main()
