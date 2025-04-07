import openai
import os
import re
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
            "search_context_size": "medium",  # 検索深度
            "user_location": {
                "type": "approximate",
                "approximate": {
                    "country": "JP",  # 地域
                },
            },
        },
        messages=[{"role": "user", "content": query}],
    )
    return response.choices[0].message.content

def extract_prices(text):
    """テキストから価格情報を抽出し、リストで返す関数"""
    # 円マークまたは「円」を含む価格パターン、または「価格：」の後の数字を検索
    prices_with_symbol = re.findall(r'[¥￥]\d{1,3}(?:,\d{3})*', text) # ¥5,000,000 形式
    prices_with_unit = re.findall(r'\d{1,3}(?:,\d{3})*円', text) # 5,000,000円 形式
    prices_after_label = re.findall(r'価格：\s*(\d{1,3}(?:,\d{3})*)', text) # 価格： 5,000,000 形式

    prices = prices_with_symbol + prices_with_unit + prices_after_label

    # 重複を除き、数値に変換してソート
    numeric_prices = []
    seen_prices = set()
    for p_str in prices:
        # 数字とカンマ以外を除去
        cleaned_p = re.sub(r'[^\d,]', '', p_str)
        try:
            price_int = int(cleaned_p.replace(',', ''))
            if price_int not in seen_prices:
                 # 価格として妥当な範囲かチェック (例: 10万円以上、1億円未満)
                if 100000 <= price_int < 100000000:
                    numeric_prices.append(price_int)
                    seen_prices.add(price_int)
        except ValueError:
            continue # 数値変換できないものは無視

    # 昇順にソート
    numeric_prices.sort()

    # 表示用にフォーマット
    formatted_prices = [f"¥{p:,}" for p in numeric_prices]

    return formatted_prices

def extract_details(text):
    """テキストから詳細情報（出品者、保証書日付、付属品、状態）を抽出する関数"""
    details = {
        '出品者': None,
        '保証書日付': None,
        '付属品': None,
        '状態': None,
    }

    # 出品者 (例: "出品者：〇〇", "販売店：〇〇") - 精度は低い可能性あり
    seller_match = re.search(r'(?:出品者|販売店|ショップ)\s*[:：]\s*([^\n\s]+)', text)
    if seller_match:
        details['出品者'] = seller_match.group(1).strip()
    else:
         # リンク元などから推測 (例: GINZA RASIN 楽天市場店) - さらに精度低い
        seller_link_match = re.search(r'([^\s]+(?:店|楽天市場店|ショップ))\s*\(', text, re.IGNORECASE)
        if seller_link_match:
             details['出品者'] = seller_link_match.group(1).strip()


    # 保証書日付 (例: "保証書日付：YYYY年MM月", "ギャラ：YYYY/MM") - 形式多様
    date_match = re.search(r'(?:保証書日付|ギャラ(?:ンティ)?)\s*[:：]\s*(\d{4}年?\d{1,2}月?|\d{4}/\d{1,2})', text)
    if date_match:
        details['保証書日付'] = date_match.group(1).strip()

    # 付属品 (例: "付属品：箱、保証書", "付属品：あり")
    # "保証書"と"箱"（または"ボックス"）が含まれるかチェック
    accessories = []
    if re.search(r'保証書', text):
        accessories.append('保証書')
    if re.search(r'箱|ボックス', text):
        accessories.append('箱')
    if accessories:
        details['付属品'] = '、'.join(accessories)
    else:
        # "付属品：あり/なし"のような記述を探す
        付属品_match = re.search(r'付属品\s*[:：]\s*(あり|なし|[^\n]+)', text)
        if 付属品_match:
             details['付属品'] = 付属品_match.group(1).strip()


    # 状態 (例: "状態：中古A", "コンディション：良好") - 非常に多様
    condition_match = re.search(r'(?:状態|コンディション)\s*[:：]\s*([^\n]+)', text)
    if condition_match:
        details['状態'] = condition_match.group(1).strip().split(' ')[0] # 最初の単語だけ取るなど簡易的に
    else:
        # "中古"、"未使用"、"新品同様"などのキーワードを探す
        if re.search(r'新品同様|未使用|極美品', text):
             details['状態'] = '新品同様/未使用'
        elif re.search(r'中古[A-Z]?ランク|美品|良好', text):
             details['状態'] = '中古 (美品/良好)'
        elif re.search(r'中古', text):
             details['状態'] = '中古'

    return details
