import json
from pathlib import Path
from src.watch_info_extractor import WatchInfoExtractor

def main():
    extractor = WatchInfoExtractor()

    # サンプルのテキスト（実際のテキストに合わせて適宜調整してください）
    sample_text = """
    【管理番号】659588  \n【ジャンル】腕時計 /メンズ  \n【ブランド】ロレックス / ROLEX  \n【モデル】コスモグラフ デイトナ  \n【型番（型式番号）】126500LN  \n【ムーブメント】自動巻き / Cal.4131  \n【文字盤】ブラック  \n【ケース】ステンレス  \n【風防】サファイアクリスタル風防  \n【ベゼル】ステンレス/セラミック / ブラック  \n【ブレスレット】オイスターブレス（ステンレス）\n【状態】\n中古 ランクA\n目立つダメージはございません\n【サイズ】\nケース\n縦/約40mm 横/約40mm\n厚み/約12mm\nラグ幅\n20mm\n腕周り\n約19.5cm\n【機能】\n防水(100ｍ) クロマライト夜光 スモールセコンド,クロノグラフ,タキメーター\n【付属品】\nメーカー保証書(2024年11月購入) メーカー箱 冊子\n【コメント】\n【当社保証】\n2年\nランク状態について\n商品の状態は、下記のランクで評価しています。\n弊社基準にて正確に評価しておりますが、主観的なものであるため、よくお考え頂いた上でご注文頂きますよう宜しくお願いいたします。 [...] 神経質な方・完璧を求められる方はご購入をご遠慮下さい。\n※店頭販売もしているため、写真や記載のない傷や汚れが生じる場合がございます。\n※掲載以外の詳細をご希望の方は在庫店舗をご案内致しますので一度お問い合わせ下さい。  \nＮ\n新品。\nＳ\n未使用品。未使用ですが展示品や保管などで僅かな色ヤケや傷が見られる品。一度も使用していない品。\nＳＡ\n新品同様。数回程度使用の中古品で、新品に近い綺麗な状態の中古品。\nＡ\n多少の使用感や傷はありますが状態の良い品\nＡＢ\n使用感や傷は見られますが、全体的に状態の良い品\nＢ\n日常的に使用していたような使用感や傷等が見られますが、充分に使用できる品\nＣ\n色濃く使用感があり、傷や汚れが多く目立つ品、リペアが必要な品\nＱ\nアンティーク品\nお支払方法\n・クレジットカード\n・ショッピングローン\n・振込銀行\n・代金引換（※代引き手数料を含め30万円以下のみご利用頂けます）\n詳しくはこちらをご覧ください。  \n商品仕様\nブランド名\nロレックス\nメーカー型番\n126500LN\n原産国／製造国\nスイス\nシリーズ名\nデイトナ（ロレックス）\nデュアルタイム\n無\n防滴・防水機能 [...] カテゴリトップ > 時計\nカテゴリトップ > 時計 > ロレックス\nカテゴリトップ > 時計 > ロレックス > デイトナ\n\n\n\n\n\n\n\n\n中古 ロレックス ROLEX コスモグラフ デイトナ 126500LN ブラック メンズ 腕時計 ロレックス 時計 高級腕時計 ブランド\n【～4/10 最大2万円クーポン】ロレックス ROLEX コスモグラフ デイトナ 126500LN ブラック メンズ 腕時計 ロレックス 時計 高級腕時計 ブランド 【ローン60回払い無金利】【中古】 \n商品番号： ik-00-0659588\n4,428,000\n円\n送料無料\n40,254ポイント\n\n1倍
    """

    # 抽出処理を実行
    result = extractor.extract_info(sample_text)

    # 出力先のディレクトリ（test/results）を pathlib で指定。なければ作成
    output_dir = Path(__file__).parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "watch_info.json"

    # 結果を JSON ファイルに保存
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"抽出結果は {output_file.resolve()} に保存されました。")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()