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

    def search_item(self, query: str, max_results: int = 20, advance_search: bool = True):
        """
        Tavily Search API を使って楽天内の商品を検索する処理
        パラメータ:
        query (str): 検索クエリ
        max_results (int): 返却する検索結果の最大件数
        advance_search (bool): Trueの場合は高度な検索深度を使用、Falseの場合は標準検索
        戻り値:
        List[dict]: 各辞書が {"url": <URL>, "content": <raw_content>} となるリスト（重複なし）
        """
        # 検索パラメータを辞書として準備
        search_params = {
            "query": query,
            "max_results": max_results,
            "include_raw_content": True,
            "include_domains": ["https://item.rakuten.co.jp/"],
            "exclude_domains": [""],
        }

        # advance_searchがTrueの場合のみ、search_depthパラメータを追加
        if advance_search:
            search_params["search_depth"] = "advanced"

        # 準備したパラメータでAPIを呼び出し
        response = self.client.search(**search_params)

        results = response.get("results", [])
        filtered_results = []
        processed_urls = set()  # URLの重複チェック用セット

        for item in results:
            url = item.get("url")
            content = item.get("raw_content")

            # URLが有効で、コンテンツがあり、まだ処理していないURLのみを追加
            if url and content and url not in processed_urls:
                processed_urls.add(url)  # 処理済みとしてマーク
                filtered_results.append({"url": url, "content": content})

        return filtered_results

    def extract_content(self, url: str, extract_depth: str = "advanced", include_images: bool = False):
        """
        Tavily Extract API を使って、指定されたURLから content と画像URLを抽出する処理
        パラメータ:
        url (str): 抽出対象のURL（リストに変換して渡す）
        extract_depth (str): "advanced" または "basic"
        include_images (bool): 画像URLを含めるかどうか。デフォルトはFalse
        戻り値:
        dict または str または None:
            include_images=True の場合: {"raw_content": 抽出されたコンテンツ, "images": 画像URLのリスト}
            include_images=False の場合: 抽出された raw_content のみ
            結果がなければ None を返す。
        """
        response = self.client.extract(urls=[url], extract_depth=extract_depth, include_images=include_images)
        results = response.get("results", [])
        if not results:
            return None

        result = results[0]
        raw_content = result.get("raw_content")

        if include_images:
            images = result.get("images", [])
            return {"raw_content": raw_content, "images": images}
        else:
            return raw_content
