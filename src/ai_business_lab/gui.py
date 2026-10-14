"""初心者向けのデスクトップ画面。標準ライブラリの tkinter のみを使う。"""
from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from .config import ROOT, load_config
from .meeting import ModeError, make_logger, run_meeting, save_outputs
from .prompts import DEFAULT_THEME


class MeetingApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI Business Lab — 3人でビジネス会議")
        self.root.geometry("760x600")
        self.root.minsize(680, 540)
        self.events: queue.Queue = queue.Queue()
        self.latest_files: tuple[Path, Path] | None = None

        style = ttk.Style()
        style.configure("Title.TLabel", font=("Yu Gothic UI", 18, "bold"))
        style.configure("Step.TLabel", font=("Yu Gothic UI", 11, "bold"))
        style.configure("Start.TButton", font=("Yu Gothic UI", 12, "bold"), padding=12)

        body = ttk.Frame(root, padding=24)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="あなた + チャッピー + Claude", style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text="議題を入力するだけで、2つのAIが話し合って事業案をまとめます。",
                  foreground="#555555").pack(anchor="w", pady=(4, 22))

        ttk.Label(body, text="1  話し合いたいこと", style="Step.TLabel").pack(anchor="w")
        self.theme = tk.Text(body, height=6, wrap="word", font=("Yu Gothic UI", 11), padx=10, pady=10)
        self.theme.pack(fill="x", pady=(8, 20))
        self.theme.insert("1.0", DEFAULT_THEME)

        ttk.Label(body, text="2  会議モード", style="Step.TLabel").pack(anchor="w")
        self.mode = tk.StringVar(value="mock")
        mode_box = ttk.Frame(body)
        mode_box.pack(fill="x", pady=(8, 6))
        ttk.Radiobutton(mode_box, text="無料で練習（おすすめ）", variable=self.mode,
                        value="mock").pack(side="left", padx=(0, 28))
        ttk.Radiobutton(mode_box, text="実際のAIを使う（少額課金）", variable=self.mode,
                        value="real").pack(side="left")
        ttk.Label(body, text="実AIでも1回50円の予算ガードが働きます。開始前にもう一度確認します。",
                  foreground="#666666").pack(anchor="w", pady=(0, 20))

        ttk.Label(body, text="3  会議を開始", style="Step.TLabel").pack(anchor="w")
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=(8, 12))
        self.start_button = ttk.Button(actions, text="会議を開始する", style="Start.TButton",
                                       command=self.start)
        self.start_button.pack(side="left")
        self.open_button = ttk.Button(actions, text="最新の結果を開く", command=self.open_result,
                                      state="disabled")
        self.open_button.pack(side="left", padx=12)

        self.progress = ttk.Progressbar(body, mode="indeterminate")
        self.progress.pack(fill="x", pady=(4, 10))
        self.status = tk.StringVar(value="準備できています。")
        ttk.Label(body, textvariable=self.status, font=("Yu Gothic UI", 10)).pack(anchor="w")
        ttk.Label(body, text="結果はこのPC内の C:\\AI-Business-Lab\\outputs に保存されます。",
                  foreground="#666666").pack(anchor="w", pady=(8, 0))

    def start(self) -> None:
        theme = self.theme.get("1.0", "end").strip()
        if not theme:
            messagebox.showinfo("議題を入力してください", "話し合いたい内容を入力してください。")
            return
        real = self.mode.get() == "real"
        if real:
            cfg = load_config()
            if cfg.use_mock_env or not cfg.openai_key or not cfg.anthropic_key:
                messagebox.showerror("設定を確認してください",
                                     ".env のAPIキーと USE_MOCK=false を確認してください。")
                return
            approved = messagebox.askyesno(
                "実AI会議の確認",
                "OpenAIとAnthropicへ議題を送信します。\n"
                f"この会議の予算上限は {cfg.max_budget_jpy:.0f}円です。\n\n開始しますか？",
            )
            if not approved:
                return

        self.start_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.progress.start(12)
        self.status.set("2つのAIが会議中です。画面を閉じずにお待ちください…")
        threading.Thread(target=self._run, args=(theme, real), daemon=True).start()
        self.root.after(150, self._poll)

    def _run(self, theme: str, real: bool) -> None:
        try:
            cfg = load_config()
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result, budget = run_meeting(cfg, theme, real, make_logger(stamp))
            files = save_outputs(result, budget, ROOT / "outputs", stamp)
            self.events.put(("done", result, budget.summary(), files))
        except ModeError as exc:
            self.events.put(("error", str(exc)))
        except Exception as exc:
            self.events.put(("error", f"会議を開始できませんでした: {exc}"))

    def _poll(self) -> None:
        try:
            event = self.events.get_nowait()
        except queue.Empty:
            self.root.after(150, self._poll)
            return
        self.progress.stop()
        self.start_button.configure(state="normal")
        if event[0] == "error":
            self.status.set("停止しました。設定を確認してください。")
            messagebox.showerror("エラー", event[1])
            return
        _, result, summary, files = event
        self.latest_files = files
        self.open_button.configure(state="normal")
        cost = summary["estimated_total_jpy"]
        if result.status == "completed":
            self.status.set(f"会議が完了しました。推定料金: {cost}円")
            messagebox.showinfo("会議完了", "事業案が完成しました。\n「最新の結果を開く」で確認できます。")
        else:
            self.status.set(f"安全停止しました。{result.stop_reason}")
            messagebox.showwarning("安全停止", result.stop_reason)

    def open_result(self) -> None:
        if self.latest_files:
            os.startfile(self.latest_files[0])


def main() -> None:
    root = tk.Tk()
    MeetingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
