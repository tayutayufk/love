# Rolex Search Tool (rolex-search)

## 概要

このツールは、Excelファイル (`target.xlsx`) に記載された時計の情報（ブランド、型番、文字盤色、ブレス形状）をもとに、Web検索 (Tavily API) を行い、中古市場での価格候補や詳細情報（出品者、保証書日付、付属品、状態など）を自動で収集し、結果を新しいExcelファイル (`result.xlsx` または `result_test.xlsx`) に出力します。

## 機能

*   指定されたExcelファイル (`target.xlsx` がデフォルト) を入力として読み込みます。
*   各行の時計情報から検索クエリを自動生成します。
*   Tavily APIを利用してWeb検索を実行し、関連情報を取得します。
*   検索結果のテキストから、OpenAI APIを用いて各種情報を取得します
*   抽出した情報と元のデータを結合し、新しいExcelファイル (`result.xlsx` またはテストモード時は `result_test.xlsx`) に保存します。
*   コマンドライン引数により、テストモード (`--test`) での実行（最初の5件のみ処理）や、入出力ファイル名の指定 (`--input`, `--output`) が可能です。

## 必要なもの

*   Python 3.8 以上
*   [uv](https://github.com/astral-sh/uv) (Pythonパッケージ管理ツール)
*   OpenAI API キー
*   `rich` ライブラリ (コンソール出力整形用、`uv sync` で自動インストールされます)
*   Tavily Search API(https://tavily.com/)

## セットアップ

1.  **リポジトリの準備:**
    このプロジェクトのファイルを任意のディレクトリに配置します。

2.  **依存関係のインストール:**
    ターミナル（PowerShellなど）を開き、プロジェクトのディレクトリに移動して以下のコマンドを実行します。
    ```powershell
    uv sync
    ```

3.  **OpenAI API キーの設定:**
    `utils.py` が `.env` ファイルを読み込みます。
    プロジェクトルートに `.env` という名前のファイルを作成し、以下のように記述してご自身のOpenAI API及びTavily APIキーを設定してください。
    ```dotenv
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
    TAVILY_API_KEY="YOUR_TAVILY_API_KEY"
    ```
    `.env` ファイルは `.gitignore` によってGitの追跡対象から除外されるため、APIキーが誤ってリポジトリにコミットされるのを防ぎます。

4.  **入力ファイルの準備:**
    `target.xlsx` ファイルに、検索したい時計の情報を入力します。以下の列が必要です。
    *   `ブランド` (例: ROLEX)
    *   `型番` (例: 126500LN)
    *   `文字盤色` (例: ブラック)
    *   `ブレス形状` (例: オイスター)

## 使い方

ターミナル（PowerShellなど）でプロジェクトディレクトリに移動し、以下のコマンドを実行します。

*   **通常実行 (全件処理):**
    ```powershell
    $env:PYTHONIOENCODING='utf-8'; uv run python ./src/process_excel.py
    ```
    `target.xlsx` を読み込み、全件を処理して `result.xlsx` に結果を出力します。
    (Windows環境で文字化けが発生する場合は、`$env:PYTHONIOENCODING='utf-8';` を先頭に追加してください。)

*   **テスト実行 (最初の5件のみ):**
    ```powershell
    $env:PYTHONIOENCODING='utf-8'; uv run python ./src/process_excel.py --test
    ```
    `target.xlsx` を読み込み、最初の5件のみ処理して `result_test.xlsx` に結果を出力します。

*   **入出力ファイルを指定して実行:**
    ```powershell
    $env:PYTHONIOENCODING='utf-8'; uv run python ./src/process_excel.py --input 入力ファイル名.xlsx --output 出力ファイル名.xlsx
    ```
    依存関係 (`pyproject.toml`) を更新した場合は、再度 `uv sync` を実行して環境を同期してください。
    スクリプト実行時には、`rich` ライブラリによって整形された見やすいコンソール出力（設定情報、進行状況バー、各アイテムの検索結果、完了メッセージなど）が表示されます。

## ファイル構成

```
.
├──　*data/                     # 入出力データを格納するディレクトリ
|   ├── result.xlsx             # 通常実行時の出力結果ファイル (実行後に生成)
|   ├── result_test.xlsx        # テスト実行時の出力結果ファイル (実行後に生成)
|   └── target.xlsx             # 検索対象の時計情報を入力するExcelファイル (サンプル)
|
├── *src/                       #ベースラインを格納するディレクトリ
|   ├── process_excell.py       # Excel処理を実行するメインスクリプト
|   ├── tavily_processor.py     # Tavily APIを実行するスクリプト
|   └── watch_info_extractor.py # テキストから時計情報を抽出するスクリプト              # 
|
├──　*test/
|   ├── result/                 #テスト結果を格納するディレクトリ
|   ├── tavily_processor.py     # Tavily APIを実行するスクリプト
|   └── watch_info_extractor.py # テキストから時計情報を抽出するスクリプト
|          
├── analyze_excel.py      # 結果ファイル (result_test.xlsx) を分析するサンプルスクリプト
├── main.py               # utils.py の関数をテストするためのサンプルスクリプト (実行には不要)
├── utils.py              # Web検索、価格抽出、詳細抽出などのコア関数群
├── pyproject.toml        # プロジェクト設定と依存関係 (uv用)
├── README.md             # このファイル
├── result.xlsx           # 通常実行時の出力結果ファイル (実行後に生成)
├── result_test.xlsx      # テスト実行時の出力結果ファイル (実行後に生成)
├── target.xlsx           # 検索対象の時計情報を入力するExcelファイル (サンプル)
├── .env                  # OpenAI APIキーを記述するファイル (Git管理外)
├── .gitignore            # Gitで無視するファイルを指定するファイル
└── uv.lock               # uvが生成するロックファイル
```

## 注意点

*   Web検索結果からの情報抽出精度は、検索エンジンの結果や対象となるWebサイトの構造に大きく依存します。特に詳細情報（出品者、保証書日付、付属品、状態など）は、必ずしも正確に抽出できるとは限りません。抽出ロジック (`utils.py` 内の `extract_details` 関数) は改善の余地があります。
*   価格抽出 (`utils.py` 内の `extract_prices` 関数) は、¥マークや「円」表記、特定のパターン（例: `価格： XXXX`）に基づいていますが、Webサイトによっては抽出できない場合があります。また、妥当な価格範囲（10万円〜1億円未満）でフィルタリングしています。
*   OpenAI API の利用には、従量課金が発生する場合があります。利用量にご注意ください。
*   APIキーは機密情報です。`.env` ファイルに記述し、このファイルがGitリポジトリに含まれないように注意してください (`.gitignore` で設定済み)。
