# test/test_tavily.py
import json
from pathlib import Path
from rich.progress import Progress
from src.tavily_processor import tavily_processor

def main():
    processor = tavily_processor()
    query = "ROLEX 126500LN ブラック オイスター 中古"

    # 出力先のディレクトリ（test/results）を pathlib で指定。なければ作成
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "tavily_search_results.json"

    results_with_content = []
    with Progress() as progress:
        # 検索処理の進捗表示
        task_search = progress.add_task("[cyan]Searching items...", total=1)
        search_results = processor.search_item(query, max_results=20)
        progress.update(task_search, advance=1)

        # 全URLに対する抽出処理の進捗バーを 1 つ用意（合計ステップ数 = 検索結果の件数）
        task_extract = progress.add_task("[green]Extracting content...", total=len(search_results))
        for item in search_results:
            url = item.get("url")
            extraction_result = processor.extract_content(url, extract_depth="advanced", include_images=True)
            
            if extraction_result is None:
                # 抽出結果がない場合
                results_with_content.append({"url": url, "raw_content": None, "images": []})
            elif isinstance(extraction_result, dict):
                # 画像URLを含む抽出結果の場合
                results_with_content.append({
                    "url": url, 
                    "raw_content": extraction_result["raw_content"],
                    "images": extraction_result["images"]
                })
            else:
                # 画像URLを含まない抽出結果の場合（バックワードコンパティビリティ）
                results_with_content.append({"url": url, "raw_content": extraction_result, "images": []})
                
            progress.update(task_extract, advance=1)

    # 保存する内容の構造例: クエリと各URL毎の raw_content と画像URL
    output_data = {
        "query": query,
        "results": results_with_content
    }

    # JSON ファイルとして保存
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"結果は {output_file.resolve()} に保存されました。")

if __name__ == "__main__":
    main()