# このファイルは、utils.py の関数をテストするためのサンプルコードです。
# process_excel.py を実行する際には、このファイルは直接使用されません。

from utils import search_web, extract_prices, extract_details

# ===== 実際に動かしてみる (テスト用) =====
if __name__ == "__main__":
    # テスト用のクエリ
    test_query = "ROLEX デイトナ 116500LN ブラック 中古 価格"
    print(f"--- テスト検索実行 ---")
    print(f"クエリ: {test_query}")

    try:
        search_result = search_web(test_query)
        print("\n--- 検索結果 (テスト) ---")
        print(search_result)

        print("\n--- 抽出された価格リスト (テスト) ---")
        extracted_prices = extract_prices(search_result)
        if extracted_prices:
            for price in extracted_prices:
                print(f"- {price}")
        else:
            print("価格情報が見つかりませんでした。")

        print("\n--- 抽出された詳細情報 (テスト) ---")
        extracted_details_result = extract_details(search_result)
        print(extracted_details_result)

    except Exception as e:
        print(f"\n--- テスト中にエラーが発生しました ---")
        print(e)
