#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""3指数と market_analysis.json から、確認用のX投稿案を生成する。
このスクリプトは投稿しない。生成文は必ず人が確認してから利用する。
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

# XのURLは通常23文字として扱われるため、余裕を持って上限を設定する。
POST_LIMIT = 270

INDICES = [
    {"name": "S&P500", "ticker": "^GSPC"},
    {"name": "NASDAQ100", "ticker": "^NDX"},
    {"name": "SOX", "ticker": "^SOX"},
]

# 個人に関する疑惑・捜査・不祥事など、裏付け確認が特に必要な話題は
# 自動で投稿文に採用せず、手動確認対象として除外する。
REVIEW_TERMS = (
    "疑惑", "不倫", "スパイ", "捜査", "調査", "逮捕", "不祥事",
    "fraud", "investigation", "investigated", "spy", "affair",
    "scandal", "arrest", "accusation", "allegation",
)


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


def clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def select_drivers(analysis: dict[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    selected: list[dict[str, str]] = []
    excluded: list[str] = []

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

        # 出典情報がない材料は自動採用しない。
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


def build_post(
    indices: list[dict[str, Any]],
    drivers: list[dict[str, str]],
) -> str:
    market_date = indices[0]["date"]
    date_label = market_date.replace("-", "/")

    lines = [
        f"【米国株マーケット｜{date_label}】",
        "■主要3指数（前日比）",
        *[format_index(item) for item in indices],
    ]

    if drivers:
        lines.extend(["", "■市場を動かした材料"])
        for driver in drivers:
            # 見出しだけでなく詳細説明を優先して要点を伝える。
            summary = driver["detail"]
            lines.append("・" + summary)

    lines.extend([
        "",
        "詳しいチャート・市場分析",
        MARKET_REPORT_URL,
        "#米国株 #S&P500 #NASDAQ100 #SOX",
    ])

    post = "\n".join(lines)

    # 長すぎる場合は詳細説明を短くする。指数・レポートURLは残す。
    if len(post) > POST_LIMIT and drivers:
        lines = [
            f"【米国株マーケット｜{date_label}】",
            "■主要3指数（前日比）",
            *[format_index(item) for item in indices],
            "",
            "■市場材料",
        ]
        for driver in drivers:
            summary = driver["detail"]
            # 文字数に余裕を持たせるため、各材料を短く要約表示。
            lines.append("・" + (summary[:34] + ("…" if len(summary) > 34 else "")))
        lines.extend([
            "",
            "詳しい分析：" + MARKET_REPORT_URL,
            "#米国株 #S&P500 #NASDAQ100 #SOX",
        ])
        post = "\n".join(lines)

    if len(post) > POST_LIMIT:
        logging.warning(
            "投稿案が%d文字です（目安上限%d文字）。手動で短縮してください。",
            len(post), POST_LIMIT
        )

    return post


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

    post = build_post(indices, drivers)
    OUTPUT_FILE.write_text(post + "\n", encoding="utf-8")

    print("\n========== X投稿案（人による確認が必要） ==========\n")
    print(post)
    print(f"\n文字数（改行含む・単純計算）: {len(post)}")
    print(f"採用した市場材料: {len(drivers)}件")
    print(f"確認対象として除外した材料: {len(excluded)}件")
    print(f"保存先: {OUTPUT_FILE}")
    print("\n注意: このプログラムはニュースの真偽を検証しません。投稿前に出典を確認してください。")


if __name__ == "__main__":
    main()
