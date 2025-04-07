import openai
import os
import re
import json # JSONを扱うためにインポート
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
            "search_context_size": "high",  # 検索深度
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

def extract_multiple_watch_info_json(text):
    """LLM(gpt-4o-mini)を使用してテキストから複数の時計情報を抽出し、JSONオブジェクトのリスト(List[Dict])で返す関数"""
    # 個々の時計情報のスキーマ
    single_watch_info_schema = {
        "type": "object",
        "properties": {
            "name": {"type": ["string", "null"], "description": "時計の名称やタイトル"},
            "price": {"type": ["integer", "null"], "description": "価格（日本円、整数）。見つからない場合はnull。10万円以上1億円未満。"},
            "url": {"type": ["string", "null"], "description": "商品ページのURL。見つからない場合はnull。末尾の'?utm_source=openai'は削除する。"},
            "seller": {"type": ["string", "null"], "description": "出品者名。見つからない場合はnull。"},
            "warranty_date": {"type": ["string", "null"], "description": "保証書日付。見つからない場合はnull。"},
            "accessories": {"type": ["string", "null"], "description": "付属品の情報。見つからない場合はnull。"},
            "condition": {"type": ["string", "null"], "description": "時計の状態。見つからない場合はnull。"}
        },
        "required": ["name", "price", "url", "seller", "warranty_date", "accessories", "condition"]
    }

    # 複数の時計情報をリストで返すためのスキーマ
    multiple_watch_info_schema = {
        "type": "object",
        "properties": {
            "watches": {
                "type": "array",
                "description": "抽出された時計情報のリスト。見つからない場合は空のリスト。",
                "items": single_watch_info_schema
            }
        },
        "required": ["watches"]
    }

    prompt = f"""以下のWeb検索結果のテキストから、比較可能な中古時計の情報を複数抽出し、指定されたJSONスキーマに従ってJSONオブジェクトのリストで返してください。
各時計について、以下の情報を抽出してください： name, price (10万円以上1億円未満、整数、なければnull), url ('?utm_source=openai'削除), seller, warranty_date, accessories, condition。
該当情報がない場合は null としてください。抽出できる時計がなければ空のリスト `[]` を含むJSONを返してください。

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
                {"role": "system", "content": f"あなたはテキストから複数の時計情報を抽出し、以下のJSONスキーマに従ってJSONオブジェクトで出力するアシスタントです。\nスキーマ:\n{json.dumps(multiple_watch_info_schema, indent=2, ensure_ascii=False)}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        result_json_str = response.choices[0].message.content
        result_data = json.loads(result_json_str)
        watches_list = result_data.get("watches", [])

        # 各時計情報のバリデーションと整形
        validated_watches = []
        for watch_info in watches_list:
            # URLから ?utm_source=openai を削除
            if watch_info.get("url") and isinstance(watch_info["url"], str):
                watch_info["url"] = watch_info["url"].split('?utm_source=openai')[0]

            # 価格のバリデーション
            if watch_info.get("price") is not None:
                if not (isinstance(watch_info["price"], int) and 100000 <= watch_info["price"] < 100000000):
                    watch_info["price"] = None

            # スキーマに定義されたキーが存在するか確認し、なければnullで補完
            for key in single_watch_info_schema["properties"].keys():
                if key not in watch_info:
                    watch_info[key] = None
            validated_watches.append(watch_info)

        return validated_watches # 辞書のリストを返す

    except json.JSONDecodeError as e:
        print(f"  -> 情報抽出エラー (JSONデコード失敗): {repr(e)}")
        print(f"  -> 不正なJSON文字列: {result_json_str}")
        return [] # エラー時は空リスト
    except Exception as e:
        print(f"  -> 情報抽出エラー (API呼び出し等): {repr(e)}")
        return [] # エラー時は空リスト
