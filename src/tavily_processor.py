import os
from tavily import TavilyClient
from dotenv import load_dotenv

# .envファイルから環境変数を読み込み
load_dotenv()

class tavily_processor:
    """
    Tavily の Search と Extract の処理をラップするクラス
    """
    def __init__(self):
        # 環境変数から Tavily API キーを取得
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("Tavily APIキーが設定されていません。.envファイルを確認してください。")
        # TavilyClient を初期化（同期版）
        self.client = TavilyClient(self.api_key)
    
    def search_item(self, query: str, max_results: int = 20):
        """
        Tavily Search API を使って楽天内の商品を検索する処理
        パラメータ:
          query (str): 検索クエリ
          max_results (int): 返却する検索結果の最大件数
        戻り値:
          List[dict]: 各辞書が {"url": <URL>, "content": <raw_content>} となるリスト
        """
        response = self.client.search(
            query=query,
            max_results=max_results,
            include_raw_content=True,
            include_domains=["https://item.rakuten.co.jp/"],
            exclude_domains=[""]
        )
        results = response.get("results", [])
        filtered_results = []
        for item in results:
            url = item.get("url")
            # raw_content が存在する場合、それを content として返す
            content = item.get("raw_content")
            if url and content:
                filtered_results.append({"url": url, "content": content})
        return filtered_results

    def extract_content(self, url: str, extract_depth: str = "advanced"):
        """
        Tavily Extract API を使って、指定されたURLから raw_content を抽出する処理
        パラメータ:
          url (str): 抽出対象のURL（リストに変換して渡す）
          extract_depth (str): "advanced" または "basic"
        戻り値:
          str または None: 抽出された raw_content。結果がなければ None を返す。
        """
        response = self.client.extract(
            urls=[url],
            extract_depth=extract_depth
        )
        results = response.get("results", [])
        if results:
            return results[0].get("raw_content")
        return None