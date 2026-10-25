#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AIバリューチェーン株価ダッシュボード

プログラム:
    scripts/ai_value_chain_analysis.py

画像:
    assets/header_energy.png
    assets/header_semiconductor.png
    assets/header_datacenter.png
    assets/header_cloud.png
    assets/header_analysis.png
    assets/header_security.png
    assets/header_service.png

出力:
    ai_value_chain_analysis.html

機能:
    ・AIバリューチェーン7カテゴリーの株価分析
    ・S&P500、NASDAQ100、SOX、FANG+、POWR、NQCYBRの比較
    ・1日、1週間、1ヶ月、年初来の表示切り替え
    ・指数ごとのカテゴリー別ドット表示
    ・画像のBase64埋め込み
"""

import json
import base64
import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


# =========================================================
# 0. ディレクトリ設定
# =========================================================

# このPythonファイルがある場所
SCRIPT_DIR = Path(__file__).resolve().parent

# リポジトリのルート
BASE_DIR = SCRIPT_DIR.parent

# 画像フォルダ
ASSETS_DIR = BASE_DIR / "assets"

# HTML出力先
OUTPUT_FILE = BASE_DIR / "ai_value_chain_analysis.html"


# =========================================================
# 1. 画像読み込み
# =========================================================

def get_image_b64(file_name):
    """
    assetsフォルダ内の画像を読み込み、
    HTMLに埋め込めるBase64形式に変換する。
    """

    image_path = ASSETS_DIR / file_name

    if not image_path.exists() or not image_path.is_file():
        print(f"⚠️ 画像が見つかりません: {image_path}")
        return None

    try:
        data = image_path.read_bytes()

        ext = image_path.suffix.lower().lstrip(".")

        if ext in ("jpg", "jpeg"):
            mime = "image/jpeg"
        elif ext == "png":
            mime = "image/png"
        else:
            print(f"⚠️ 対応していない画像形式です: {image_path}")
            return None

        encoded = base64.b64encode(data).decode("utf-8")

        return f"data:{mime};base64,{encoded}"

    except Exception as e:
        print(f"⚠️ 画像読み込みエラー: {image_path} / {e}")
        return None


# 画像が読み込めなかった場合の代替画像
DEFAULT_FALLBACK_IMG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


# =========================================================
# 2. カテゴリー定義
# =========================================================

# 並び順は元のプログラムを維持
CATEGORIES = [
    (
        "energy",
        "エネルギー",
        "（電力）",
        "#38d65c",
        "header_energy.png",
    ),
    (
        "semiconductor",
        "半導体",
        "（チップ）",
        "#54d85a",
        "header_semiconductor.png",
    ),
    (
        "datacenter",
        "データセンター",
        "（物理インフラ）",
        "#25d5ef",
        "header_datacenter.png",
    ),
    (
        "cloud",
        "クラウド",
        "（プラットフォーム）",
        "#289dff",
        "header_cloud.png",
    ),
    (
        "analysis",
        "分析",
        "（学習・差別化の源泉）",
        "#b34be8",
        "header_analysis.png",
    ),
    (
        "security",
        "セキュリティ",
        "（安全性・信頼性の確保）",
        "#ff9900",
        "header_security.png",
    ),
    (
        "service",
        "サービス・アプリ",
        "（エンドユーザー）",
        "#f02f66",
        "header_service.png",
    ),
]


# =========================================================
# 3. 比較対象指数
# =========================================================

INDEX_DEFS = {
    "S&P500": "^GSPC",
    "NASDAQ100": "^NDX",
    "SOX": "^SOX",
    "FANG+": "FNGS",
    "POWR": "POWR",
    "NQCYBR": "CIBR",
}


# =========================================================
# 4. 指数ごとのカテゴリー別ドット数
# =========================================================

# カテゴリー順:
# エネルギー、半導体、データセンター、クラウド、
# 分析、セキュリティ、サービス・アプリ

DOT_COUNTS = {
    "S&P500":    [2, 3, 2, 3, 2, 2, 1],
    "NASDAQ100": [1, 3, 3, 4, 3, 2, 4],
    "SOX":       [0, 5, 0, 0, 0, 0, 0],
    "FANG+":     [0, 3, 0, 5, 1, 0, 1],
    "POWR":      [5, 0, 1, 0, 0, 0, 0],
    "NQCYBR":    [0, 0, 0, 0, 0, 4, 0],
}


# =========================================================
# 5. カテゴリー別構成銘柄
# =========================================================

STOCK_MAPPING = {
    "energy": [
        "CEG",
        "GEV",
        "VST",
    ],
    "semiconductor": [
        "NVDA",
        "AMD",
        "AVGO",
        "TSM",
        "ASML",
        "ARM",
        "MU",
    ],
    "datacenter": [
        "EQIX",
        "DLR",
        "SMCI",
    ],
    "cloud": [
        "MSFT",
        "AMZN",
        "GOOGL",
        "META",
    ],
    "analysis": [
        "PLTR",
        "SNOW",
        "DDOG",
    ],
    "security": [
        "PANW",
        "CRWD",
        "S",
    ],
    "service": [
        "NOW",
        "ADBE",
        "CRM",
    ],
}


# =========================================================
# 6. データ取得
# =========================================================

print("=" * 60)
print("AIバリューチェーン株価ダッシュボード")
print("=" * 60)

print(f"📁 リポジトリ: {BASE_DIR}")
print(f"🖼️ 画像フォルダ: {ASSETS_DIR}")
print(f"📄 出力先: {OUTPUT_FILE}")
print()

# 画像の存在確認
print("画像ファイルを確認しています...")

for _, title, _, _, image_name in CATEGORIES:
    image_path = ASSETS_DIR / image_name

    if image_path.exists():
        print(f"  ✅ {image_name}")
    else:
        print(f"  ⚠️ 見つかりません: {image_name}")

print()

# 全取得銘柄
stock_symbols = [
    symbol
    for symbols in STOCK_MAPPING.values()
    for symbol in symbols
]

all_symbols = list(dict.fromkeys(stock_symbols + list(INDEX_DEFS.values())))


# =========================================================
# 7. 時価総額取得
# =========================================================

print("📡 構成銘柄の時価総額を取得しています...")

market_caps = {}

for sym in stock_symbols:
    try:
        ticker = yf.Ticker(sym)
        market_cap = ticker.info.get("marketCap")

        if market_cap is not None and market_cap > 0:
            market_caps[sym] = float(market_cap)
        else:
            market_caps[sym] = 1.0

    except Exception as e:
        print(f"  ⚠️ 時価総額取得失敗: {sym} / {e}")
        market_caps[sym] = 1.0


# =========================================================
# 8. 日次データと前日終値の取得
# =========================================================

print("📈 日次株価データを取得しています...")

stock_daily_dict = {}
prev_close_dict = {}
index_1d_chg = {}

for sym in all_symbols:
    try:
        ticker = yf.Ticker(sym)

        hist = ticker.history(period="2y")

        if hist.empty or "Close" not in hist.columns:
            print(f"  ⚠️ 日次データなし: {sym}")
            continue

        close = hist["Close"].dropna()

        if len(close) >= 2:
            prev_close = float(close.iloc[-2])
            current_close = float(close.iloc[-1])

            if prev_close != 0:
                prev_close_dict[sym] = prev_close

                index_1d_chg[sym] = (
                    (current_close - prev_close)
                    / prev_close
                    * 100
                )

            stock_daily_dict[sym] = close

    except Exception as e:
        print(f"  ⚠️ 日次データ取得失敗: {sym} / {e}")


if not stock_daily_dict:
    raise RuntimeError(
        "株価データを取得できませんでした。"
        "Yahoo Financeへの接続状況を確認してください。"
    )

df_daily = pd.DataFrame(stock_daily_dict).sort_index()

df_daily = df_daily.ffill().bfill().dropna(how="all")


# =========================================================
# 9. 1日分の5分足データ
# =========================================================

print("⏱️ 5分足データを取得しています...")

stock_1d_norm_dict = {}

for sym in all_symbols:
    try:
        ticker = yf.Ticker(sym)

        hist_1d = ticker.history(
            period="7d",
            interval="5m",
        )

        if (
            hist_1d.empty
            or "Close" not in hist_1d.columns
            or sym not in prev_close_dict
        ):
            continue

        close = hist_1d["Close"].dropna()

        if close.empty:
            continue

        if close.index.tz is None:
            close.index = (
                close.index
                .tz_localize("UTC")
                .tz_convert("America/New_York")
            )
        else:
            close.index = close.index.tz_convert(
                "America/New_York"
            )

        # データ中で最も新しい日付を使用
        latest_date = close.index[-1].date()

        close_latest = close[
            close.index.date == latest_date
        ]

        market_open = datetime.time(9, 30)
        market_close = datetime.time(16, 0)

        close_market = close_latest[
            (close_latest.index.time >= market_open)
            & (close_latest.index.time <= market_close)
        ]

        if not close_market.empty:
            previous_close = prev_close_dict[sym]

            stock_1d_norm_dict[sym] = (
                close_market / previous_close
            ) * 100

    except Exception as e:
        print(f"  ⚠️ 5分足取得失敗: {sym} / {e}")


df_1d_raw = pd.DataFrame(stock_1d_norm_dict)

df_1d_norm = (
    df_1d_raw.sort_index()
    .ffill()
    .bfill()
)


# =========================================================
# 10. 1週間分の1時間足データ
# =========================================================

print("📊 1時間足データを取得しています...")

stock_1wk_norm_dict = {}

for sym in all_symbols:
    try:
        ticker = yf.Ticker(sym)

        hist_1wk = ticker.history(
            period="7d",
            interval="1h",
        )

        if hist_1wk.empty or "Close" not in hist_1wk.columns:
            continue

        close = hist_1wk["Close"].dropna()

        if close.empty:
            continue

        if close.index.tz is None:
            close.index = (
                close.index
                .tz_localize("UTC")
                .tz_convert("America/New_York")
            )
        else:
            close.index = close.index.tz_convert(
                "America/New_York"
            )

        first_value = float(close.iloc[0])

        if first_value > 0:
            stock_1wk_norm_dict[sym] = (
                close / first_value
            ) * 100

    except Exception as e:
        print(f"  ⚠️ 1時間足取得失敗: {sym} / {e}")


df_1wk_raw = pd.DataFrame(stock_1wk_norm_dict)

df_1wk_norm = (
    df_1wk_raw.sort_index()
    .ffill()
    .bfill()
)


# =========================================================
# 11. 時価総額加重平均
# =========================================================

def calc_weighted_series(df, symbols, mode_type=False):
    """
    指定された銘柄の時価総額加重平均系列を計算する。

    intraday:
        前日終値を100とした値を計算する。

    その他:
        対象期間の最初の値を100とした値を計算する。
    """

    if df.empty:
        return None

    valid_symbols = [
        symbol
        for symbol in symbols
        if symbol in df.columns
    ]

    if not valid_symbols:
        return None

    sub_df = df[valid_symbols].copy()

    weights = np.array(
        [
            market_caps.get(symbol, 1.0)
            for symbol in valid_symbols
        ],
        dtype=float,
    )

    total_weight = weights.sum()

    if total_weight <= 0:
        raw_weighted = sub_df.mean(axis=1)
    else:
        normalized_weights = weights / total_weight

        raw_weighted = (
            sub_df.mul(normalized_weights, axis=1)
            .sum(axis=1, min_count=1)
        )

    if mode_type == "intraday":
        return raw_weighted

    raw_weighted = raw_weighted.dropna()

    if raw_weighted.empty:
        return raw_weighted

    first_value = raw_weighted.iloc[0]

    if first_value > 0:
        return (raw_weighted / first_value) * 100

    return raw_weighted


# =========================================================
# 12. 期間別データを組み立てる
# =========================================================

periods_config = {
    "1d": "intraday",
    "1wk": "1wk",
    "1mo": 22,
    "ytd": "ytd",
}

data_by_period = {}

# 各カテゴリー画像を読み込み
category_images = {}

for _, title, _, _, image_name in CATEGORIES:
    category_images[image_name] = (
        get_image_b64(image_name)
        or DEFAULT_FALLBACK_IMG
    )

print()
print("🧮 期間別データを組み立てています...")


for period_key, mode in periods_config.items():

    if mode == "intraday":
        target_df = df_1d_norm

    elif mode == "1wk":
        target_df = df_1wk_norm

    elif mode == "ytd":
        current_year = df_daily.index[-1].year

        ytd_df = df_daily[
            df_daily.index.year == current_year
        ]

        if len(ytd_df) >= 2:
            target_df = ytd_df
        else:
            target_df = df_daily.iloc[-250:]

    else:
        target_df = (
            df_daily.iloc[-mode:]
            if len(df_daily) >= mode
            else df_daily
        )

    categories_payload = []

    # -----------------------------------------------------
    # カテゴリー別データ
    # -----------------------------------------------------

    for key, title, subtitle, color, image_name in CATEGORIES:

        category_series = calc_weighted_series(
            target_df,
            STOCK_MAPPING[key],
            mode_type=mode,
        )

        if (
            category_series is not None
            and not category_series.empty
        ):

            category_series = category_series.dropna()

            if period_key == "1d":
                labels = [
                    index.strftime("%H:%M")
                    for index in category_series.index
                ]

            elif period_key == "1wk":
                labels = [
                    index.strftime("%m/%d %H:%M")
                    for index in category_series.index
                ]

            else:
                labels = [
                    index.strftime("%Y-%m-%d")
                    for index in category_series.index
                ]

            series_data = [
                {
                    "date": label,
                    "value": round(float(value), 2),
                }
                for label, value in zip(
                    labels,
                    category_series,
                )
            ]

        else:
            series_data = []

        categories_payload.append(
            {
                "key": key,
                "title": title,
                "subtitle": subtitle,
                "color": color,
                "image": category_images[image_name],
                "symbols": STOCK_MAPPING[key],
                "series": series_data,
            }
        )

    # -----------------------------------------------------
    # 指数別データ
    # -----------------------------------------------------

    indices_payload = []

    index_colors = {
        "S&P500": "#93c5fd",
        "NASDAQ100": "#6ee7a8",
        "SOX": "#65b8ff",
        "FANG+": "#ffd166",
        "POWR": "#ff8a80",
        "NQCYBR": "#ffb74d",
    }

    for index_key, symbol in INDEX_DEFS.items():

        color = index_colors.get(
            index_key,
            "#ffffff",
        )

        change = 0.0
        series_data = []

        if period_key == "1d":

            change = index_1d_chg.get(symbol, 0.0)

            if symbol in target_df.columns:

                index_series = (
                    target_df[symbol]
                    .dropna()
                )

                if len(index_series) >= 2:

                    labels = [
                        index.strftime("%H:%M")
                        for index in index_series.index
                    ]

                    series_data = [
                        {
                            "date": label,
                            "value": round(float(value), 2),
                        }
                        for label, value in zip(
                            labels,
                            index_series,
                        )
                    ]

        else:

            if symbol in target_df.columns:

                index_series = (
                    target_df[symbol]
                    .dropna()
                )

                if len(index_series) >= 2:

                    first_value = float(
                        index_series.iloc[0]
                    )

                    if first_value != 0:

                        normalized = (
                            index_series / first_value
                        ) * 100

                        if period_key == "1wk":
                            labels = [
                                index.strftime("%m/%d %H:%M")
                                for index in normalized.index
                            ]
                        else:
                            labels = [
                                index.strftime("%Y-%m-%d")
                                for index in normalized.index
                            ]

                        series_data = [
                            {
                                "date": label,
                                "value": round(float(value), 2),
                            }
                            for label, value in zip(
                                labels,
                                normalized,
                            )
                        ]

                        change = (
                            (
                                float(index_series.iloc[-1])
                                - first_value
                            )
                            / first_value
                        ) * 100

        indices_payload.append(
            {
                "key": index_key,
                "label": index_key,
                "color": color,
                "change": round(float(change), 2),
                "dotCounts": DOT_COUNTS.get(
                    index_key,
                    [0, 0, 0, 0, 0, 0, 0],
                ),
                "series": series_data,
            }
        )

    # -----------------------------------------------------
    # 表示期間
    # -----------------------------------------------------

    if not target_df.empty:

        if mode == "intraday":

            start_time = target_df.index[0].strftime(
                "%Y-%m-%d %H:%M"
            )

            end_time = target_df.index[-1].strftime(
                "%H:%M"
            )

            range_string = (
                f"{start_time} 〜 {end_time} (米国東部時間)"
            )

        elif mode == "1wk":

            start_time = target_df.index[0].strftime(
                "%Y-%m-%d %H:%M"
            )

            end_time = target_df.index[-1].strftime(
                "%m-%d %H:%M"
            )

            range_string = (
                f"{start_time} 〜 {end_time} (米国東部時間)"
            )

        else:

            start_time = target_df.index[0].strftime(
                "%Y-%m-%d"
            )

            end_time = target_df.index[-1].strftime(
                "%Y-%m-%d"
            )

            range_string = (
                f"{start_time} 〜 {end_time}"
            )

    else:
        range_string = ""

    data_by_period[period_key] = {
        "dates": range_string,
        "categories": categories_payload,
        "indices": indices_payload,
    }


# =========================================================
# 13. HTMLテンプレート
# =========================================================

HTML_TEMPLATE = r'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>AIバリューチェーン株価ダッシュボード</title>

<style>
:root {
  color-scheme: dark;
  --bg: #080b0d;
  --panel: #111719;
  --line: #253033;
  --muted: #91a2a3;
  --text: #f0f5f3;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.5 system-ui, "Segoe UI", sans-serif;
}

header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 16px;
  flex-wrap: wrap;
}

h1 {
  font-size: 20px;
  margin: 0;
}

.period {
  color: var(--muted);
  font-size: 13px;
}

.period-btn-group {
  display: flex;
  gap: 6px;
  background: #182226;
  padding: 4px;
  border-radius: 6px;
  border: 1px solid var(--line);
}

.period-btn {
  background: transparent;
  border: none;
  color: var(--muted);
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.period-btn:hover {
  color: var(--text);
}

.period-btn.active {
  background: #2b3940;
  color: #31c487;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.dashboard {
  padding: 20px;
  overflow-x: auto;
}

.aligned {
  min-width: 1250px;
}

.cards {
  display: grid;
  grid-template-columns: 240px repeat(7, minmax(0, 1fr));
  gap: 10px;
}

.spacer {
  min-width: 0;
}

.category-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.category-card img {
  width: 100%;
  height: auto;
  object-fit: contain;
  display: block;
  background: #000;
  min-height: 80px;
}

.chart-wrap {
  padding: 10px;
  border-top: 1px solid var(--line);
  flex-grow: 1;
}

.cat-name {
  font-size: 18px;
  font-weight: bold;
  text-align: center;
  margin: 0 0 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chart {
  display: block;
  width: 100%;
  height: 130px;
}

.matrix {
  margin-top: 16px;
  padding: 16px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.matrix-grid {
  display: grid;
  grid-template-columns: 240px repeat(7, minmax(0, 1fr));
  align-items: center;
  gap: 12px 10px;
}

.index-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 12px;
  font-size: 15px;
  gap: 8px;
}

.index-label strong {
  font-weight: 600;
}

.dots {
  display: flex;
  justify-content: center;
  gap: 4px;
  flex-wrap: wrap;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  opacity: 0.95;
  display: inline-block;
}

.dot.green {
  background: #31c487;
}

.dot.red {
  background: #ff4444;
}

footer {
  padding: 0 24px 20px;
  color: var(--muted);
  font-size: 11px;
}

@media (max-width: 700px) {
  header {
    padding: 12px;
  }

  h1 {
    font-size: 17px;
  }

  .dashboard {
    padding: 10px;
  }

  .period-btn-group {
    width: 100%;
    justify-content: space-between;
  }

  .period-btn {
    padding: 7px 10px;
  }

  footer {
    padding: 0 12px 16px;
  }
}
</style>
</head>

<body>

<header>
  <div class="header-left">
    <h1>AIバリューチェーン株価ダッシュボード</h1>
    <div class="period" id="period"></div>
  </div>

  <div class="period-btn-group">
    <button class="period-btn active" onclick="updatePeriod('1d')">1日</button>
    <button class="period-btn" onclick="updatePeriod('1wk')">1週間</button>
    <button class="period-btn" onclick="updatePeriod('1mo')">1ヶ月</button>
    <button class="period-btn" onclick="updatePeriod('ytd')">年初来</button>
  </div>
</header>

<div class="dashboard">
  <div class="aligned">

    <section class="cards" id="cards-container"></section>

    <section class="matrix">
      <div class="matrix-grid" id="matrix-container"></div>
    </section>

  </div>
</div>

<footer>
  ※各カテゴリーは、選定した米国主要構成銘柄の時価総額加重平均を表示しています。
  1日表示は前日終値を100とした値、その他の期間は期間初値を100とした値です。
  ※指数のドット数は、設定されたカテゴリー別の関連度を示します。
</footer>

<script>
const ALL_PERIOD_DATA = __PERIOD_DATA_JSON__;

let currentPeriodKey = '1d';
let currentCategoryStatus = [];


function drawChart(canvas, points, color, is1d = false) {

  const ctx = canvas.getContext('2d');

  const rect = canvas.getBoundingClientRect();

  const dpr = window.devicePixelRatio || 1;

  canvas.width = Math.max(1, rect.width * dpr);
  canvas.height = Math.max(1, rect.height * dpr);

  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;

  if (!points || points.length < 2 || w <= 0 || h <= 0) {
    return;
  }

  const marginBottom = 20;
  const chartH = h - marginBottom;

  const values = points.map(p => p.value);

  let min = Math.min(...values);
  let max = Math.max(...values);

  if (is1d) {
    min = Math.min(min, 100.0);
    max = Math.max(max, 100.0);
  }

  const pad = 6;
  const range = (max - min) || 0.0001;

  const coords = points.map((p, i) => [
    pad + i * (w - 2 * pad) / (points.length - 1),
    chartH - pad - (p.value - min) * (chartH - 2 * pad) / range
  ]);

  // 折れ線
  ctx.beginPath();

  coords.forEach(([x, y], i) => {
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });

  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();

  // 横軸のラベル
  ctx.fillStyle = "#8899a6";
  ctx.font = "10px sans-serif";

  const firstDate = points[0].date || "";
  const midIndex = Math.floor((points.length - 1) / 2);
  const midDate = points[midIndex]?.date || "";
  const lastDate = points[points.length - 1]?.date || "";

  ctx.textAlign = "left";
  ctx.fillText(firstDate, pad, h - 4);

  if (points.length > 5) {

    ctx.textAlign = "center";

    const midX = pad
      + midIndex * (w - 2 * pad) / (points.length - 1);

    ctx.fillText(midDate, midX, h - 4);

    ctx.strokeStyle = "rgba(255,255,255,0.1)";
    ctx.lineWidth = 1;

    ctx.beginPath();
    ctx.moveTo(midX, pad);
    ctx.lineTo(midX, chartH - pad);
    ctx.stroke();
  }

  ctx.textAlign = "right";
  ctx.fillText(lastDate, w - pad, h - 4);
}


function renderAllCharts() {

  document.querySelectorAll('canvas[data-key]').forEach(canvas => {

    const key = canvas.dataset.key;

    const category = currentCategoryStatus.find(
      item => item.key === key
    );

    if (category) {
      drawChart(
        canvas,
        category.series,
        category.chartColor,
        currentPeriodKey === '1d'
      );
    }
  });
}


function updatePeriod(periodKey) {

  currentPeriodKey = periodKey;

  const DATA = ALL_PERIOD_DATA[periodKey];

  if (!DATA) {
    return;
  }

  // 選択中ボタンの表示
  document.querySelectorAll('.period-btn').forEach(button => {

    const isTarget = button.getAttribute('onclick')
      .includes(`'${periodKey}'`);

    button.classList.toggle('active', isTarget);
  });

  document.getElementById('period').textContent =
    DATA.dates || '';

  // カテゴリーの騰落率を計算
  currentCategoryStatus = DATA.categories.map(category => {

    const series = category.series || [];

    const lastValue = series.length
      ? series[series.length - 1].value
      : 100;

    const changePct = lastValue - 100;

    const isPositive = changePct >= 0;

    const chartColor = isPositive
      ? '#31c487'
      : '#ff4444';

    return {
      ...category,
      changePct,
      isPositive,
      chartColor
    };
  });

  // -------------------------------------------------------
  // カテゴリーカード
  // -------------------------------------------------------

  const cardsContainer =
    document.getElementById('cards-container');

  let cardsHTML = '<div class="spacer"></div>';

  currentCategoryStatus.forEach(category => {

    const sign = category.changePct >= 0 ? '+' : '';

    const changeText =
      `${sign}${category.changePct.toFixed(2)}%`;

    const symbolsText = category.symbols
      ? category.symbols.join(', ')
      : '';

    cardsHTML += `
      <article
        class="category-card"
        title="構成銘柄: ${symbolsText}"
      >
        <img
          src="${category.image}"
          alt="${category.title}"
        >

        <div class="chart-wrap">

          <div class="cat-name">
            <span style="color:${category.chartColor};font-weight:bold;">
              ${changeText}
            </span>
          </div>

          <canvas
            class="chart"
            data-key="${category.key}"
          ></canvas>

        </div>
      </article>
    `;
  });

  cardsContainer.innerHTML = cardsHTML;

  // -------------------------------------------------------
  // 指数とドットマトリクス
  // -------------------------------------------------------

  const matrixContainer =
    document.getElementById('matrix-container');

  let matrixHTML = '';

  DATA.indices.forEach(index => {

    const changeColor = index.change >= 0
      ? '#31c487'
      : '#ff4444';

    const sign = index.change >= 0 ? '+' : '';

    const changeText =
      `${sign}${index.change.toFixed(2)}%`;

    matrixHTML += `
      <div class="index-label">
        <strong>${index.label}</strong>
        <span style="color:${changeColor}">
          ${changeText}
        </span>
      </div>
    `;

    currentCategoryStatus.forEach((category, indexPosition) => {

      const count =
        index.dotCounts[indexPosition] || 0;

      const dotClass = category.isPositive
        ? 'green'
        : 'red';

      const dots = `<i class="dot ${dotClass}"></i>`
        .repeat(count);

      matrixHTML += `
        <div class="dots">${dots}</div>
      `;
    });
  });

  matrixContainer.innerHTML = matrixHTML;

  // DOM更新後にチャートを描画
  requestAnimationFrame(renderAllCharts);
}


// 初期表示
updatePeriod('1d');

// 画面サイズ変更時に再描画
window.addEventListener('resize', renderAllCharts);
</script>

</body>
</html>
'''


# =========================================================
# 14. HTML出力
# =========================================================

print()
print("💾 HTMLファイルを生成しています...")

html_out = HTML_TEMPLATE.replace(
    "__PERIOD_DATA_JSON__",
    json.dumps(
        data_by_period,
        ensure_ascii=False,
        allow_nan=False,
    ),
)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_FILE.write_text(
    html_out,
    encoding="utf-8",
)

print()
print("=" * 60)
print("✅ HTMLの生成が完了しました")
print(f"📄 出力ファイル: {OUTPUT_FILE}")
print("=" * 60)
