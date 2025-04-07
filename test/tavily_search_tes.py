# To install: pip install tavily-python
from tavily import TavilyClient
client = TavilyClient("tvly-dev-********************************")
response = client.search(
    query="ROLEX 126500LN ブラック オイスター 中古 ",
    max_results=20,
    include_raw_content=True,
    include_domains=["https://item.rakuten.co.jp/"],
    exclude_domains=[""]
)
print(response)