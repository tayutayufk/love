import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# .envから環境変数を読み込み
load_dotenv()

class WatchInfoExtractor:
    """
    入力されたテキストから、時計の情報を抽出するクラス
    OpenAI API の json_object モードを利用して、以下のスキーマに従った情報を抽出する
    """
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI APIキーが設定されていません。.envファイルを確認してください。")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o-mini"  # json_object 出力に対応したモデルを指定

    def extract_info(self, text: str):
        # JSONスキーマの定義（各項目の型や説明を含む）
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"], "description": "時計の名前"},
                "model_number": {"type": ["string", "null"], "description": "型番"},
                "dial_color": {"type": ["string", "null"], "description": "文字盤の色"},
                "bracelet_type": {
                    "type": ["string", "null"],
                    "description": "ブレス形状",
                    "enum": [
                        "オイスターブレスレット", "ジュビリーブレスレット", "プレジデントブレスレット",
                        "オイスターフレックスブレスレット", "パールマスターブレスレット",
                        "レザーブレスレット", "そのほか", "不明"
                    ]
                },
                "price": {"type": ["integer", "null"], "description": "価格"},
                "seller": {"type": ["string", "null"], "description": "出品者名"},
                "warranty_date": {"type": ["string", "null"], "description": "保証書の日付"},
                "accessories": {
                    "type": "object",
                    "properties": {
                        "has_warranty_card": {"type": ["boolean", "null"], "description": "保証書の有無"},
                        "has_box": {"type": ["boolean", "null"], "description": "箱の有無"},
                        "other_description": {"type": ["string", "null"], "description": "他の付属品の名前"}
                    },
                    "required": ["has_warranty_card", "has_box", "other_description"]
                },
                "condition": {"type": ["string", "null"], "description": "状態"}
            },
            "required": [
                "name", "model_number", "dial_color", "bracelet_type", "price",
                "seller", "warranty_date", "accessories", "condition"
            ]
        }

        prompt = f"""
以下のテキストから、時計の情報を抽出してください。抽出する情報は以下の JSON スキーマに従って出力してください。

スキーマ:
{json.dumps(schema, indent=2, ensure_ascii=False)}

テキスト:
\"\"\"
{text}
\"\"\"
"""
        response = self.client.chat.completions.create(
            model=self.model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": f"あなたは時計情報抽出のアシスタントです。以下のスキーマに従って、情報を抽出してください。\n{json.dumps(schema, indent=2, ensure_ascii=False)}"
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        result_json_str = response.choices[0].message.content
        result = json.loads(result_json_str)
        return result