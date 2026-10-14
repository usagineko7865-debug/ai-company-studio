# AI Company Studio — Phase 1

Languages: [日本語](docs/README.ja.md) · [English](docs/README.en.md) · [简体中文](docs/README.zh-CN.md) · [Português (Brasil)](docs/README.pt-BR.md) · [Español](docs/README.es.md)

**あなたが社長になり、ChatGPT役とClaude役のAI役員と事業を育てるローカルWebアプリです。**

普通のマルチAIチャットではなく、会話を事業案として保存し、将来は商品制作・需要検証・販売準備・成功した会社テンプレートの複製までつなげることを目指しています。

## 現在できること

- ChatGPT風のレスポンシブなWeb UI
- あなた・チャッピーCEO・Claude CTOの3人役員会
- 無料モックと実AIの安全な切替
- OpenAI / Anthropic APIの予算ガード
- 会話から事業案を保存
- 会社名・目的・顧客・運営予算の管理
- ダーク／ライト表示
- APIキーと会社データをPC内だけに保存

## 30秒で起動

1. `.env.example` を `.env` にコピー（無料練習だけならキー不要）
2. Windowsで `AI会議を開く.bat` をダブルクリック
3. ブラウザで `http://127.0.0.1:8765` が開く

依存パッケージは不要です。Python 3だけで動作します。

> 現在は需要検証中のPhase 1です。売上や成果を保証するサービスではありません。公開・販売・購入を自動実行しません。

無料版はGitHubで需要を検証し、有料版の定期課金と売上管理はStripeを使う計画です。決済ページはまだ公開していません。設計は [STRIPE_PLAN.md](STRIPE_PLAN.md) にまとめています。

開発計画は [PHASES.md](PHASES.md) を参照してください。

---

## 旧コマンド版について

OpenAI(CEO役)と Claude(CTO役)が最大3往復で議論し、事業案を Markdown と JSON に保存します。
**初期状態はモックモード(APIを一切使わない・無料)です。**

## フォルダ構成
```
AI-Business-Lab/
├─ src/ai_business_lab/   プログラム本体(config / clients / budget / meeting / prompts / mock_data)
├─ tests/test_phase1.py   自動テスト
├─ outputs/               会議記録(.md)と最終提案(.json)の保存先
├─ logs/                  実行ごとのログ
├─ run_mock.bat           モックで実行(ダブルクリック)
├─ run_real.bat           実APIで実行(確認あり)
├─ .env.example           設定ひな形(.env にコピーして使う)
└─ .gitignore             .env / logs / outputs を GitHub に上げない設定
```

## 使い方(モック)
いちばん簡単な方法は、`AI会議を開く.bat` をダブルクリックして Phase 1 の会社画面を使うことです。会社情報、AI役員会、事業案、見た目の設定をタブで切り替えられます。

1. `run_mock.bat` をダブルクリック。
2. `outputs` フォルダの `meeting_日時.md`(会議)と `proposal_日時.json`(最終提案)を開く。
3. 画面と記録には「MOCK」と明示されます。モックの内容は市場調査ではなく動作確認用のサンプルです。

テスト実行: `py tests/test_phase1.py`

## 実APIを使う(料金が発生します)
実APIは **次の3つがすべて揃った時だけ** 動きます。
1. `.env.example` を `.env` にコピーし、`USE_MOCK=false` にする
2. `OPENAI_API_KEY` と `ANTHROPIC_API_KEY` を `.env` に書く(`.env` は絶対に共有・GitHub公開しない)
3. `run_real.bat` から実行(`--real` 付き)

### 先にやること:API側の利用上限(必須)
プログラム内の予算停止は**推定値**で、厳密な課金上限ではありません。必ず各社の管理画面で上限を設定してください。
- OpenAI: Platform の Billing → Limits で月間の Usage limit を設定(前払いクレジット方式なら、チャージ額=最大支出になります)
- Anthropic: Console の Plan & Billing / Limits で月間の Spend limit を設定
- 合計が月3,000円に収まるよう、両社とも少額(例: 各1,000円程度)に。
- モデルと料金(2026-10-14 に公式で確認、`.env.example` に反映済み):
  - OpenAI `gpt-6-luna`: 入力 $0.10 / 出力 $0.50(100万トークンあたり)
  - Anthropic `claude-haiku-5-5`: 入力 $0.10 / 出力 $0.50(プロンプト10万トークン以下の場合)
  - 料金は変わることがあります。実行前に各社の公式 Pricing ページで再確認し、`.env` の `*_USD_PER_M` を更新してください。
  - 初回テストの予算上限は `MAX_BUDGET_JPY=50`(50円)です。

## 安全設計
- 会議は最大3往復(固定)+ CEOによる最終取りまとめ1回
- 呼び出し前に「最悪ケースの料金」を計算し、1回の上限(`MAX_BUDGET_JPY`)を超えるなら停止
- エラー・予算超過時は安全停止し、それまでの記録を保存。自動リトライはしない
- メール送信・公開・課金操作などの外部アクションは実装していません(通信先は公式APIのみ)

## 保存場所について
このプロジェクトは `C:\AI-Business-Lab`(OneDrive の外)にあります。`.env` に書いたAPIキーがクラウドに同期されません。

## Python 3.14 について
外部パッケージを使わない(標準ライブラリのみ)ため、3.14で互換性問題は起きない設計です。
