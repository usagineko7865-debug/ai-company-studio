# AI Company Studio

<p align="center">
  <img src="docs/assets/hero.jpg" alt="AI Company Studio — human founder meeting with two AI executives" width="100%">
</p>

<p align="center"><strong>事業をつくる。成功を証明する。その方法を「複製できる会社」として販売する。</strong></p>

<p align="center">
  <a href="https://github.com/usagineko7865-debug/ai-company-studio/releases/latest">最新版をダウンロード</a> ·
  <a href="#3分で試す">3分で試す</a> ·
  <a href="PHASES.md">開発ロードマップ</a> ·
  <a href="https://github.com/usagineko7865-debug/ai-company-studio/issues">要望・不具合</a>
</p>

日本語 · [English](docs/README.en.md) · [简体中文](docs/README.zh-CN.md) · [Português (Brasil)](docs/README.pt-BR.md) · [Español](docs/README.es.md)

## これは何？

普通の「複数AIを並べただけのチャット」ではありません。あなた・チャッピーCEO・Claude CTOが事業を一緒に育て、実際に成功した手順・判断基準・制作物を会社テンプレートとして商品化し、他の人が複製できる形で販売することを目指す事業開発プラットフォームです。

## 最大の違い — 成功した会社を商品にできる

```text
事業をつくる → 行動と結果を記録する → 成功要因を検証する
→ 再現可能な会社テンプレートにする → 他の人へ販売する
```

販売するのは単なるプロンプト集ではありません。ターゲット、商品設計、価格、作業手順、AI役員の役割、失敗条件、改善履歴を含む「実行できる会社の設計図」です。

> 現在のPhase 1では事業づくりと記録の土台を検証しています。会社テンプレートの生成・出品・購入・作成者への還元はPhase 5までに段階的に実装する計画で、現時点ではまだ販売できません。

| 一般的なAIチャット | AI Company Studio |
|---|---|
| 質問に回答して終わる | CEOが提案し、CTOが弱点と実行方法を検証 |
| 会話が流れていく | 会話を事業案として保存 |
| 1つのAI視点 | 役割の異なるAI役員会 |
| API料金が分かりにくい | 呼び出し前に予算ガード |
| 成果は本人だけのもの | 成功手順を会社テンプレートとして販売（Phase 5） |

## 現在できること

- あなた・チャッピーCEO・Claude CTOのグループ会話
- 料金のかからない無料練習モード
- OpenAI / Anthropicを使う実AIモード
- API利用前の予算ガード
- 会話から事業案を保存
- 成功条件・証拠・再現手順・失敗条件を会社テンプレートとして保存
- 会社テンプレートを安全なJSONで書き出し／読み込み
- 会社の目的・顧客・運営予算を管理
- 日本語・英語・簡体字中国語・ポルトガル語・スペイン語
- スマホ対応、ライト／ダーク表示
- APIキーと会社データはPC内に保存
- アプリ内から改善要望・有料ベータ参加希望を送信
- 起動回数・役員会回数・保存数を端末内だけで確認

## 3分で試す

### 起動方法

1. [最新版](https://github.com/usagineko7865-debug/ai-company-studio/releases/latest)から `AI-Company-Studio-Windows-...zip` をダウンロードして展開
2. `AI-Company-Studio.exe` をダブルクリック
3. ブラウザで `http://127.0.0.1:8765` が開く

Windows 10 / 11に対応し、PythonやAPIキーの用意は不要です。現在はコード署名前のため、Windowsが「未確認の発行元」と表示する場合があります。ソースから起動したい開発者は [BUILD.md](BUILD.md) を参照してください。

## 実AIを使う場合

1. `.env.example` を複製して `.env` に変更
2. `.env` にOpenAIとAnthropicのAPIキーを自分で入力
3. `USE_MOCK=false` に変更
4. 画面右上の「実AI」をONにする

> `.env` はGitHubやチャットに共有しないでください。実AIへの送信前には確認画面が表示され、少額のAPI料金が発生します。

## 安全設計

- 初期状態は無料練習モード
- サーバーはPC内の `127.0.0.1` だけで待受
- `.env`、会話ログ、会社データはGit管理対象外
- 呼び出し前に最大料金を推定し、設定予算を超える場合は停止
- 公開・販売・購入・メール送信を自動実行しない
- エラー時の自動リトライなし

## 現在の位置づけ

これは需要検証中の **Phase 1 Preview** です。売上や成果を保証するものではありません。無料版への反応を確認しながら改善し、有料版の定期課金・売上管理にはStripeを使う予定です。決済はまだ開始していません。

- 開発計画: [PHASES.md](PHASES.md)
- Stripe設計案: [STRIPE_PLAN.md](STRIPE_PLAN.md)
- 会社テンプレートの仕様: [docs/COMPANY_TEMPLATE.md](docs/COMPANY_TEMPLATE.md)
- 販売開始の判定表: [VALIDATION.md](VALIDATION.md)
- セキュリティ報告: [SECURITY.md](SECURITY.md)
- 開発への参加: [CONTRIBUTING.md](CONTRIBUTING.md)

## 開発者向け

```powershell
$env:PYTHONPATH="src"
py -m ai_business_lab.web_server
```

テスト:

```powershell
py tests/test_phase1.py
```

Railwayへ無料練習モード専用の公開デモを配備する場合は、[DEPLOY_RAILWAY.md](DEPLOY_RAILWAY.md)を参照してください。公開デモではAPIキーと共有データを扱いません。

外部Pythonパッケージを使わず、標準ライブラリだけで動作します。

## ライセンス

現在は需要検証中のため、ライセンスをまだ確定していません。ソースコードの著作権は作者に留保されます。閲覧と個人での試用はできますが、再配布・商用利用の条件は正式ライセンス決定後に明示します。
