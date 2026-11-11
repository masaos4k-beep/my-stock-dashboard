#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3指数と market_analysis.json からX投稿案を生成する（投稿はしません）。

v4: ニュース文を文の途中で切らず、完結した文だけを採用します。
文字数に収まらない場合は材料を減らし、指数・市場総括・リンクを優先します。
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_FILE = ROOT / "market_analysis.json"
OUTPUT_FILE = ROOT / "market_post.txt"
MARKET_REPORT_URL = "https://www.beyondworklife.com/market_report.html"
POST_LIMIT = 270

INDICES = [
    {"name": "S&P500", "ticker": "^GSPC"},
    {"name": "NASDAQ100", "ticker": "^NDX"},
    {"name": "SOX", "ticker": "^SOX"},
]

REVIEW_TERMS = (
    "疑惑", "不倫", "スパイ", "捜査", "調査", "逮捕", "不祥事",
    "fraud", "investigation", "investigated", "spy", "affair",
    "scandal", "arrest", "accusation", "allegation",
)


def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def load_analysis() -> dict[str, Any]:
    if not ANALYSIS_FILE.exists():
        raise FileNotFoundError(f"市場分析ファイルがありません: {ANALYSIS_FILE}")
    with ANALYSIS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("drivers"), list):
        raise ValueError("market_analysis.json の形式が正しくありません。")
    return data


def fetch_index(name: str, ticker: str) -> dict[str, Any]:
    history = yf.Ticker(ticker).history(
        period="10d", interval="1d", auto_adjust=False, actions=False
    )
    if history.empty or "Close" not in history.columns:
        raise RuntimeError(f"{name} ({ticker}) の株価データを取得できません。")
    closes = history["Close"].dropna()
    if len(closes) < 2:
        raise RuntimeError(f"{name} ({ticker}) の終値データが2日分ありません。")

    previous_close = float(closes.iloc[-2])
    latest_close = float(closes.iloc[-1])
    if previous_close == 0:
        raise RuntimeError(f"{name} の前日終値が0のため計算できません。")

    return {
        "name": name,
        "date": closes.index[-1].date().isoformat(),
        "close": latest_close,
        "change_pct": (latest_close / previous_close - 1) * 100,
    }


def has_review_term(text: str) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in REVIEW_TERMS)


def select_drivers(analysis: dict[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    selected = []
    excluded = []

    for driver in analysis.get("drivers", []):
        if not isinstance(driver, dict):
            continue
        title = clean_text(driver.get("title"))
        detail = clean_text(driver.get("detail"))
        source_title = clean_text(driver.get("source_title"))
        source_url = clean_text(driver.get("source_url"))

        if not title or not detail:
            excluded.append(title or "(タイトルまたは詳細が空欄)")
            continue
        if has_review_term(" ".join([title, detail, source_title])):
            excluded.append(title + "（要確認語句を検出）")
            continue
        if not source_title or not source_url.startswith("https://"):
            excluded.append(title + "（出典情報不足）")
            continue

        selected.append({
            "title": title,
            "detail": detail,
            "source_title": source_title,
            "source_url": source_url,
        })
        if len(selected) >= 3:
            break

    return selected, excluded


def format_index(item: dict[str, Any]) -> str:
    pct = item["change_pct"]
    sign = "+" if pct >= 0 else ""
    return f'{item["name"]} {item["close"]:,.2f}（{sign}{pct:.2f}%）'


def make_market_summary(indices: list[dict[str, Any]]) -> str:
    by_name = {item["name"]: item["change_pct"] for item in indices}
    sp = by_name["S&P500"]
    ndx = by_name["NASDAQ100"]
    sox = by_name["SOX"]

    if sp > 0 and ndx > 0 and sox > 0:
        if sox - sp >= 2.0:
            return "半導体株が相対的に強く、上昇相場をけん引しました。"
        if ndx - sp >= 1.0:
            return "大型ハイテク株が市場全体を上回る展開でした。"
        return "主要3指数がそろって上昇し、堅調な地合いでした。"
    if sp < 0 and ndx < 0 and sox < 0:
        if sox < sp - 2.0:
            return "半導体株の下げが大きく、ハイテク株に売りが目立ちました。"
        return "主要3指数がそろって下落し、軟調な地合いでした。"
    if sp > 0 and ndx < 0:
        return "ハイテク株が弱含む一方、S&P500は上昇しました。"
    if sp < 0 and ndx > 0:
        return "S&P500が下落する一方、NASDAQ100は底堅さを見せました。"
    if sox > ndx and sox > sp:
        return "半導体株が相対的に底堅い動きとなりました。"
    if sox < ndx and sox < sp:
        return "半導体株が相対的に弱い動きとなりました。"
    return "主要指数で方向感が分かれる展開となりました。"


def first_complete_sentence(text: str) -> str:
    """最初の完結した文を返す。文末がない文章は採用しない。"""
    text = clean_text(text)
    match = re.search(r"^(.+?[。.!?])(?:\s|$|[「『])", text)
    if match:
        return match.group(1).strip()
    # 文字列全体が文末記号で終わる場合も採用
    if text.endswith(("。", "!", "?")):
        return text
    return ""


def build_post(
    indices: list[dict[str, Any]],
    drivers: list[dict[str, str]],
) -> tuple[str, list[str]]:
    date_label = indices[0]["date"].replace("-", "/")
    summary = make_market_summary(indices)

    # 完結した最初の文だけを候補にする。途中で切る処理は一切しない。
    complete_items = []
    for driver in drivers:
        sentence = first_complete_sentence(driver["detail"])
        if sentence:
            complete_items.append(sentence)

    base_lines = [
        f"【米国株｜{date_label}】",
        "■主要3指数（前日比）",
        *[format_index(item) for item in indices],
        "",
        "■市場総括",
        summary,
    ]

    # まず2件、入らなければ1件、さらに入らなければ材料なし。
    for count in (2, 1, 0):
        lines = list(base_lines)
        if count and complete_items:
            lines.append("■注目材料")
            lines.extend("・" + item for item in complete_items[:count])
        lines.extend([
            "",
            "詳細分析：" + MARKET_REPORT_URL,
            "#米国株 #S&P500 #NASDAQ100 #SOX",
        ])
        post = "\n".join(lines)
        if len(post) <= POST_LIMIT:
            return post, complete_items[:count]

    # 固定部分だけで上限超過する場合は警告し、無断で文章を切らない。
    lines = base_lines + ["", "詳細分析：" + MARKET_REPORT_URL]
    post = "\n".join(lines)
    return post, []


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    analysis = load_analysis()
    drivers, excluded = select_drivers(analysis)

    if excluded:
        logging.warning("自動採用せず、確認対象にした材料:")
        for title in excluded:
            logging.warning("  - %s", title)

    indices = []
    for item in INDICES:
        logging.info("%s の株価データを取得中...", item["name"])
        result = fetch_index(item["name"], item["ticker"])
        indices.append(result)
        logging.info(
            "%s: %s / 前日比 %+.2f%%",
            result["name"], result["date"], result["change_pct"]
        )

    dates = {item["date"] for item in indices}
    if len(dates) != 1:
        details = ", ".join(f'{x["name"]}={x["date"]}' for x in indices)
        raise RuntimeError(f"指数のデータ日が一致しません: {details}")

    post, included_sentences = build_post(indices, drivers)
    OUTPUT_FILE.write_text(post + "\n", encoding="utf-8")

    print("\n========== X投稿案（人による確認が必要） ==========\n")
    print(post)
    print(f"\n文字数（改行含む・単純計算）: {len(post)}")
    print(f"採用した完結文: {len(included_sentences)}件")
    print(f"確認対象として除外した材料: {len(excluded)}件")
    print(f"保存先: {OUTPUT_FILE}")
    if len(post) > POST_LIMIT:
        logging.warning("投稿案が目安上限%d文字を超えています。投稿前に確認してください。", POST_LIMIT)
    print("\n注意: 市場総括は指数の値動きから作成し、値動きの原因を断定しません。")
    print("注意: ニュースの真偽は検証しません。投稿前に出典を確認してください。")


if __name__ == "__main__":
    main()
