import pandas as pd
import time
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

# utils.py から関数をインポート
from utils import search_web, extract_prices, extract_details

# richコンソール初期化
console = Console()

# --- 設定 ---
DEFAULT_INPUT_EXCEL = 'target.xlsx'
DEFAULT_OUTPUT_EXCEL = 'result.xlsx'
TEST_OUTPUT_EXCEL = 'result_test.xlsx'
DEFAULT_LIMIT = None # Noneの場合は全件処理
TEST_LIMIT = 5       # テストモード時の処理行数
SLEEP_SECONDS = 1    # APIリクエスト間の待機時間（秒）

def process_row_data(row, row_index, total_rows):
    """Excelの行データからクエリを作成し、価格候補、詳細情報、検索結果テキストを取得する"""
    # クエリを作成
    query = f"{row['ブランド']} {row['型番']} {row['文字盤色']} {row['ブレス形状']} 中古 価格 詳細"
    console.print(f"[dim]({row_index+1}/{total_rows})[/dim] 検索中: [cyan]{query}[/cyan]")

    price1, price2, price3 = None, None, None
    details = {'出品者': None, '保証書日付': None, '付属品': None, '状態': None}
    search_result_text = None # 検索結果テキストを初期化

    try:
        search_result = search_web(query)
        search_result_text = search_result # 生テキストを保存

        # 価格抽出
        extracted_prices = extract_prices(search_result)
        price1 = extracted_prices[0] if len(extracted_prices) > 0 else None
        price2 = extracted_prices[1] if len(extracted_prices) > 1 else None
        price3 = extracted_prices[2] if len(extracted_prices) > 2 else None

        # 詳細情報抽出
        details = extract_details(search_result)

        # 結果表示用のテーブルを作成
        result_table = Table(show_header=False, box=None, padding=(0, 1))
        result_table.add_column()
        result_table.add_column()

        price_str = ', '.join(filter(None, [price1, price2, price3])) or "[dim]N/A[/dim]"
        result_table.add_row("[bold green]価格候補[/bold green]:", price_str)
        result_table.add_row("[bold blue]出品者[/bold blue]:", Text(details['出品者'] or "[dim]N/A[/dim]"))
        result_table.add_row("[bold blue]保証書日付[/bold blue]:", Text(details['保証書日付'] or "[dim]N/A[/dim]"))
        result_table.add_row("[bold blue]付属品[/bold blue]:", Text(details['付属品'] or "[dim]N/A[/dim]"))
        result_table.add_row("[bold blue]状態[/bold blue]:", Text(details['状態'] or "[dim]N/A[/dim]"))

        console.print(result_table)

        # APIのレート制限を避けるために少し待機
        time.sleep(SLEEP_SECONDS)

    except Exception as e:
        console.print(f"  -> [bold red]エラー発生[/bold red]: {e}")
        # エラーが発生した場合もNoneを返す
        time.sleep(SLEEP_SECONDS) # エラー時も待機

    # 結果をSeriesで返す (列名に合わせて)
    return pd.Series([
        price1, price2, price3,
        details['出品者'], details['保証書日付'], details['付属品'], details['状態'],
        search_result_text # 検索結果テキストも返す
    ])

def main():
    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description='Excelの時計情報からWeb検索し、価格と詳細情報を追記するスクリプト')
    parser.add_argument('--test', action='store_true', help='最初の5件のみ処理するテストモード')
    parser.add_argument('--input', default=DEFAULT_INPUT_EXCEL, help=f'入力Excelファイル名 (デフォルト: {DEFAULT_INPUT_EXCEL})')
    parser.add_argument('--output', default=None, help='出力Excelファイル名 (デフォルト: testモード時はresult_test.xlsx, 通常時はresult.xlsx)')
    args = parser.parse_args()

    # 入力/出力ファイルパスと処理行数制限の設定
    input_excel_path = args.input
    limit = TEST_LIMIT if args.test else DEFAULT_LIMIT
    if args.output:
        output_excel_path = args.output
    else:
        output_excel_path = TEST_OUTPUT_EXCEL if args.test else DEFAULT_OUTPUT_EXCEL

    console.print(Panel(f"[bold green]Rolex Search Tool 開始[/bold green]\n"
                        f"入力ファイル: [cyan]{input_excel_path}[/cyan]\n"
                        f"出力ファイル: [cyan]{output_excel_path}[/cyan]\n"
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

            # 各行に関数を適用して価格候補と詳細情報を取得
            for index, row in df_process.iterrows():
                result_series = process_row_data(row, index, total_rows)
                results_list.append(result_series)
                progress.update(task, advance=1) # プログレスバーを進める

        # 結果をDataFrameに変換
        new_columns = ['価格候補1', '価格候補2', '価格候補3', '出品者', '保証書日付', '付属品', '状態', '検索結果テキスト'] # 新しい列名
        results_df = pd.DataFrame(results_list, columns=new_columns)

        # 元のDataFrameに結果を結合
        df_result = pd.concat([df_process.reset_index(drop=True), results_df.reset_index(drop=True)], axis=1)

        # 結果を新しいExcelファイルに保存
        console.print(f"\n書き込み中: [cyan]{output_excel_path}[/cyan]...")
        df_result.to_excel(output_excel_path, index=False)
        console.print(Panel(f"[bold green]✓ 処理完了[/bold green]\n結果を '{output_excel_path}' に保存しました。",
                            border_style="green"))

    except FileNotFoundError:
        console.print(f"[bold red]エラー:[/bold red] ファイル '{input_excel_path}' が見つかりません。")
    except Exception as e:
        console.print(f"[bold red]エラー:[/bold red] 処理中に問題が発生しました。")
        console.print_exception(show_locals=True) # 詳細なエラー情報を表示

if __name__ == "__main__":
    main()
