# Stripe販売・売上管理計画

AI Company Studioの有料版は、Stripe BillingとStripe Checkoutを使う想定です。現時点では設計だけで、商品作成・決済受付・公開は行っていません。

## 最初の構成

- 無料版: GitHubで公開し、需要と利用状況を確認
- 有料版: Stripe Checkoutで月額契約
- 契約変更・解約: Stripe Customer Portal
- 売上、返金、未払い: Stripe Dashboardで管理
- アプリの利用権: Webhookで契約状態を同期

## 商品の分け方

- AI Company Studio Cloud（月額980円）
- AI Company Studio Company（月額2,980円）

Stripeではプランごとに別Productを作り、月払い・年払いを用意する場合だけ同じProductに複数Priceを付けます。

## 安全な実装順

1. Stripeの独立したSandboxでテストする
2. Checkout、Customer Portal、Webhookを実装する
3. `checkout.session.completed`、`checkout.session.async_payment_succeeded`、`customer.subscription.*`、`invoice.paid`、`invoice.payment_failed`を処理する
4. Webhook署名を必ず検証する
5. 制限付きAPIキーをサーバー側の秘密保管庫に置く
6. テスト決済・解約・支払失敗を確認後、公開直前に本番設定を行う

## 税金について

海外販売では消費税・VAT・sales taxの確認が必要です。Stripe Taxを有効にするだけでは徴収されず、対象地域の税務登録が必要です。登録状況を確認してから設定します。
