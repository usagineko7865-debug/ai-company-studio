# Windows実行ファイルの作成

通常の利用者は、GitHub ReleasesにあるWindowsアプリ版ZIPを展開し、`AI-Company-Studio.exe` を使うためPythonは不要です。

開発者が再ビルドする場合:

ビルド専用の仮想環境でPyInstallerを使い、`src/ai_business_lab/launcher.py` を起点として `web` フォルダを同梱します。生成物は `dist\AI-Company-Studio\AI-Company-Studio.exe` と必要なランタイム一式です。フォルダ内のファイルはまとめて配布してください。APIキーや `.env`、会社データは含めません。

## 注意

現在の実行ファイルはコード署名されていません。Windowsが未確認の発行元として警告する場合があります。一般販売前にはコード署名証明書を取得し、署名済みインストーラーを用意します。
