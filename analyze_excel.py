import pandas as pd

excel_file_path = 'result_test.xlsx' # 読み込むファイルを変更

try:
    # Excelファイルを読み込む
    df = pd.read_excel(excel_file_path)

    print(f"--- '{excel_file_path}' の内容 ---")
    # データフレームの内容を表示 (最初の5行)
    print("最初の5行:")
    print(df.head())

    # データフレームの基本情報を表示
    print("\n基本情報:")
    df.info()

    # 要約統計量を表示 (全列)
    print("\n要約統計量 (全列):")
    print(df.describe(include='all')) # 全ての列

except FileNotFoundError:
    print(f"エラー: ファイル '{excel_file_path}' が見つかりません。")
except Exception as e:
    print(f"エラー: Excelファイルの読み込み中に問題が発生しました。")
    print(e)
