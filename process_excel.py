import pandas as pd
import time
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
import json # JSONを扱うためにインポート
from rich.text import Text

# utils.py から関数をインポート
# from utils import search_web, extract_prices, extract_details # 古い関数を削除
# from utils import search_web, extract_watch_info_json # 古い関数を削除
from utils import search_web, extract_multiple_watch_info_json # 新しい関数をインポート

# richコンソール初期化
console = Console()

# --- 設定 ---
DEFAULT_INPUT_EXCEL = 'target.xlsx'
# DEFAULT_OUTPUT_EXCEL = 'result.xlsx' # JSON出力に変更
# TEST_OUTPUT_EXCEL = 'result_test.xlsx' # JSON出力に変更
DEFAULT_OUTPUT_JSON = 'result.json'
TEST_OUTPUT_JSON = 'result_test.json'
DEFAULT_LIMIT = None # Noneの場合は全件処理
TEST_LIMIT = 2       # テストモード時の処理行数 (5から2に変更)
SLEEP_SECONDS = 1    # APIリクエスト間の待機時間（秒）

def process_row_data(row, row_index, total_rows):
    """Excelの行データからクエリを作成し、価格候補、詳細情報、検索結果テキストを取得する"""
    # クエリを作成
    query = f"楽天市場 {row['ブランド']} {row['型番']} {row['文字盤色']} {row['ブレス形状']} 中古品 \n"
    query += f"楽天市場 URL :https://www.rakuten.co.jp/ \n"
    query += "検索結果には、価格、商品ページのURL、出品者、保証書日付、付属品、状態を含めてください。\n"
    console.print(f"[dim]({row_index+1}/{total_rows})[/dim] 検索中: [cyan]{query}[/cyan]")
    # print(f"({row_index+1}/{total_rows}) 検索中: {query}")

    search_result_text = None # 検索結果テキストを初期化
    extracted_watches_list = [] # 抽出結果(辞書のリスト)を初期化

    try:
        search_result = search_web(query)
        search_result_text = search_result # 生テキストを保存

        # 複数の時計情報をJSONオブジェクトのリストとして抽出
        extracted_watches_list = extract_multiple_watch_info_json(search_result)

        if extracted_watches_list:
            # 結果表示 (抽出された情報のリストを表示)
            print(f"  抽出結果 ({len(extracted_watches_list)}件):")
            for i, watch_info in enumerate(extracted_watches_list):
                 print(f"    --- 商品 {i+1} ---")
                 # 見やすいように主要情報だけ表示（例）
                 print(f"      名前: {watch_info.get('name', 'N/A')}")
                 price_val = watch_info.get('price')
                 print(f"      価格: {f'¥{price_val:,}' if price_val else 'N/A'}")
                 print(f"      URL: {watch_info.get('url', 'N/A')}")
                 print(f"      出品者: {watch_info.get('seller', 'N/A')}")
        else:
            # 抽出失敗または結果なし
            print("  -> 抽出結果なし または 抽出失敗")

        # APIのレート制限を避けるために少し待機
        time.sleep(SLEEP_SECONDS)

    except Exception as e:
        print(f"  -> エラー発生: {repr(e)}") # Use standard print and repr(e)
        extracted_watches_list = [] # エラー時は空リスト

    # 結果を辞書で返す (main関数で処理するため)
    return {
        "input_query": query,
        "search_result_text": search_result_text,
        "extracted_results": extracted_watches_list # 辞書のリスト
    }

def main():
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='Excelの時計情報からWeb検索し、結果をJSONファイルに出力するスクリプト') # 説明変更
    parser.add_argument('--test', action='store_true', help='最初の2件のみ処理するテストモード') # ヘルプ変更
    parser.add_argument('--input', default=DEFAULT_INPUT_EXCEL, help=f'入力Excelファイル名 (デフォルト: {DEFAULT_INPUT_EXCEL})')
    parser.add_argument('--output', default=None, help='出力JSONファイル名 (デフォルト: testモード時はresult_test.json, 通常時はresult.json)') # ヘルプ変更
    args = parser.parse_args()

    # 入力/出力ファイルパスと処理行数制限の設定
    input_excel_path = args.input
    limit = TEST_LIMIT if args.test else DEFAULT_LIMIT
    if args.output:
        output_json_path = args.output # 変数名変更
    else:
        output_json_path = TEST_OUTPUT_JSON if args.test else DEFAULT_OUTPUT_JSON # 変数名変更

    console.print(Panel(f"[bold green]Rolex Search Tool 開始[/bold green]\n"
                        f"入力ファイル: [cyan]{input_excel_path}[/cyan]\n"
                        f"出力ファイル: [cyan]{output_json_path}[/cyan]\n" # 変数名変更
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
        results_list = [] # 結果を格納するリスト

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
                result_dict = process_row_data(row, index, total_rows) # 変数名変更
                results_list.append(result_dict) # 辞書をリストに追加
                progress.update(task, advance=1) # プログレスバーを進める

        # --- Excel関連処理を削除 ---
        # # 結果をDataFrameに変換
        # # new_columns = ['価格候補1', '価格候補2', '価格候補3', '出品者', '保証書日付', '付属品', '状態', '検索結果テキスト'] # 古い列名
        # new_columns = ['抽出結果JSON', '検索結果テキスト'] # 新しい列名
        # results_df = pd.DataFrame(results_list, columns=new_columns)
        #
        # # 元のDataFrameに結果を結合
        # df_result = pd.concat([df_process.reset_index(drop=True), results_df.reset_index(drop=True)], axis=1)
        #
        # # 結果を新しいExcelファイルに保存
        # console.print(f"\n書き込み中: [cyan]{output_excel_path}[/cyan]...")
        # df_result.to_excel(output_excel_path, index=False)

        # 結果をJSONファイルに保存
        console.print(f"\n書き込み中: [cyan]{output_json_path}[/cyan]...")
        try:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(results_list, f, ensure_ascii=False, indent=2)
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
