import pandas as pd
import time
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
# from rich.table import Table # Tableは使わなくなったので削除
import json # JSONを扱うためにインポート
# from rich.text import Text # Textは使わなくなったので削除

# utils.py から関数をインポート
from utils import search_web, generate_rakuten_search_url, extract_initial_info, extract_single_watch_info_json # インポートする関数名を修正

# richコンソール初期化
console = Console()

# --- 設定 ---
DEFAULT_INPUT_EXCEL = 'target.xlsx'
DEFAULT_OUTPUT_JSON = 'result.json'
TEST_OUTPUT_JSON = 'result_test.json'
DEFAULT_LIMIT = None # Noneの場合は全件処理
TEST_LIMIT = 2       # テストモード時の処理行数
SLEEP_SECONDS = 1    # APIリクエスト間の待機時間（秒）
MAX_URLS_TO_FETCH = 5 # 最初に取得する商品URLの最大数

def process_row_data(row, row_index, total_rows):
    """Excel行データから初期情報(URL,価格,画像URL)を取得し、各URLの詳細情報を抽出する""" # docstring更新
    initial_keywords = f"{row['ブランド']} {row['型番']} {row['文字盤色']} {row['ブレス形状']} 中古"
    console.print(f"[dim]({row_index+1}/{total_rows})[/dim] 処理開始: [cyan]{initial_keywords}[/cyan]")

    initial_info_list = [] # URL,価格,画像URLのペアリスト
    extracted_watches_details = [] # 個別商品情報のリスト
    initial_search_result_text = None # 初期情報取得時の検索結果テキスト

    try:
        # 1. 検索URL生成 & 初期情報取得クエリ作成
        search_url = generate_rakuten_search_url(initial_keywords)
        # クエリ変更: URL, 価格, 画像URLを要求
        initial_info_query = f"{search_url} から、商品ページのURL (`https://item.rakuten.co.jp/`で始まるもの)、価格、メイン画像のURL(.png/.jpg)を{MAX_URLS_TO_FETCH}件リストアップしてください。"
        console.print(f"  -> 初期情報取得クエリ実行中...")

        # 2. 初期情報リスト取得 (Web検索 + LLM抽出)
        initial_search_result = search_web(initial_info_query)
        initial_search_result_text = initial_search_result # テキスト保存
        initial_info_list = extract_initial_info(initial_search_result, max_results=MAX_URLS_TO_FETCH) # 関数名変更
        print(f"  -> 抽出された初期情報 ({len(initial_info_list)}件):")
        for item in initial_info_list:
            price_str = f"¥{item['price']:,}" if item.get('price') else "N/A"
            print(f"    - URL: {item.get('url', 'N/A')}, 価格: {price_str}, 画像URL: {item.get('image_url', 'N/A')}")

    except Exception as e:
        print(f"  -> 初期情報取得/抽出中にエラー発生: {repr(e)}") # メッセージ変更
        initial_info_list = [] # エラー時は空リスト

    # 3. 個別商品情報取得ループ
    console.print(f"  -> 個別商品ページ情報取得中 ({len(initial_info_list)}件)...") # 変数名修正
    for i, initial_info in enumerate(initial_info_list): # 変数名変更
        product_url = initial_info.get("url")
        initial_price = initial_info.get("price") # 最初に取得した価格
        initial_image_url = initial_info.get("image_url") # 最初に取得した画像URL

        if not product_url:
            console.print(f"    ({i+1}/{len(initial_info_list)}) URLが見つからないためスキップ")
            continue

        console.print(f"    ({i+1}/{len(initial_info_list)}) URL: {product_url}") # 変数名修正
        try:
            # 詳細情報取得クエリ作成 & 実行 (画像URLは含めない)
            detail_query = f"{product_url} の商品ページから詳細情報（名前, 型番, 文字盤色, ブレス形状, 出品者, 保証書日付, 付属品(保証書有無,箱有無,その他記述), 状態）を抽出してください。"
            detail_search_result = search_web(detail_query)

            # 詳細情報抽出
            watch_detail = extract_single_watch_info_json(detail_search_result)

            if watch_detail:
                # URLが抽出できなかった場合、元のURLを補完
                if not watch_detail.get("url"):
                    watch_detail["url"] = product_url

                # 価格を優先的にマージ
                if initial_price is not None:
                    watch_detail["price"] = initial_price
                # 画像URLを追加 (最初のステップで取得したもの)
                watch_detail["image_url"] = initial_image_url

                extracted_watches_details.append(watch_detail)
                # コンソールに主要情報表示 (任意) - 画像URLも表示(短縮)
                price_str_final = f"¥{watch_detail.get('price'):,}" if watch_detail.get('price') else "N/A"
                image_url_short = watch_detail.get('image_url', 'N/A')
                if image_url_short and len(image_url_short) > 30: image_url_short = image_url_short[:27] + "..."
                print(f"      -> 抽出成功: {watch_detail.get('name', 'N/A')} ({watch_detail.get('bracelet_type', 'N/A')}) / {price_str_final} / Img: {image_url_short}")
            else:
                print("      -> 詳細抽出失敗")
                # 詳細抽出失敗時も、URL, 価格, 画像URLは記録
                extracted_watches_details.append({
                    "name": None, "model_number": None, "dial_color": None, "bracelet_type": None,
                    "price": initial_price, "url": product_url, "image_url": initial_image_url, # image_url追加
                    "seller": None, "warranty_date": None,
                    "accessories": {"has_warranty_card": None, "has_box": None, "other_description": "詳細抽出失敗"},
                    "condition": None
                })

            # APIのレート制限を避けるために待機
            time.sleep(SLEEP_SECONDS)

        except Exception as e:
            print(f"    -> URL {product_url} の処理中にエラー発生: {repr(e)}")
            # エラー時も、URL, 価格, 画像URLは記録
            extracted_watches_details.append({
                "name": None, "model_number": None, "dial_color": None, "bracelet_type": None,
                "price": initial_price, "url": product_url, "image_url": initial_image_url, # image_url追加
                "seller": None, "warranty_date": None,
                "accessories": {"has_warranty_card": None, "has_box": None, "other_description": f"処理中エラー: {repr(e)}"},
                "condition": None
            })

    # 結果を辞書で返す (main関数で処理するため)
    return {
        "input_keywords": initial_keywords,
        "search_result_text_for_initial_info": initial_search_result_text,
        "extracted_initial_info": initial_info_list,
        "extracted_results": extracted_watches_details
    }

def main():
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='Excelの時計情報からWeb検索し、結果をJSONファイルに出力するスクリプト')
    parser.add_argument('--test', action='store_true', help='最初の2件のみ処理するテストモード')
    parser.add_argument('--input', default=DEFAULT_INPUT_EXCEL, help=f'入力Excelファイル名 (デフォルト: {DEFAULT_INPUT_EXCEL})')
    parser.add_argument('--output', default=None, help='出力JSONファイル名 (デフォルト: testモード時はresult_test.json, 通常時はresult.json)')
    args = parser.parse_args()

    # 入力/出力ファイルパスと処理行数制限の設定
    input_excel_path = args.input
    limit = TEST_LIMIT if args.test else DEFAULT_LIMIT
    if args.output:
        output_json_path = args.output
    else:
        output_json_path = TEST_OUTPUT_JSON if args.test else DEFAULT_OUTPUT_JSON

    console.print(Panel(f"[bold green]Rolex Search Tool 開始[/bold green]\n"
                        f"入力ファイル: [cyan]{input_excel_path}[/cyan]\n"
                        f"出力ファイル: [cyan]{output_json_path}[/cyan]\n"
                        f"テストモード: {'[bold yellow]有効[/bold yellow]' if args.test else '[dim]無効[/dim]'}",
                        title="設定", border_style="blue"))

    try:
        # 入力Excelファイルを読み込む
        console.print(f"読み込み中: [cyan]{input_excel_path}[/cyan]...")
        df = pd.read_excel(input_excel_path)
        console.print(f"[green]✓[/green] '{input_excel_path}' を読み込みました。")

        # 処理行数を制限 (テストモード時)
        if limit is not None:
            df_process = df.head(limit).copy()
            console.print(f"[yellow]テストモード:[/yellow] 最初の {limit} 行のみ処理します。")
        else:
            df_process = df.copy()
            console.print(f"全 {len(df_process)} 行を処理します。")

        total_rows = len(df_process)
        final_results_list = [] # 最終結果を格納するリスト

        # プログレスバーの設定
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=True # 完了したら消す
        ) as progress:
            task = progress.add_task("[cyan]処理中...", total=total_rows)

            # 各行に関数を適用して結果を取得 (戻り値は辞書)
            for index, row in df_process.iterrows():
                result_data_for_row = process_row_data(row, index, total_rows) # 変数名変更
                final_results_list.append(result_data_for_row) # 辞書をリストに追加
                progress.update(task, advance=1) # プログレスバーを進める

        # 結果をJSONファイルに保存
        console.print(f"\n書き込み中: [cyan]{output_json_path}[/cyan]...")
        try:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(final_results_list, f, ensure_ascii=False, indent=2) # final_results_list を保存
            console.print(Panel(f"[bold green]✓ 処理完了[/bold green]\n結果を '{output_json_path}' に保存しました。",
                                border_style="green"))
        except IOError as e:
             console.print(f"[bold red]エラー:[/bold red] ファイル '{output_json_path}' の書き込み中にエラーが発生しました: {e}")


    except FileNotFoundError:
        console.print(f"[bold red]エラー:[/bold red] ファイル '{input_excel_path}' が見つかりません。")
    except Exception as e:
        console.print(f"[bold red]エラー:[/bold red] 処理中に問題が発生しました。")
        console.print_exception(show_locals=True) # 詳細なエラー情報を表示

if __name__ == "__main__":
    main()
