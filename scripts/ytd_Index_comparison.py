import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from pathlib import Path
import re

# ============================================================
# 1. 保存先の設定
# ============================================================

# このPythonファイルが置かれている場所から、GitHubリポジトリの
# ルートディレクトリを取得
BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_FILE = BASE_DIR / "ytd_Index_comparison.html"

# ============================================================
# 2. 対象銘柄の定義
# ============================================================

targets = [
    {"name": "S&P 500 (円建て)", "ticker": "^GSPC", "calc": "jpy"},
    {"name": "NASDAQ 100 (円建て)", "ticker": "^NDX", "calc": "jpy"},
    {"name": "日経平均株価", "ticker": "^N225", "calc": "raw"},
    {"name": "レバナス (為替ヘッジ有)", "ticker": "QLD", "calc": "raw"},
    {"name": "FANG+ (円建て)", "ticker": "FNGS", "calc": "jpy"},
]

print("年初来データを取得しています...")

# ============================================================
# 3. データ取得用の関数
# ============================================================

def remove_timezone(index):
    """
    日付インデックスのタイムゾーンを除去する。
    タイムゾーンがない場合もエラーにならないようにする。
    """
    if index.tz is not None:
        return index.tz_localize(None)

    return index


def get_close_prices(ticker):
    """
    Yahoo Financeから年初来の日次終値を取得する。
    """
    df = yf.Ticker(ticker).history(
        period="ytd",
        interval="1d",
        auto_adjust=True
    )

    if df is None or df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)

    close = df["Close"].dropna()
    close.index = remove_timezone(close.index)

    return close


# ============================================================
# 4. ドル円レートの取得
# ============================================================

try:
    usdjpy_close = get_close_prices("USDJPY=X")

    if usdjpy_close.empty:
        raise ValueError("ドル円レートを取得できませんでした")

    print(f"ドル円データ取得完了：{len(usdjpy_close)}日分")

except Exception as e:
    print(f"ドル円データの取得に失敗しました：{e}")
    raise


# ============================================================
# 5. 各銘柄のデータ取得と円換算
# ============================================================

ytd_prices = {}

for item in targets:

    name = item["name"]
    ticker = item["ticker"]
    calc = item["calc"]

    try:
        print(f"{name} のデータを取得中...")

        close = get_close_prices(ticker)

        if close.empty:
            print(f"警告：{name} のデータが空のためスキップします")
            continue

        # 米国銘柄を円換算する場合
        if calc == "jpy":

            combined = pd.concat(
                [
                    close.rename("Price"),
                    usdjpy_close.rename("USDJPY")
                ],
                axis=1,
                join="outer"
            ).sort_index()

            # 休場日などの欠損を直前の値で補完
            combined = combined.ffill().dropna()

            # ドル建て価格 × ドル円レート
            ytd_prices[name] = (
                combined["Price"] * combined["USDJPY"]
            )

        # 円建て指数など、追加換算が不要な場合
        else:
            ytd_prices[name] = close

        print(f"取得完了：{name}（{len(close)}日分）")

    except Exception as e:
        print(f"警告：{name} の取得に失敗しました：{e}")


# ============================================================
# 6. データを統合
# ============================================================

if not ytd_prices:
    raise RuntimeError(
        "すべての銘柄データの取得に失敗しました。"
        "Yahoo Financeへの接続状況を確認してください。"
    )

df_all = pd.DataFrame(ytd_prices).sort_index()

# 各銘柄の休場日などによる欠損を補完
df_all = df_all.ffill()

# 全銘柄で価格がそろっている日付だけを使用
df_all = df_all.dropna(how="any")

if df_all.empty:
    raise RuntimeError(
        "比較可能なデータがありません。取得期間や各銘柄のデータを確認してください。"
    )

# 凡例表示用に銘柄名から括弧内の説明を除去
clean_columns = [
    re.sub(r"\s*\(.*?\)", "", col)
    for col in df_all.columns
]

df_all.columns = clean_columns

# ============================================================
# 7. 年初来騰落率を計算
# ============================================================

# 最初の共通データ日を0%として計算
df_pct = (
    (df_all - df_all.iloc[0])
    / df_all.iloc[0]
) * 100.0

# 最新データの順位を計算
latest_pct = df_pct.iloc[-1].sort_values(ascending=False)

rank_dict = {
    name: i + 1
    for i, name in enumerate(latest_pct.index)
}

dates = df_pct.index

print("\n最新の年初来騰落率")
print("------------------------------")

for name, value in latest_pct.items():
    print(f"{rank_dict[name]}位：{name} {value:+.2f}%")


# ============================================================
# 8. チャート作成
# ============================================================

fig = go.Figure()

# 5つの資産を同時に描画
for col in df_pct.columns:

    fig.add_trace(
        go.Scatter(
            x=df_pct.index,
            y=df_pct[col],
            mode="lines",
            name=col,
            line=dict(width=2),
            hovertemplate=(
                "%{x|%Y-%m-%d}<br>"
                + col
                + ": %{y:+.2f}%"
                + "<extra></extra>"
            )
        )
    )


# ============================================================
# 9. イベント縦線と注釈
# ============================================================

# ※イベント日は元のプログラムで指定されていた日付を維持
target_march = "2026-03-30"
target_july = "2026-07-29"


def find_event_date(target_date):
    """
    指定日以降で、チャートに存在する最初の日付を返す。
    該当する日付がなければNoneを返す。
    """
    matching_dates = [
        d for d in dates
        if str(d)[:10] >= target_date
    ]

    return matching_dates[0] if matching_dates else None


march_event_date = find_event_date(target_march)
july_event_date = find_event_date(target_july)


# イラン戦争（指定日：2026年3月30日）
if march_event_date:

    fig.add_shape(
        type="line",
        x0=march_event_date,
        x1=march_event_date,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(
            color="#FF4444",
            width=1.5,
            dash="dash"
        )
    )

    fig.add_annotation(
        x=march_event_date,
        y=0.92,
        yref="paper",
        text="⚠️ イラン戦争",
        showarrow=False,
        xanchor="left",
        font=dict(
            size=11,
            color="#FF6666"
        )
    )


# AI・半導体調整（指定日：2026年7月29日）
if july_event_date:

    fig.add_shape(
        type="line",
        x0=july_event_date,
        x1=july_event_date,
        y0=0,
        y1=1,
        yref="paper",
        line=dict(
            color="#FFAA00",
            width=1.5,
            dash="dash"
        )
    )

    fig.add_annotation(
        x=july_event_date,
        y=0.84,
        yref="paper",
        text="⚠️ AI/半導体調整",
        showarrow=False,
        xanchor="left",
        font=dict(
            size=11,
            color="#FFCC00"
        )
    )


# ============================================================
# 10. チャート右端に順位と騰落率を表示
# ============================================================

last_date = dates[-1]

# 5位から1位の順番で配置
sorted_items = latest_pct.sort_values(ascending=True)

# 注釈の縦方向のずらし量
ay_offsets = [40, 20, 0, -20, -40]

for idx, (name, value) in enumerate(sorted_items.items()):

    rank = rank_dict[name]

    text = (
        f"<b>{rank}位：{name}</b><br>"
        f"{value:+.2f}%"
    )

    ay_val = ay_offsets[idx] if idx < len(ay_offsets) else 0

    fig.add_annotation(
        x=last_date,
        y=value,
        xref="x",
        yref="y",
        text=text,
        showarrow=True,
        arrowhead=2,
        ax=50,
        ay=ay_val,
        font=dict(
            size=10,
            color="#FFFFFF"
        ),
        bgcolor="#222222",
        bordercolor="#00CC44" if value >= 0 else "#FF3333",
        borderwidth=1,
        borderpad=3,
        opacity=0.9
    )


# ============================================================
# 11. レイアウト設定
# ============================================================

# 縦軸の表示範囲
y_min = min(0, df_pct.min().min() - 5)
y_max = max(0, df_pct.max().max() + 8)

fig.update_layout(

    title=dict(
        text="<b>年初来 騰落率推移</b>",
        x=0.02,
        y=0.96
    ),

    xaxis=dict(
        range=[dates[0], dates[-1]],
        title=None
    ),

    yaxis=dict(
        range=[y_min, y_max],
        zeroline=True,
        zerolinewidth=1.5,
        zerolinecolor="gray",
        ticksuffix="%",
        title="騰落率 (%)"
    ),

    hovermode="x unified",

    template="plotly_dark",

    height=800,
    autosize=True,

    margin=dict(
        r=170,
        t=70,
        b=100,
        l=60
    ),

    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.12,
        xanchor="center",
        x=0.5,
        font=dict(size=11)
    )
)


# ============================================================
# 12. HTMLファイルへ出力
# ============================================================

# HTMLを生成
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

# HTML全体の高さをブラウザの表示領域に合わせる
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

# HTMLを保存
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"チャートを出力しました: {OUTPUT_FILE}")
