"""実行入口: py -m ai_business_lab  (src フォルダ内、または run.bat 経由)"""
import argparse
import sys
from datetime import datetime

from . import prompts
from .config import ROOT, load_config
from .meeting import ModeError, make_logger, run_meeting, save_outputs


def main(argv=None) -> int:
    for s in (sys.stdout, sys.stderr):  # Windowsの文字化け対策
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="AI Business Lab Phase 1: AI同士の自動会議")
    ap.add_argument("--real", action="store_true",
                    help="実APIを使う(.env の USE_MOCK=false も必要。料金が発生します)")
    ap.add_argument("--theme", default=prompts.DEFAULT_THEME, help="会議のテーマ")
    args = ap.parse_args(argv)

    cfg = load_config()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log = make_logger(stamp)

    if args.real and cfg.use_mock_env:
        print("⚠ --real が指定されましたが、.env が USE_MOCK=true のためモックで実行します。")
        print("   実APIを使うには .env の USE_MOCK=false にしてください。")

    try:
        res, budget = run_meeting(cfg, args.theme, args.real, log)
    except ModeError as e:
        log.error("モード設定エラー: %s", e)
        print(f"❌ {e}")
        return 2

    md, js = save_outputs(res, budget, ROOT / "outputs", stamp)
    s = budget.summary()
    print(f"\n=== モード: {'🟡 MOCK(サンプル応答)' if res.mode == 'MOCK' else '🟢 REAL(実API)'} / 状態: {res.status} ===")
    if res.stop_reason:
        print(f"備考: {res.stop_reason}")
    print(f"推定料金: {s['estimated_total_jpy']}円 / 上限 {s['limit_jpy']}円  (推定値。正式な上限は各社の管理画面で設定)")
    for k, v in s["providers"].items():
        print(f"  {k}: {v['calls']}回 入力{v['input_tokens']} 出力{v['output_tokens']}トークン")
    print(f"会議記録: {md}\n最終提案: {js}\nログ: {ROOT / 'logs' / f'run_{stamp}.log'}")
    return 0 if res.status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
