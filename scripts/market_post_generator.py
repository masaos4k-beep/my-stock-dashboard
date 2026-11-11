#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""株価3指数と market_analysis.json からX投稿案を生成する（投稿はしません）。"""

import json
import logging
from pathlib import Path
from typing import Any

import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_FILE = ROOT / "market_analysis.json"
OUTPUT_FILE = ROOT / "market_post.txt"
MARKET_REPORT_URL = "https://www.beyondworklife.com/market_report.html"
MAX_POST_LENGTH = 280

INDICES = [
    {"name": "S&P500", "ticker": "^GSPC"},
    {"name": "NASDAQ100", "ticker": "^NDX"},
    {"name": "SOX", "ticker": "^SOX"},
]


def load_analysis() -> dict[str, Any]:
    if not ANALYSIS_FILE.exists():
        raise FileNotFoundError(f"市場分析ファイルがありません: {ANALYSIS_FILE}")
    with ANALYSIS_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("drivers", []), list):
        raise ValueError("market_analysis.json の形式が正しくありません。")
    return data


def fetch_index(name: str, ticker: str) -> dict[str, Any]:
    # 直近10日の日足から、最新終値とその直前の終値を比較する
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


def format_index(item: dict[str, Any]) -> str:
    pct = item["change_pct"]
    sign = "+" if pct >= 0 else ""
    return f'{item["name"]} {item["close"]:,.2f}（{sign}{pct:.2f}%）'


def build_post(indices: list[dict[str, Any]], analysis: dict[str, Any]) -> str:
    market_date = indices[0]["date"]
    date_label = market_date.replace("-", "/")
    lines = [
        f"【米国株マーケット｜{date_label}】",
        "■主要3指数（前日比）",
        *[format_index(item) for item in indices],
    ]

    driver_lines = []
    for driver in analysis.get("drivers", [])[:3]:
        if isinstance(driver, dict) and isinstance(driver.get("title"), str):
            title = " ".join(driver["title"].split())
            if title:
                driver_lines.append("・" + title)

    if driver_lines:
        lines.extend(["", "■市場を動かした材料", *driver_lines])

    analysis_date = analysis.get("report_date")
    if analysis_date and analysis_date != market_date:
        lines.extend(["", f"※ニュース分析日：{analysis_date}"])

    lines.extend([
        "",
        f"詳しいチャート・市場分析はこちら",
        MARKET_REPORT_URL,
        "",
        "#米国株 #S&P500 #NASDAQ100 #SOX",
    ])
    post = "\n".join(lines)

    # 長すぎる場合はニュース見出しを短縮する。指数データとリンクは残す。
    if len(post) > MAX_POST_LENGTH and driver_lines:
        compact = [
            f"【米国株マーケット｜{date_label}】",
            "■主要3指数（前日比）",
            *[format_index(item) for item in indices],
            "",
            "■市場材料",
        ]
        for line in driver_lines:
            title = line[1:]
            compact.append("・" + (title[:22] + ("…" if len(title) > 22 else "")))
        if analysis_date and analysis_date != market_date:
            compact.extend(["", f"※ニュース分析日：{analysis_date}"])
        compact.extend([
            "",
            "詳細分析：" + MARKET_REPORT_URL,
            "#米国株 #S&P500 #NASDAQ100 #SOX",
        ])
        post = "\n".join(compact)

    if len(post) > MAX_POST_LENGTH:
        logging.warning("投稿案が%d文字です。280文字以内か確認してください。", len(post))
    return post


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    analysis = load_analysis()

    indices = []
    for item in INDICES:
        logging.info("%s の株価データを取得中...", item["name"])
        result = fetch_index(item["name"], item["ticker"])
        indices.append(result)
        logging.info("%s: %s / 前日比 %+.2f%%",
                     result["name"], result["date"], result["change_pct"])

    # 指数間で異なる営業日のデータが混ざる場合は投稿案を作らない
    dates = {item["date"] for item in indices}
    if len(dates) != 1:
        details = ", ".join(f'{x["name"]}={x["date"]}' for x in indices)
        raise RuntimeError(f"指数のデータ日が一致しません: {details}")

    post = build_post(indices, analysis)
    OUTPUT_FILE.write_text(post + "\n", encoding="utf-8")
    print("\n========== X投稿案 ==========\n")
    print(post)
    print(f"\n文字数（改行含む）: {len(post)}")
    print(f"保存先: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
