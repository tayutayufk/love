import pandas as pd
import time
import argparse
import json
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

# 新しく追加されたクラスをインポート
from tavily_processor import tavily_processor
from watch_info_extractor import WatchInfoExtractor

# richコンソール初期化
console = Console()

# --- 設定 ---
DEFAULT_INPUT_EXCEL = '../data/target.xlsx'
DEFAULT_OUTPUT_JSON = '../data/result.json'
TEST_OUTPUT_JSON = '../data/result_test.json'
DEFAULT_LIMIT = None # Noneの場合は全件処理
TEST_LIMIT = 2       # テストモード時の処理行数
SLEEP_SECONDS = 1    # APIリクエスト間の待機時間（秒）
MAX_URLS_TO_FETCH = 5 # 検索結果の最大取得数

def process_row_data(row, row_index, total_rows, tavily_client, watch_extractor):
    """Excel行データから楽天の時計情報を検索し、詳細情報を抽出する"""
    initial_keywords = f"{row['ブランド']} {row['型番']} {row['文字盤色']} {row['ブレス形状']} 中古"
    console.print(f"[dim]({row_index+1}/{total_rows})[/dim] 処理開始: [cyan]{initial_keywords}[/cyan]")

    search_query = f"楽天市場 {initial_keywords}"
    extracted_watches_details = []  # 最終的な抽出結果リスト
    search_results = []  # 検索結果リスト

    try:
        # Tavilyを使用して楽天の商品を検索
        console.print(f"  -> 商品検索クエリ実行中: {search_query}")
        search_results = tavily_client.search_item(search_query, max_results=MAX_URLS_TO_FETCH)
        console.print(f"  -> 検索結果 ({len(search_results)}件):")
        
        for i, item in enumerate(search_results):
            console.print(f"    - URL: {item.get('url', 'N/A')}")

    except Exception as e:
        console.print(f"  -> 商品検索中にエラー発生: {repr(e)}")
        search_results = []

    # 個別商品情報の抽出ループ
    console.print(f"  -> 個別商品ページ情報取得中 ({len(search_results)}件)...")
    
    for i, item in enumerate(search_results):
        product_url = item.get("url")
        product_content = item.get("content")
        
        if not product_url or not product_content:
            console.print(f"    ({i+1}/{len(search_results)}) URL/コンテンツなしでスキップ")
            continue

        console.print(f"    ({i+1}/{len(search_results)}) URL: {product_url}")
        
        try:
            # WatchInfoExtractorを使って時計情報を抽出
            watch_detail = watch_extractor.extract_info(product_content)
            
            if watch_detail:
                # URLの追加
                watch_detail["url"] = product_url
                
                # 抽出結果をリストに追加
                extracted_watches_details.append(watch_detail)
                
                # コンソールに主要情報表示
                price_str = f"¥{watch_detail.get('price'):,}" if watch_detail.get('price') else "N/A"
                console.print(f"      -> 抽出成功: {watch_detail.get('name', 'N/A')} ({watch_detail.get('model_number', 'N/A')}) / {price_str}")
            else:
                console.print("      -> 詳細抽出失敗")
                # 詳細抽出失敗時も、URLは記録
                extracted_watches_details.append({
                    "name": None, "model_number": None, "dial_color": None, "bracelet_type": None,
                    "price": None, "url": product_url,
                    "seller": None, "warranty_date": None,
                    "accessories": {"has_warranty_card": None, "has_box": None, "other_description": "詳細抽出失敗"},
                    "condition": None
                })

            # APIのレート制限を避けるために待機
            time.sleep(SLEEP_SECONDS)

        except Exception as e:
            console.print(f"    -> URL {product_url} の処理中にエラー発生: {repr(e)}")
            # エラー時も基本情報は記録
            extracted_watches_details.append({
                "name": None, "model_number": None, "dial_color": None, "bracelet_type": None,
                "price": None, "url": product_url,
                "seller": None, "warranty_date": None,
                "accessories": {"has_warranty_card": None, "has_box": None, "other_description": f"処理中エラー: {repr(e)}"},
                "condition": None
            })

    # 結果を辞書で返す（search_resultsフィールドは除外）
    return {
        "input_keywords": initial_keywords,
        "extracted_results": extracted_watches_details
    }

def main():
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='Excelの時計情報からTavily APIとOpenAI APIを使って検索・抽出し、結果をJSONファイルに出力するスクリプト')
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
        # APIクライアントの初期化
        console.print("Tavily APIクライアントを初期化中...")
        tavily_client = tavily_processor()
        
        console.print("OpenAI APIクライアントを初期化中...")
        watch_extractor = WatchInfoExtractor()
        
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
        final_results_list = []  # 最終結果を格納するリスト

        # プログレスバーの設定
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=True  # 完了したら消す
        ) as progress:
            task = progress.add_task("[cyan]処理中...", total=total_rows)

            # 各行に関数を適用して結果を取得
            for index, row in df_process.iterrows():
                # 行ごとの処理を実行
                result_data_for_row = process_row_data(row, index, total_rows, tavily_client, watch_extractor)
                
                # 結果をリストに追加
                final_results_list.append(result_data_for_row)
                
                # 出力ディレクトリの確認と作成
                output_dir = Path(output_json_path).parent
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # 逐次保存（各行の処理後にJSONファイルを更新）
                with open(output_json_path, 'w', encoding='utf-8') as f:
                    json.dump(final_results_list, f, ensure_ascii=False, indent=2)
                
                # プログレスバーを進める
                progress.update(task, advance=1)

        # 最終結果の保存完了メッセージ
        console.print(Panel(f"[bold green]✓ 処理完了[/bold green]\n結果を '{output_json_path}' に保存しました。",
                            border_style="green"))

    except FileNotFoundError:
        console.print(f"[bold red]エラー:[/bold red] ファイル '{input_excel_path}' が見つかりません。")
    except Exception as e:
        console.print(f"[bold red]エラー:[/bold red] 処理中に問題が発生しました。")
        console.print_exception(show_locals=True)  # 詳細なエラー情報を表示

if __name__ == "__main__":
    main()