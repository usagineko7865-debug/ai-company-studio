"""あなた・ChatGPT・Claudeで話す、グループチャット風UI。"""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from .budget import BudgetExceeded, BudgetTracker
from .clients import AnthropicClient, ApiError, MockClient, OpenAIClient
from .config import ROOT, load_config
from .prompts import CEO_SYSTEM, CTO_SYSTEM


class GroupChatApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("AI Business Lab — 3人グループ")
        root.geometry("800x700")
        root.minsize(680, 560)
        self.events = queue.Queue()
        self.messages = []
        self.budget = None
        self.session_mode = None
        self.transcript = None

        style = ttk.Style()
        style.configure("Title.TLabel", font=("Yu Gothic UI", 17, "bold"))
        style.configure("Send.TButton", font=("Yu Gothic UI", 11, "bold"), padding=9)

        top = ttk.Frame(root, padding=(18, 14)); top.pack(fill="x")
        ttk.Label(top, text="ビジネス開発グループ", style="Title.TLabel").pack(side="left")
        self.mode = tk.StringVar(value="mock")
        ttk.Radiobutton(top, text="無料練習", variable=self.mode, value="mock").pack(side="right")
        ttk.Radiobutton(top, text="実AI", variable=self.mode, value="real").pack(side="right", padx=12)

        self.chat = tk.Text(root, wrap="word", state="disabled", font=("Yu Gothic UI", 11),
                            padx=16, pady=14, bg="#f3f4f6", relief="flat")
        self.chat.pack(fill="both", expand=True, padx=18)
        self.chat.tag_configure("you_name", foreground="#16833b", font=("Yu Gothic UI", 10, "bold"), justify="right")
        self.chat.tag_configure("you", background="#d8f7c9", lmargin1=170, lmargin2=170, rmargin=8,
                                spacing1=3, spacing3=12, justify="right")
        self.chat.tag_configure("gpt_name", foreground="#1565c0", font=("Yu Gothic UI", 10, "bold"))
        self.chat.tag_configure("gpt", background="#ffffff", lmargin1=8, lmargin2=8, rmargin=170,
                                spacing1=3, spacing3=12)
        self.chat.tag_configure("claude_name", foreground="#a45117", font=("Yu Gothic UI", 10, "bold"))
        self.chat.tag_configure("claude", background="#fff4e8", lmargin1=8, lmargin2=8, rmargin=170,
                                spacing1=3, spacing3=12)
        self.chat.tag_configure("system", foreground="#666666", justify="center", spacing1=7, spacing3=7)
        self._append("system", "議題やアイデアを書いて送信してください。チャッピーとClaudeが順番に返事します。")

        compose = ttk.Frame(root, padding=18); compose.pack(fill="x")
        self.input = tk.Text(compose, height=4, wrap="word", font=("Yu Gothic UI", 11), padx=9, pady=9)
        self.input.pack(side="left", fill="x", expand=True)
        self.input.bind("<Control-Return>", lambda _event: self.send())
        buttons = ttk.Frame(compose); buttons.pack(side="left", padx=(12, 0))
        self.send_button = ttk.Button(buttons, text="送信", style="Send.TButton", command=self.send)
        self.send_button.pack(fill="x")
        ttk.Button(buttons, text="結果を開く", command=self.open_transcript).pack(fill="x", pady=(8, 0))

        bottom = ttk.Frame(root, padding=(18, 0, 18, 14)); bottom.pack(fill="x")
        self.progress = ttk.Progressbar(bottom, mode="indeterminate"); self.progress.pack(fill="x")
        self.status = tk.StringVar(value="準備完了  •  Ctrl+Enterでも送信できます")
        ttk.Label(bottom, textvariable=self.status, foreground="#555555").pack(anchor="w", pady=(6, 0))

    def _append(self, who, text):
        labels = {"you": "あなた", "gpt": "チャッピー", "claude": "Claude"}
        self.chat.configure(state="normal")
        if who == "system":
            self.chat.insert("end", f"{text}\n", "system")
        else:
            self.chat.insert("end", f"{labels[who]}\n", f"{who}_name")
            self.chat.insert("end", f"{text}\n", who)
        self.chat.configure(state="disabled"); self.chat.see("end")

    def _prepare_session(self, real):
        cfg = load_config(); mode = "real" if real else "mock"
        if self.session_mode and self.session_mode != mode:
            self.messages.clear(); self.budget = None
            self._append("system", "モードを変更したため、新しい会話として開始します。")
        self.session_mode = mode
        if self.budget is None:
            self.budget = BudgetTracker(cfg.max_budget_usd, cfg.jpy_per_usd,
                {"openai": (cfg.openai_in, cfg.openai_out), "anthropic": (cfg.anthropic_in, cfg.anthropic_out)})
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.transcript = ROOT / "outputs" / f"group_chat_{stamp}.md"
        if real:
            if cfg.use_mock_env or not cfg.openai_key or not cfg.anthropic_key:
                raise ValueError(".env のAPIキーと USE_MOCK=false を確認してください。")
            clients = OpenAIClient(cfg.openai_key, cfg.openai_model), AnthropicClient(cfg.anthropic_key, cfg.anthropic_model)
        else:
            clients = MockClient("openai", "ceo"), MockClient("anthropic", "cto")
        return cfg, clients

    def send(self):
        text = self.input.get("1.0", "end").strip()
        if not text: return
        real = self.mode.get() == "real"
        if real and not messagebox.askyesno("実AIへ送信します",
            "このメッセージをOpenAIとAnthropicへ送り、2人から返事を受け取ります。\n"
            "セッション合計の予算上限は50円です。送信しますか？"):
            return
        try:
            cfg, clients = self._prepare_session(real)
        except ValueError as exc:
            messagebox.showerror("設定エラー", str(exc)); return
        self.input.delete("1.0", "end")
        self._append("you", text); self.messages.append(("あなた", text))
        self.send_button.configure(state="disabled"); self.progress.start(12)
        self.status.set("チャッピーとClaudeが考えています…")
        threading.Thread(target=self._reply, args=(cfg, clients), daemon=True).start()
        self.root.after(150, self._poll)

    def _history(self):
        return "\n\n".join(f"[{name}]\n{text}" for name, text in self.messages)[-12000:]

    def _reply(self, cfg, clients):
        try:
            gpt, claude = clients
            # グループチャットでは短めに返し、待ち時間と料金を抑える。
            max_tokens = min(cfg.max_output_tokens, 500)
            prompt = "3人のグループ会話です。直前の発言に、事業開発の視点で簡潔に返答してください。\n\n" + self._history()
            self.budget.check_before_call(gpt.provider, CEO_SYSTEM + prompt, max_tokens)
            a = gpt.chat(CEO_SYSTEM, prompt, max_tokens)
            self.budget.record(gpt.provider, a.input_tokens, a.output_tokens)
            # 2人分を待たず、チャッピーの返事を先に画面へ出す。
            self.events.put(("gpt", a.text))
            cp = prompt + f"\n\n[チャッピー]\n{a.text}\n\nチャッピーの意見も踏まえて返答してください。"
            self.budget.check_before_call(claude.provider, CTO_SYSTEM + cp, max_tokens)
            b = claude.chat(CTO_SYSTEM, cp, max_tokens)
            self.budget.record(claude.provider, b.input_tokens, b.output_tokens)
            self.events.put(("claude", b.text))
        except (BudgetExceeded, ApiError, Exception) as exc:
            self.events.put(("error", str(exc)))

    def _poll(self):
        try: event = self.events.get_nowait()
        except queue.Empty:
            self.root.after(150, self._poll); return
        if event[0] == "error":
            self.progress.stop(); self.send_button.configure(state="normal")
            self._append("system", "安全停止しました。")
            self.status.set("停止: " + event[1]); messagebox.showerror("停止しました", event[1]); return
        if event[0] == "gpt":
            gpt_text = event[1]
            self._append("gpt", gpt_text); self.messages.append(("チャッピー", gpt_text))
            self.status.set("チャッピーが返信しました。Claudeが考えています…")
            self.root.after(150, self._poll)
            return
        claude_text = event[1]
        self._append("claude", claude_text); self.messages.append(("Claude", claude_text))
        self.progress.stop(); self.send_button.configure(state="normal")
        self._save()
        cost = self.budget.summary()["estimated_total_jpy"]
        self.status.set(f"返事が届きました  •  セッション推定料金 {cost}円 / 上限50円")
        self.input.focus_set()

    def _save(self):
        self.transcript.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# AI Business Lab グループ会話", "", f"- モード: {self.session_mode.upper()}",
                 f"- 推定料金: {self.budget.summary()['estimated_total_jpy']}円", ""]
        for name, text in self.messages: lines += [f"## {name}", "", text, ""]
        self.transcript.write_text("\n".join(lines), encoding="utf-8")

    def open_transcript(self):
        if self.transcript and self.transcript.exists(): os.startfile(self.transcript)
        else: messagebox.showinfo("まだ結果がありません", "まずメッセージを送ってください。")


def main():
    root = tk.Tk(); GroupChatApp(root); root.mainloop()


if __name__ == "__main__": main()
