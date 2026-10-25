import datetime
from pathlib import Path

import pandas as pd
import yfinance as yf
import plotly.graph_objects as go


# ============================================================
# 1. 基本設定
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "SP500_2026_target.html"

TARGET_PRICE = 8000.0
MAX_TRADING_DAYS = 252

current_year = pd.Timestamp.now().year
today_str = datetime.datetime.now().strftime("%Y/%m/%d")

COLOR_THIS_YEAR = "#F59E0B"
COLOR_PAST_AVG = "#3B82F6"
COLOR_TRUMP_AVG = "#E11D48"

print("S&P500 年末目標分析を開始します...")
print(f"実行日：{today_str}")
print(f"目標株価：{TARGET_PRICE:,.0f}ポイント")


# ============================================================
# 2. S&P500の日足データを取得
# ============================================================

sp500 = yf.Ticker("^GSPC")

df = sp500.history(
    period="25y",
    interval="1d",
    auto_adjust=True
)

if df is None or df.empty:
    raise RuntimeError(
        "S&P500の株価データを取得できませんでした。"
        "Yahoo Financeへの接続状況を確認してください。"
    )

# タイムゾーンを安全に除去
if df.index.tz is not None:
    df.index = df.index.tz_localize(None)

df = df.dropna(subset=["Close"]).copy()
df["Year"] = df.index.year

print(f"取得データ数：{len(df)}営業日")


# ============================================================
# 3. 各年の年初来騰落率を計算
# ============================================================

yearly_pct = {}
current_year_valid_len = 0

for year, group in df.groupby("Year"):

    group = group.sort_index()

    if len(group) < 10 and year != current_year:
        continue

    # 各年の最初の営業日の終値を0%とする
    base_price = group["Close"].iloc[0]

    pct_series = (
        (group["Close"] - base_price) / base_price
    ) * 100.0

    # 営業日順の整数インデックスに変更
    pct_series.index = range(len(pct_series))

    yearly_pct[year] = pct_series.round(2)

    if year == current_year:
        current_year_valid_len = len(group)


if current_year not in yearly_pct:
    raise RuntimeError(
        f"{current_year}年のS&P500データがありません。"
    )


df_yearly_pct = pd.DataFrame(yearly_pct).iloc[:MAX_TRADING_DAYS]


# ============================================================
# 4. 過去の比較グループを設定
# ============================================================

completed_years = sorted(
    [year for year in df_yearly_pct.columns if year < current_year]
)

last_20_years = completed_years[-20:]

# 元のプログラムで指定されていた年を維持
trump_years = [
    year
    for year in [2017, 2018, 2019, 2020, 2025]
    if year in df_yearly_pct.columns
]

if not last_20_years:
    raise RuntimeError("過去の比較データが不足しています。")

if not trump_years:
    raise RuntimeError("トランプ政権下の比較データが不足しています。")


# 過去20年平均
avg_past_20 = (
    df_yearly_pct[last_20_years]
    .ffill()
    .mean(axis=1)
    .round(2)
    .dropna()
)

# 指定年の平均
avg_trump = (
    df_yearly_pct[trump_years]
    .ffill()
    .mean(axis=1)
    .round(2)
    .dropna()
)


# ============================================================
# 5. 今年の実績と最新株価を取得
# ============================================================

current_year_df = df[df["Year"] == current_year].copy()

if current_year_df.empty:
    raise RuntimeError(
        f"{current_year}年の株価データを取得できませんでした。"
    )

base_price_current_year = float(
    current_year_df["Close"].iloc[0]
)

latest_close_price = float(
    current_year_df["Close"].iloc[-1]
)

latest_date_obj = current_year_df.index[-1]

current_year_pct = (
    (current_year_df["Close"] - base_price_current_year)
    / base_price_current_year
) * 100.0

current_year_pct = current_year_pct.round(2)

latest_pct_val = float(current_year_pct.iloc[-1])

latest_month = latest_date_obj.month
latest_day = latest_date_obj.day


# ============================================================
# 6. 8,000ポイントまでの残りポイントと必要上昇率
# ============================================================

remaining_pts = TARGET_PRICE - latest_close_price

required_pct_upside = (
    (TARGET_PRICE / latest_close_price) - 1
) * 100.0

# 目標株価を年初来騰落率に換算
target_pct = (
    (TARGET_PRICE / base_price_current_year) - 1
) * 100.0

print("\n現在の状況")
print("--------------------------------")
print(f"最新データ日：{latest_date_obj:%Y-%m-%d}")
print(f"最新S&P500：{latest_close_price:,.2f}ポイント")
print(f"年初来騰落率：{latest_pct_val:+.2f}%")
print(f"目標株価：{TARGET_PRICE:,.0f}ポイント")
print(f"目標までの残り：{remaining_pts:+,.2f}ポイント")
print(f"目標までの必要上昇率：{required_pct_upside:+.2f}%")
print("--------------------------------")


# ============================================================
# 7. チャート用の横軸を作成
# ============================================================

# 今年の実際の日付を基準に、過去の年を営業日順で比較する
current_year_dates = current_year_df.index.strftime("%m/%d").tolist()

dummy_year_dates = current_year_dates.copy()

# 年末までの横軸を補うため、前年の日付を利用
previous_year_df = df[df["Year"] == current_year - 1]

if len(dummy_year_dates) < MAX_TRADING_DAYS:
    ref_dates = previous_year_df.index.strftime("%m/%d").tolist()

    remaining_days = MAX_TRADING_DAYS - len(dummy_year_dates)

    dummy_year_dates.extend(
        ref_dates[len(dummy_year_dates):len(dummy_year_dates) + remaining_days]
    )

# 252営業日分に制限
dummy_year_dates = dummy_year_dates[:MAX_TRADING_DAYS]

# 月ごとの目盛り
month_start_days = [0, 21, 40, 62, 83, 104, 125, 147, 168, 189, 209, 228]

month_labels = [
    "1月", "2月", "3月", "4月", "5月", "6月",
    "7月", "8月", "9月", "10月", "11月", "12月"
]

month_start_dates = [
    dummy_year_dates[i]
    for i in month_start_days
    if i < len(dummy_year_dates)
]

month_labels = month_labels[:len(month_start_dates)]


# ============================================================
# 8. チャートを作成
# ============================================================

fig = go.Figure()


# ① 過去20年平均
fig.add_trace(
    go.Scatter(
        x=dummy_year_dates[:len(avg_past_20)],
        y=avg_past_20.values,
        mode="lines",
        name="過去20年平均",
        line=dict(
            color=COLOR_PAST_AVG,
            width=2
        ),
        hovertemplate=(
            "過去20年平均：<b>%{y:+.2f}%</b>"
            "<extra></extra>"
        )
    )
)


# ② トランプ政権下の指定年平均
fig.add_trace(
    go.Scatter(
        x=dummy_year_dates[:len(avg_trump)],
        y=avg_trump.values,
        mode="lines",
        name="トランプ政権下平均（指定年）",
        line=dict(
            color=COLOR_TRUMP_AVG,
            width=2
        ),
        hovertemplate=(
            "指定年平均：<b>%{y:+.2f}%</b>"
            "<extra></extra>"
        )
    )
)


# ③ 今年の実績
x_dates_this_year = dummy_year_dates[:len(current_year_pct)]

fig.add_trace(
    go.Scatter(
        x=x_dates_this_year,
        y=current_year_pct.values,
        mode="lines",
        name=f"{current_year}年実績",
        line=dict(
            color=COLOR_THIS_YEAR,
            width=3
        ),
        hovertemplate=(
            f"{current_year}年実績：<b>%{{y:+.2f}}%</b>"
            "<extra></extra>"
        )
    )
)


# ============================================================
# 9. 8,000ポイント目標線
# ============================================================

fig.add_hline(
    y=target_pct,
    line_dash="dash",
    line_color=COLOR_THIS_YEAR,
    line_width=1.5,
    annotation_text=(
        f"目標 8,000pt：年初比 {target_pct:+.2f}%"
    ),
    annotation_position="top right",
    annotation_font=dict(
        color=COLOR_THIS_YEAR,
        size=12
    )
)


# ============================================================
# 10. 最新実績から目標までの垂線と注釈
# ============================================================

latest_x_date = x_dates_this_year[-1]
latest_y = latest_pct_val

# 最新実績から目標ラインまで垂線を引く
fig.add_shape(
    type="line",
    x0=latest_x_date,
    y0=latest_y,
    x1=latest_x_date,
    y1=target_pct,
    line=dict(
        color=COLOR_THIS_YEAR,
        width=1.5,
        dash="dot"
    )
)

# 注釈の位置
mid_y = (latest_y + target_pct) / 2.0

if remaining_pts >= 0:
    remaining_text = (
        f"目標まで残り {remaining_pts:,.2f}pt"
        f"<br>必要上昇率 +{required_pct_upside:.2f}%"
    )
else:
    remaining_text = (
        f"目標を {abs(remaining_pts):,.2f}pt 上回る"
        f"<br>目標比 {required_pct_upside:+.2f}%"
    )

fig.add_annotation(
    x=latest_x_date,
    y=mid_y,
    text=remaining_text,
    showarrow=False,
    xanchor="right",
    align="right",
    font=dict(
        color=COLOR_THIS_YEAR,
        size=12
    ),
    bgcolor="rgba(0,0,0,0.75)",
    bordercolor=COLOR_THIS_YEAR,
    borderwidth=1,
    borderpad=5
)


# ============================================================
# 11. レイアウト設定
# ============================================================

fig.update_layout(
    title=dict(
        text=(
            f"<b>S&P 500 年末目標 8,000ポイントへの道のり</b>"
            f"<br><span style='font-size:13px; color:#888888; "
            f"font-weight:normal;'>"
            f"実行日：{today_str}｜最新データ：{latest_date_obj:%Y/%m/%d}"
            f"</span>"
        ),
        x=0.02,
        y=0.97
    ),

    height=800,
    autosize=True,

    margin=dict(
        l=65,
        r=65,
        t=105,
        b=100
    ),

    xaxis=dict(
        title="月",
        type="category",
        tickmode="array",
        tickvals=month_start_dates,
        ticktext=month_labels,
        showgrid=True,
        gridcolor="#222222"
    ),

    yaxis=dict(
        title="年初からの騰落率 (%)",
        zeroline=True,
        zerolinewidth=1.5,
        zerolinecolor="#666666",
        ticksuffix="%",
        showgrid=True,
        gridcolor="#222222"
    ),

    hovermode="x unified",
    template="plotly_dark",
    paper_bgcolor="#000000",
    plot_bgcolor="#111111",

    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="right",
        x=1
    )
)


# ============================================================
# 12. HTML出力
# ============================================================

full_html = fig.to_html(
    include_plotlyjs="cdn",
    full_html=True,
    config={
        "responsive": True,
        "displaylogo": False
    },
    default_height="100%",
    default_width="100%"
)

# iframe内のスクロールバーを防ぐ
full_html = full_html.replace(
    "<head>",
    """<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        html, body {
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
            overflow: hidden;
        }
        .plotly-graph-div {
            width: 100% !important;
            height: 100% !important;
        }
    </style>"""
)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(full_html)

print("\nHTML出力が完了しました")
print(f"保存先：{OUTPUT_FILE}")

# GitHub Actionsではブラウザ表示を行わない
# ローカルで確認する場合は、次の行のコメントを外してください。
# fig.show(config={"responsive": True})
