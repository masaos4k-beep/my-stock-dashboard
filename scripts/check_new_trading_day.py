import os
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf


# ==========================================
# 設定
# ==========================================

TZ = ZoneInfo("America/New_York")
CUTOFF = time(16, 15)

SYMBOLS = [
    {"name": "NASDAQ100", "ticker": "^NDX"},
    {"name": "SOX", "ticker": "^SOX"},
    {"name": "FANG+", "ticker": "^NYFANG"},
    {"name": "S&P500", "ticker": "^GSPC"},
    {"name": "Russell2000", "ticker": "^RUT"},
    {"name": "Dow", "ticker": "^DJI"},
]

LAST_DATE_FILE = Path("data/last_processed_trading_day.txt")


# ==========================================
# GitHub Actionsへの結果出力
# ==========================================

def set_output(name, value):
    github_output = os.getenv("GITHUB_OUTPUT")

    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")

    print(f"{name}={value}")


# ==========================================
# 各指数の最新完了取引日を取得
# ==========================================

def get_latest_completed_date(item):

    ticker = item["ticker"]
    name = item["name"]

    print(f"データ確認中: {name} ({ticker})")

    df = yf.Ticker(ticker).history(
        period="10d",
        interval="1d",
        auto_adjust=False,
        actions=False
    )

    if df is None or df.empty:
        raise RuntimeError(f"{name}: 日足データを取得できません")

    index = pd.DatetimeIndex(df.index)

    if index.tz is None:
        index = index.tz_localize(TZ)
    else:
        index = index.tz_convert(TZ)

    dates = sorted(set(index.date))

    now_ny = datetime.now(TZ)
    today_ny = now_ny.date()

    # 16:15より前の当日データは未確定として除外
    completed_dates = [
        d for d in dates
        if d < today_ny
        or (d == today_ny and now_ny.time() >= CUTOFF)
    ]

    if not completed_dates:
        raise RuntimeError(f"{name}: 完了済み取引日がありません")

    latest_date = completed_dates[-1]

    print(f"{name}: 最新完了取引日 = {latest_date}")

    return latest_date


# ==========================================
# メイン処理
# ==========================================

def main():

    try:
        latest_dates = []

        for item in SYMBOLS:
            date = get_latest_completed_date(item)
            latest_dates.append(date)

        # 6指数すべてのデータ日付が一致するか確認
        unique_dates = set(latest_dates)

        if len(unique_dates) != 1:
            print("6指数のデータ日付が一致しません。")
            print("安全のためDaily Updateをスキップします。")
            set_output("has_new_data", "false")
            return

        latest_date = latest_dates[0]
        print(f"6指数共通の最新取引日: {latest_date}")

        # 前回処理済みの日付を確認
        if LAST_DATE_FILE.exists():
            last_date = datetime.strptime(
                LAST_DATE_FILE.read_text(encoding="utf-8").strip(),
                "%Y-%m-%d"
            ).date()
        else:
            last_date = None

        print(f"前回処理済みの日付: {last_date}")

        # 新しい取引日があるか判定
        if last_date is None or latest_date > last_date:
            print("新しい取引日を確認しました。Daily Updateを実行します。")
            set_output("has_new_data", "true")
            set_output("latest_date", latest_date.isoformat())
        else:
            print("新しい取引データはありません。Daily Updateをスキップします。")
            set_output("has_new_data", "false")

    except Exception as e:
        print(f"データ確認エラー: {e}")
        print("安全のためDaily Updateをスキップします。")
        set_output("has_new_data", "false")


if __name__ == "__main__":
    main()
