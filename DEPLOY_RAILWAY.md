# Railway公開デモ配備手順

この設定は **無料練習モード専用の公開デモ** です。共有サーバーへAPIキー、会話履歴、会社データを置きません。

## 安全設定

- `PUBLIC_DEMO=true`：会社・事業・テンプレートの保存APIを無効化
- `USE_MOCK=true`：OpenAI / Anthropicを呼び出さない
- `.dockerignore`：`.env`、ログ、会社データ、出力物をコンテナへ含めない
- `/health`：Railwayの稼働確認用
- `HOST=0.0.0.0` と Railwayの `PORT` に対応

## Railwayで設定する環境変数

```text
PUBLIC_DEMO=true
USE_MOCK=true
```

OpenAI / AnthropicのAPIキーは設定しないでください。

## 配備前確認

1. `py tests/test_phase1.py` が成功すること
2. Dockerイメージ内に `.env` が含まれないこと
3. `/health` が `status: ok` を返すこと
4. 公開画面で実AIをONにすると403で拒否されること
5. 保存操作が403で拒否されること

## TrendPulseから切り替える場合

TrendPulseのVolumeを先にバックアップし、既存サービスを停止してから新しいAI Company Studioサービスを作成します。古いサービスを直接上書きせず、公開デモの動作確認後にTrendPulseを削除します。
