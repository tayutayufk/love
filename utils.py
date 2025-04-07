import openai
import os
import re
import json # JSONを扱うためにインポート
import urllib.parse # URLエンコードのためにインポート
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からAPIキーを取得
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OpenAI APIキーが設定されていません。.envファイルを確認してください。")

# OpenAIのクライアント設定（APIキーをセット）
client = openai.OpenAI(api_key=api_key)

def search_web(query):
    """Web検索を使って最新情報を取得する関数"""
    response = client.chat.completions.create(
        model="gpt-4o-search-preview",
        web_search_options={
            "search_context_size": "low",  # 検索深度
            "user_location": {
                "type": "approximate",
                "approximate": {
                    "country": "JP",  # 地域
                },
            },
        },
        messages=[{"role": "user", "content": query}],
        # temperature=0.0 # gpt-4o-search-previewはこのパラメータをサポートしていないため削除
    ) # ★閉じ括弧を追加
    return response.choices[0].message.content

def extract_url_price_pairs(text, max_results=5):
    """LLM(gpt-4o-mini)を使用して検索結果テキストから商品URLと価格のペアリストを抽出する関数"""
    url_price_pair_schema = {
        "type": "object",
        "properties": {
            "url": {"type": ["string", "null"], "description": "`https://item.rakuten.co.jp/` から始まる商品ページのURL"},
            "price": {"type": ["integer", "null"], "description": "価格（日本円、整数）。見つからない場合はnull。"}
        },
        "required": ["url", "price"]
    }
    url_price_list_schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": f"抽出された商品URLと価格のペアリスト。最大{max_results}件。",
                "items": url_price_pair_schema
            }
        },
        "required": ["items"]
    }
    prompt = f"""以下の**検索結果ページ**のテキストから、個々の商品情報（URLと価格）を抽出し、指定されたJSONスキーマに従ってリストで返してください。
URLは `https://item.rakuten.co.jp/` で始まるもののみを対象とし、価格は日本円の整数値、見つからなければ `null` としてください。最大{max_results}件まで抽出してください。

テキスト：
\"\"\"
{text}
\"\"\"
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": f"あなたはテキストから商品URLと価格のペアリストを抽出し、以下のJSONスキーマに従ってJSONオブジェクトで出力するアシスタントです。\nスキーマ:\n{json.dumps(url_price_list_schema, indent=2)}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        result_json_str = response.choices[0].message.content
        result_data = json.loads(result_json_str)
        items = result_data.get("items", [])

        # バリデーションと整形
        valid_items = []
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("url"), str) and item["url"].startswith("https://item.rakuten.co.jp/"):
                # 価格が数値でなければnullにする
                if not isinstance(item.get("price"), int):
                    item["price"] = None
                # URLからutmパラメータ削除
                item["url"] = item["url"].split('?utm_source=openai')[0]
                valid_items.append({"url": item["url"], "price": item["price"]}) # 必要なキーだけ保持

        return valid_items[:max_results] # 最大数に制限して返す

    except json.JSONDecodeError as e:
        print(f"  -> URL/価格ペア抽出エラー (JSONデコード失敗): {repr(e)}")
        print(f"  -> 不正なJSON文字列: {result_json_str}")
        return []
    except Exception as e:
        print(f"  -> URL/価格ペア抽出エラー (API呼び出し等): {repr(e)}")
        return []

def extract_single_watch_info_json(text): # 関数名を変更し、単一情報抽出に特化
    """LLM(gpt-4o-mini)を使用してテキストから単一の時計情報を抽出し、JSONオブジェクト(辞書)で返す関数"""
    # 個々の時計情報のスキーマ (修正)
    single_watch_info_schema = {
        "type": "object", # トップレベルをオブジェクトに変更
        "properties": {
            "name": {"type": ["string", "null"], "description": "時計の名称やタイトル"},
            "model_number": {"type": ["string", "null"], "description": "型番 (例: 126500LN)"}, # 追加
            "dial_color": {"type": ["string", "null"], "description": "文字盤の色"}, # 追加
            "bracelet_type": {"type": ["string", "null"], "description": "ブレスの形状 (例: オイスター, ジュビリー)"}, # 追加
            "price": {"type": ["integer", "null"], "description": "価格（日本円、整数）。見つからない場合はnull。10万円以上1億円未満。"},
            "url": {"type": ["string", "null"], "description": "商品ページのURL。見つからない場合はnull。末尾の'?utm_source=openai'は削除する。"},
            "seller": {"type": ["string", "null"], "description": "出品者名。見つからない場合はnull。"},
            "warranty_date": {"type": ["string", "null"], "description": "保証書日付。見つからない場合はnull。"},
            "accessories": { # オブジェクトに変更
                "type": "object",
                "properties": {
                    "has_warranty_card": {"type": ["boolean", "null"], "description": "保証書(ギャランティカード)の有無"},
                    "has_box": {"type": ["boolean", "null"], "description": "箱(BOX)の有無"},
                    "other_description": {"type": ["string", "null"], "description": "その他の付属品に関する記述"}
                },
                "required": ["has_warranty_card", "has_box", "other_description"]
            },
            "condition": {"type": ["string", "null"], "description": "時計の状態。"}
        },
        # 必須項目を更新
        "required": ["name", "model_number", "dial_color", "bracelet_type", "price", "url", "seller", "warranty_date", "accessories", "condition"]
    }

    # --- 複数リスト用のスキーマは削除 ---

    prompt = f"""以下の**単一の商品ページ**に関するテキストから、時計の情報を抽出し、指定されたJSONスキーマに従ってJSONオブジェクトで返してください。
抽出する情報は以下の通りです：
- name: 時計の名称やタイトル
- model_number: 型番 (例: 126500LN)
- dial_color: 文字盤の色
- bracelet_type: ブレスの形状 (例: オイスター, ジュビリー)
- price: 価格（日本円、整数、10万円以上1億円未満、なければnull）
- url: 商品ページURL ('?utm_source=openai'削除、なければnull)。**注意: `https://item.rakuten.co.jp/` から始まるURLのみを対象とします。**
- seller: 出品者名 (なければnull)
- warranty_date: 保証書日付 (なければnull)
- accessories: 付属品情報 (保証書の有無: has_warranty_card (boolean), 箱の有無: has_box (boolean), その他記述: other_description (string))
- condition: 時計の状態 (なければnull)
該当情報がない場合は null としてください。

テキスト：
\"\"\"
{text}
\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"}, # スキーマはプロンプトで指示
            messages=[
                # システムプロンプトを単一情報抽出用に変更
                {"role": "system", "content": f"あなたはテキストから単一の時計情報を抽出し、以下のJSONスキーマに従ってJSONオブジェクトで出力するアシスタントです。\nスキーマ:\n{json.dumps(single_watch_info_schema, indent=2, ensure_ascii=False)}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        result_json_str = response.choices[0].message.content
        result_dict = json.loads(result_json_str) # 単一の辞書として受け取る

        # --- バリデーションと整形 (単一の辞書に対して行う) ---
        # URLから ?utm_source=openai を削除
        if result_dict.get("url") and isinstance(result_dict["url"], str):
            result_dict["url"] = result_dict["url"].split('?utm_source=openai')[0]
            # URLがitem.rakuten.co.jpで始まらない場合はnullにする
            if not result_dict["url"].startswith("https://item.rakuten.co.jp/"):
                 result_dict["url"] = None

        # 価格のバリデーション
        if result_dict.get("price") is not None:
            if not (isinstance(result_dict["price"], int) and 100000 <= result_dict["price"] < 100000000):
                result_dict["price"] = None

        # 付属品オブジェクトのバリデーションと補完
        accessories_info = result_dict.get("accessories", {})
        if not isinstance(accessories_info, dict):
            accessories_info = {}
        accessories_info.setdefault("has_warranty_card", None)
        accessories_info.setdefault("has_box", None)
        accessories_info.setdefault("other_description", None)
        result_dict["accessories"] = accessories_info

        # スキーマに定義されたトップレベルのキーが存在するか確認し、なければnullで補完
        for key in single_watch_info_schema["properties"].keys():
            if key != "accessories" and key not in result_dict:
                result_dict[key] = None

        return result_dict # 単一の辞書を返す

    except json.JSONDecodeError as e:
        print(f"  -> 情報抽出エラー (JSONデコード失敗): {repr(e)}")
        print(f"  -> 不正なJSON文字列: {result_json_str}")
        return None # エラー時はNone
    except Exception as e:
        print(f"  -> 情報抽出エラー (API呼び出し等): {repr(e)}")
        return [] # エラー時は空リスト

def generate_rakuten_search_url(keywords):
    """検索キーワード文字列を受け取り、楽天市場の検索結果URLを生成する関数"""
    base_url = "https://search.rakuten.co.jp/search/mall/"
    # キーワードをUTF-8でURLエンコード
    encoded_keywords = urllib.parse.quote(keywords.encode('utf-8'))
    # URLを結合して返す
    return f"{base_url}{encoded_keywords}/"
