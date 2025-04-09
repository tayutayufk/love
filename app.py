import gradio as gr
import pandas as pd
import time
import json
import os
from pathlib import Path
import tempfile
import shutil
import sys
import logging  # コンソールの代わりにロギングを使用

# ロガーの設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# srcディレクトリをPythonパスに追加
# これにより、src内のモジュールを直接インポートできる
SRC_DIR = Path(__file__).parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

# 既存の処理ロジックをインポート
try:
    from tavily_processor import tavily_processor
    from watch_info_extractor import WatchInfoExtractor

    # process_excel.py から必要な定数をインポート
    from process_excel import DATA_DIR, SLEEP_SECONDS, MAX_URLS_TO_FETCH, ADVANCE_SEARCH
except ImportError as e:
    logging.error(f"必要なモジュールのインポートに失敗しました: {e}")
    # Gradioアプリ起動前にエラーを表示する方法があれば良いが、ここではログ出力に留める
    # UI上でエラーメッセージを表示するなどの対応も考えられる
    raise  # アプリケーションを停止させる


# --- Gradio 用の処理関数 ---
# def process_excel_gradio(input_file_obj, progress=gr.Progress(track_tqdm=True)): # Progressを一時的に削除
def process_excel_gradio(input_file_obj):
    """Gradioインターフェース用のExcel処理関数"""
    if input_file_obj is None:
        return pd.DataFrame(), "エラー: 入力ファイルが指定されていません。"

    # input_file_obj は Gradio の File コンポーネントが返すオブジェクト
    # .name 属性に一時ファイルのパスが含まれる
    input_excel_path = Path(input_file_obj.name)
    logging.info(f"処理対象ファイル: {input_excel_path}")

    try:
        # APIクライアントの初期化 (環境変数からAPIキーを読み込む想定)
        logging.info("APIクライアントを初期化中...")
        tavily_client = tavily_processor()
        watch_extractor = WatchInfoExtractor()
        logging.info("APIクライアントの初期化完了。")

        # Excelファイルを読み込む
        logging.info(f"Excelファイルを読み込み中: {input_excel_path}")
        df = pd.read_excel(input_excel_path)
        total_rows = len(df)
        logging.info(f"Excelファイルの読み込み完了。処理対象: {total_rows}行")
        results_list = []

        # progress(0, desc="処理開始...") # Progressを一時的に削除

        # 各行を処理
        for index, row in df.iterrows():
            # # 進捗を更新 (Progressを一時的に削除)
            # current_progress = (index + 1) / total_rows
            # progress(current_progress, desc=f"処理中: {index + 1}/{total_rows}行目")

            # Excelからデータを安全に取得 (列が存在しない場合も考慮)
            brand = row.get("ブランド", "")
            model = row.get("型番", "")
            dial_color = row.get("文字盤色", "")
            bracelet = row.get("ブレス形状", "")
            initial_keywords = f"{brand} {model} {dial_color} {bracelet} 中古".strip()  # 空白を除去

            logging.info(f"({index+1}/{total_rows}) 処理開始: {initial_keywords}")

            search_results = []
            extracted_watches_details = []
            row_error = None  # 行レベルのエラーを記録

            try:
                # Tavily検索
                logging.info(f"  -> 商品検索クエリ実行中: {initial_keywords}")
                search_results = tavily_client.search_item(
                    initial_keywords, max_results=MAX_URLS_TO_FETCH, advance_search=ADVANCE_SEARCH
                )
                logging.info(f"  -> 検索結果 ({len(search_results)}件)")

                # 個別商品情報抽出
                logging.info(f"  -> 個別商品ページ情報取得中 ({len(search_results)}件)...")
                for i, item in enumerate(search_results):
                    product_url = item.get("url")
                    product_content = item.get("content")

                    if not product_url or not product_content:
                        logging.warning(f"    ({i+1}/{len(search_results)}) URL/コンテンツなしでスキップ")
                        continue

                    logging.info(f"    ({i+1}/{len(search_results)}) URL: {product_url}")
                    try:
                        watch_detail = watch_extractor.extract_info(product_content)
                        if watch_detail:
                            watch_detail["url"] = product_url
                            extracted_watches_details.append(watch_detail)
                            price_str = f"¥{watch_detail.get('price'):,}" if watch_detail.get("price") else "N/A"
                            logging.info(
                                f"      -> 抽出成功: {watch_detail.get('name', 'N/A')} ({watch_detail.get('model_number', 'N/A')}) / {price_str}"
                            )
                        else:
                            logging.warning("      -> 詳細抽出失敗")
                            # 抽出失敗時もURLとエラー情報を記録
                            extracted_watches_details.append({"url": product_url, "error": "詳細抽出失敗"})
                    except Exception as e_extract:
                        logging.error(f"    -> URL {product_url} の処理中にエラー発生: {repr(e_extract)}")
                        # 抽出エラー時もURLとエラー情報を記録
                        extracted_watches_details.append(
                            {"url": product_url, "error": f"抽出エラー: {repr(e_extract)}"}
                        )

                    # APIのレート制限を避けるために待機
                    time.sleep(SLEEP_SECONDS)

            except Exception as e_row:
                logging.error(f"  -> 行 {index+1} の処理中にエラー発生: {repr(e_row)}")
                row_error = f"行処理エラー: {repr(e_row)}"
                # 行全体のエラーの場合、空の結果とエラーメッセージを記録

            # 行の結果をリストに追加
            results_list.append(
                {
                    "input_keywords": initial_keywords,
                    "extracted_results": extracted_watches_details,
                    "row_error": row_error,  # 行レベルのエラーを追加
                }
            )

        # --- 結果をDataFrameに整形 ---
        logging.info("処理結果をDataFrameに整形中...")
        output_data = []
        # JSONの全キーを列名として定義（accessories内のキーも展開）
        columns = [
            "検索キーワード",
            "商品名",
            "型番",
            "文字盤色",
            "ブレス形状",
            "価格",
            "販売店",
            "保証書日付",
            "保証書あり",
            "箱あり",
            "付属品詳細",
            "状態",
            "URL",
            "エラー",
        ]

        for result in results_list:
            keywords = result["input_keywords"]
            row_err = result["row_error"]

            if row_err:  # 行レベルのエラーがあった場合
                error_row = {col: "" for col in columns}  # 全ての列を空にする
                error_row["検索キーワード"] = keywords
                error_row["エラー"] = row_err
                output_data.append(error_row)

            elif not result["extracted_results"]:  # 検索結果が0件の場合
                no_result_row = {col: "" for col in columns}  # 全ての列を空にする
                no_result_row["検索キーワード"] = keywords
                no_result_row["商品名"] = "該当なし"
                output_data.append(no_result_row)

            else:  # 検索結果がある場合
                for detail in result["extracted_results"]:
                    accessories = detail.get("accessories", {})  # Noneの場合も考慮
                    if accessories is None:  # accessoriesがNoneの場合のフォールバック
                        accessories = {}
                    output_row = {
                        "検索キーワード": keywords,
                        "商品名": detail.get("name", "N/A"),
                        "型番": detail.get("model_number", "N/A"),
                        "文字盤色": detail.get("dial_color", "N/A"),
                        "ブレス形状": detail.get("bracelet_type", "N/A"),
                        "価格": f"¥{detail.get('price'):,}" if detail.get("price") is not None else "N/A",
                        "販売店": detail.get("seller", "N/A"),
                        "保証書日付": detail.get("warranty_date", "N/A"),
                        "保証書あり": accessories.get("has_warranty_card", False),  # デフォルトFalse
                        "箱あり": accessories.get("has_box", False),  # デフォルトFalse
                        "付属品詳細": accessories.get("other_description", ""),  # デフォルト空文字
                        "状態": detail.get("condition", "N/A"),
                        "URL": detail.get("url", "N/A"),
                        "エラー": detail.get("error", ""),  # 抽出エラーなど
                    }
                    output_data.append(output_row)

        # 定義した列順序でDataFrameを作成
        output_df = pd.DataFrame(output_data, columns=columns)
        logging.info("DataFrameの整形完了。")
        return output_df, "処理が完了しました。"

    except FileNotFoundError:
        logging.error(f"エラー: ファイルが見つかりません - {input_excel_path}")
        return pd.DataFrame(), f"エラー: ファイル '{input_excel_path.name}' が見つかりません。"
    except ImportError:
        # mainレベルのImportErrorは上でキャッチされるはずだが念のため
        logging.critical("重大なエラー: 必要なモジュールが見つかりません。")
        return pd.DataFrame(), "エラー: アプリケーションの初期化に失敗しました。ログを確認してください。"
    except Exception as e:
        logging.exception("エラー: 処理中に予期せぬ問題が発生しました。")  # スタックトレースもログに出力
        return pd.DataFrame(), f"エラー: 処理中に問題が発生しました。詳細: {repr(e)}"
    finally:
        # Gradioは一時ファイルを自動で削除するはずだが、念のため確認
        if input_excel_path.exists() and "gradio" in str(input_excel_path):
            try:
                # os.remove(input_excel_path) # Gradioが管理するので不要かも
                logging.info(f"一時ファイル {input_excel_path} はGradioによって管理されます。")
            except OSError as e:
                logging.warning(f"一時ファイル {input_excel_path} の削除に失敗しました: {e}")


# --- Gradio UIの定義 ---
# data/input ディレクトリ内のExcelファイルを取得
input_dir = DATA_DIR / "input"
excel_files = []
if input_dir.exists() and input_dir.is_dir():
    excel_files = sorted([f.name for f in input_dir.glob("*.xlsx")])  # ソートして表示順を安定させる
    logging.info(f"検出されたExcelファイル: {excel_files}")
else:
    logging.warning(f"入力ディレクトリが見つかりません: {input_dir}")

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# Excel 時計情報 検索・抽出ツール")
    gr.Markdown(
        "`data/input` 内のExcelファイルを選択するか、新しいファイルをアップロードして「実行」ボタンを押してください。"
    )

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 入力設定")
            # data/input内のファイルを選択するドロップダウン
            file_dropdown = gr.Dropdown(
                label="既存のファイルを選択",
                choices=excel_files,
                value=excel_files[0] if excel_files else None,
                # ファイルがない場合は非表示にするか、メッセージを表示する
                info=(
                    "`data/input` ディレクトリ内の .xlsx ファイルが表示されます。"
                    if excel_files
                    else "`data/input` に .xlsx ファイルが見つかりません。"
                ),
                interactive=bool(excel_files),  # ファイルがない場合は操作不可
            )
            # # または、ファイルをアップロード (一時的にコメントアウト)
            # file_upload = gr.File(
            #     label="または、Excelファイルをアップロード",
            #     file_types=[".xlsx"],
            # )
            run_button = gr.Button("実行", variant="primary")
            status_text = gr.Textbox(label="ステータス", interactive=False, lines=1)

        with gr.Column(scale=3):
            gr.Markdown("### 処理結果")
            output_table = gr.DataFrame(label="抽出結果")  # TextboxからDataFrameに戻す
            # output_text = gr.Textbox(label="抽出結果 (テキスト)", lines=15, interactive=False) # DataFrameを使うので削除

    # --- イベントハンドラ ---
    # ファイルがアップロードされたら、ドロップダウンの選択を解除
    def clear_dropdown_on_upload(uploaded_file):
        if uploaded_file is not None:
            return gr.Dropdown(value=None)  # ドロップダウンの選択を解除
            # アップロードがクリアされた場合などは元の値を維持 (あるいはNoneのまま)
            # この動作は要件次第
            return gr.Dropdown()  # 現状維持

    # # file_upload.upload(fn=clear_dropdown_on_upload, inputs=[file_upload], outputs=[file_dropdown]) # 一時的にコメントアウト

    # # ドロップダウンが選択されたら、アップロードされたファイルをクリア (不要に)
    # def clear_upload_on_select(dropdown_value):
    #     if dropdown_value is not None:
    #         return gr.File(value=None)
    #         return gr.File()

    # # file_dropdown.change(fn=clear_upload_on_select, inputs=[file_dropdown], outputs=[file_upload]) # 一時的にコメントアウト

    # 実行ボタンのクリックイベント (ファイルアップロードを除外, Progressを除外)
    # def run_processing_wrapper(dropdown_choice, progress=gr.Progress(track_tqdm=True)):
    def run_processing_wrapper(dropdown_choice):
        """実行ボタンクリック時の処理 (ドロップダウンのみ)"""
        target_file_obj = None
        source_description = ""

        if dropdown_choice is not None:
            # ドロップダウンで選択されたファイルを使用
            file_path = input_dir / dropdown_choice
            source_description = f"選択されたファイル ({dropdown_choice})"
            if not file_path.exists():
                logging.error(f"選択されたファイルが見つかりません: {file_path}")
                return pd.DataFrame(), f"エラー: 選択されたファイル '{dropdown_choice}' が見つかりません。"

            # GradioのFileコンポーネントはファイルオブジェクトを期待するため、
            # 選択されたファイルを一時ディレクトリにコピーして、そのオブジェクトを渡す
            try:
                # 一時ファイルを作成 (接尾辞を元のファイルに合わせる)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                    shutil.copyfile(file_path, tmp_file.name)
                    logging.info(f"選択されたファイル {file_path} を一時ファイル {tmp_file.name} にコピーしました。")

                    # GradioのFileコンポーネントが返すオブジェクトを模倣
                    # Gradio内部で使われるかもしれない属性も設定しておく
                    class MockFile:
                        def __init__(self, name, orig_name):
                            self.name = name  # 一時ファイルのフルパス
                            self.orig_name = orig_name  # 元のファイル名

                    mock_file_obj = MockFile(tmp_file.name, dropdown_choice)

                    logging.info(f"処理を開始します。ソース: {source_description}")
                    # result_df, status = process_excel_gradio(mock_file_obj, progress) # Progressを除外
                    result_df, status = process_excel_gradio(mock_file_obj)  # DataFrameが返る

                    # 処理後、一時ファイルを削除
                    # process_excel_gradio内で削除しようとすると、Gradioがまだ掴んでいる可能性があるため、ここで削除
                    try:
                        os.remove(tmp_file.name)
                        logging.info(f"一時ファイル {tmp_file.name} を削除しました。")
                    except OSError as e:
                        logging.warning(f"一時ファイル {tmp_file.name} の削除に失敗しました: {e}")

                    # DataFrameをそのまま返す
                    return result_df, status

            except Exception as e:
                logging.exception(f"ドロップダウンファイルの処理中にエラーが発生しました: {dropdown_choice}")
                error_msg = f"エラー: ファイル '{dropdown_choice}' の処理中に問題が発生しました。詳細: {repr(e)}"
                # エラー時は空のDataFrameとエラーステータスを返す
                return pd.DataFrame(), error_msg
        else:
            # ファイルが選択されていない場合
            logging.warning("実行ボタンが押されましたが、ファイルが選択されていません。")
            # 空のDataFrameとメッセージを返す
            return pd.DataFrame(), "ファイルを選択してください。"

    run_button.click(
        fn=run_processing_wrapper,
        inputs=[file_dropdown],  # file_upload を削除
        outputs=[output_table, status_text],  # output_text を output_table に変更
        # APIコールを無効化 (UIのテスト用)
        # api_name="run_processing"
    )

if __name__ == "__main__":
    # 環境変数からポート番号を取得、なければデフォルト値
    port = int(os.environ.get("GRADIO_PORT", 7860))
    logging.info(f"Gradioアプリケーションをポート {port} で起動します...")
    # share=True にするとパブリックURLが生成される
    demo.launch(server_name="0.0.0.0", server_port=port, share=True)
