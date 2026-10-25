import json
import os
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from datetime import datetime, timedelta, timezone
from google import genai
from google.genai import errors


# ============================================================
# 1. 基本設定
# ============================================================

# GitHub ActionsのSecretsからAPIキーを取得
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY が設定されていません。"
        "GitHub Secretsの設定を確認してください。"
    )

# Gemini APIクライアント
client = genai.Client(api_key=api_key)

# 日本時間
JST = timezone(timedelta(hours=9))

# Geminiのモデル名
# GitHub Actionsの環境変数で変更することも可能
MODEL_NAME = os.environ.get(
    "GEMINI_MODEL",
    "gemini-3.1-flash-lite"
)


# ============================================================
# 2. GoogleニュースのRSSからニュースを取得
# ============================================================

def fetch_google_news(query, max_items=15):
    """
    GoogleニュースのRSSからニュースを取得する。

    Parameters
    ----------
    query : str
        検索キーワード
    max_items : int
        最大取得件数

    Returns
    -------
    list
        ニュース情報のリスト
    """

    encoded_query = urllib.parse.quote(query)

    url = (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=20
    ) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    news_items = []

    for item in root.findall(".//item")[:max_items]:

        title = item.findtext(
            "title",
            default=""
        )

        description = item.findtext(
            "description",
            default=""
        )

        link = item.findtext(
            "link",
            default=""
        )

        pub_date = item.findtext(
            "pubDate",
            default=""
        )

        news_items.append({
            "title": title,
            "description": description,
            "link": link,
            "published": pub_date
        })

    return news_items


# ============================================================
# 3. Gemini APIで市場変動の主要因を分析
# ============================================================

def analyze_market_news(news_items):
    """
    取得したニュースをGemini APIで分析する。

    一時的なサーバーエラーが発生した場合は、
    最大5回まで再試行する。
    """

    news_text = json.dumps(
        news_items,
        ensure_ascii=False,
        indent=2
    )

    today = datetime.now(JST).strftime("%Y-%m-%d")

    prompt = f"""
あなたは米国株市場を分析するアナリストです。

以下のニュース情報を分析し、前日の米国ハイテク株市場の
値動きに関連する主要な材料を最大3つ抽出してください。

【分析日】
{today}

【分析対象】
米国株市場、NASDAQ、半導体株、AI関連株、
大型ハイテク株など。

【重要なルール】

1. ニュースに書かれていない事実を作らない。
2. ニュースだけでは因果関係を確認できない場合は断定しない。
3. 市場全体の動きと個別企業のニュースを区別する。
4. 同じ内容のニュースを重複して数えない。
5. ニュースが十分でない場合、無理に3つの要因を作らない。
6. 確認できない内容は「可能性」「示唆」などの表現を使う。
7. ニュースの公開日時に注意する。
8. 分析対象の日付より後に公開されたニュースを、
   その日の株価変動の原因として扱わない。
9. 過去のニュースを、当日の新しい材料として扱わない。
10. 株価データが与えられていないため、実際の値動きや
    上昇・下落の方向をニュースだけで断定しない。
11. titleは日本語18～22文字を目安にする。
12. detailは日本語90～110文字を目安にする。
13. source_titleには根拠となるニュースの見出しを入れる。
14. source_urlには根拠となるニュースのURLを入れる。
15. 十分な根拠がない場合は、driversを空配列にしてもよい。

【出力形式】

有効なJSONだけを出力してください。

次の構造にしてください。

{{
  "report_date": "{today}",
  "drivers": [
    {{
      "title": "要因のタイトル",
      "detail": "要因の説明",
      "source_title": "根拠となるニュース見出し",
      "source_url": "根拠となるニュースURL"
    }}
  ]
}}

driversは最大3件です。

【分析対象のニュース】

{news_text}
"""

    # --------------------------------------------------------
    # Gemini APIを最大5回呼び出す
    # --------------------------------------------------------

    response = None
    max_attempts = 5

    for attempt in range(max_attempts):

        try:
            print(
                f"Gemini APIを呼び出します。"
                f"モデル: {MODEL_NAME} "
                f"（試行 {attempt + 1}/{max_attempts}）"
            )

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={
                    "response_mime_type": "application/json"
                }
            )

            # 成功したらループを終了
            break

        except errors.ServerError as e:

            # 最後の試行でも失敗した場合
            if attempt == max_attempts - 1:
                print(
                    "Gemini APIの再試行がすべて失敗しました。",
                    file=sys.stderr
                )
                raise

            # 待ち時間を10、20、40、80秒と延ばす
            wait_seconds = 10 * (2 ** attempt)

            print(
                f"Gemini APIでサーバーエラーが発生しました。"
                f"{wait_seconds}秒後に再試行します。"
                f"詳細: {e}",
                file=sys.stderr
            )

            time.sleep(wait_seconds)

    if response is None:
        raise RuntimeError(
            "Gemini APIから応答を取得できませんでした。"
        )

    # --------------------------------------------------------
    # JSONを解析
    # --------------------------------------------------------

    try:
        result = json.loads(response.text)

    except (json.JSONDecodeError, TypeError) as e:
        raise ValueError(
            "Gemini APIの応答をJSONとして解析できませんでした。"
        ) from e

    # --------------------------------------------------------
    # 出力データの形式を確認
    # --------------------------------------------------------

    if not isinstance(result, dict):
        raise ValueError(
            "Gemini APIの応答が想定したJSON形式ではありません。"
        )

    drivers = result.get("drivers")

    if not isinstance(drivers, list):
        raise ValueError(
            "分析結果にdrivers配列がありません。"
        )

    if len(drivers) > 3:
        result["drivers"] = drivers[:3]

    # 各要因の必須項目を確認
    for index, driver in enumerate(result["drivers"], start=1):

        if not isinstance(driver, dict):
            raise ValueError(
                f"{index}件目の要因がオブジェクト形式ではありません。"
            )

        for key in (
            "title",
            "detail",
            "source_title",
            "source_url"
        ):
            if not isinstance(driver.get(key), str):
                raise ValueError(
                    f"{index}件目の要因に"
                    f"{key}がないか、文字列ではありません。"
                )

    # レポート日を設定
    result["report_date"] = today

    return result


# ============================================================
# 4. メイン処理
# ============================================================

def main():

    print("=" * 60)
    print("米国株ニュース分析を開始します")
    print(
        f"分析日: "
        f"{datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # ニュース検索キーワード
    # --------------------------------------------------------

    queries = [
        "US stock market Nasdaq technology stocks",
        "US semiconductor stocks Nvidia AI",
        "US megacap technology earnings"
    ]

    all_news = []

    # --------------------------------------------------------
    # ニュース取得
    # --------------------------------------------------------

    for query in queries:

        try:
            items = fetch_google_news(
                query,
                max_items=15
            )

            all_news.extend(items)

            print(
                f"取得成功: {query} "
                f"({len(items)}件)"
            )

        except Exception as exc:

            print(
                f"ニュース取得失敗: {query}: {exc}",
                file=sys.stderr
            )

    # --------------------------------------------------------
    # URLでニュースの重複を排除
    # --------------------------------------------------------

    unique_news = {}

    for item in all_news:

        link = item.get("link", "")

        if link:
            unique_news[link] = item

    news_items = list(unique_news.values())

    print(
        f"ニュース取得合計: {len(news_items)}件"
    )

    # ニュースが取得できなければ処理を終了
    if not news_items:

        raise RuntimeError(
            "ニュースを取得できませんでした。"
            "分析結果は生成しません。"
        )

    # --------------------------------------------------------
    # ニュース取得結果をJSONに保存
    # --------------------------------------------------------

    news_output_file = "market_news.json"

    with open(
        news_output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "collected_at": datetime.now(JST).isoformat(),
                "count": len(news_items),
                "news": news_items
            },
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"ニュース取得結果を保存しました: {news_output_file}"
    )

    # --------------------------------------------------------
    # Geminiで分析
    # --------------------------------------------------------

    result = analyze_market_news(news_items)

    # --------------------------------------------------------
    # AI分析結果をJSONファイルに保存
    # --------------------------------------------------------

    output_file = "market_analysis.json"

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("=" * 60)
    print(f"分析結果を保存しました: {output_file}")
    print("=" * 60)

    # --------------------------------------------------------
    # 結果をログに表示
    # --------------------------------------------------------

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )

    print("=" * 60)
    print("米国株ニュース分析が完了しました")
    print("=" * 60)


# ============================================================
# 5. 実行
# ============================================================

if __name__ == "__main__":
    main()
