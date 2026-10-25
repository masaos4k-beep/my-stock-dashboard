from pathlib import Path

import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go


# =========================================================
# 1. 出力先設定
# =========================================================

# scripts フォルダの1階層上をリポジトリのルートとする
BASE_DIR = Path(__file__).resolve().parent.parent

HTML_FILE = BASE_DIR / "ai_value_chain_heatmap.html"


# =========================================================
# 2. AIバリューチェーン構造
# =========================================================

data_structure = {
    "Category": (
        ["電力"] * 3
        + ["半導体"] * 11
        + ["データセンター"] * 3
        + ["クラウド"] * 4
        + ["分析"] * 3
        + ["セキュリティ"] * 3
        + ["サービス"] * 3
    ),

    "Symbol": [
        "CEG", "GEV", "VST",
        "NVDA", "AMD", "AVGO", "TSM",
        "6857.T", "8035.T", "ASML", "ARM",
        "MU", "000660.KS", "KXIAY",
        "EQIX", "DLR", "SMCI",
        "MSFT", "AMZN", "GOOGL", "META",
        "PLTR", "SNOW", "DDOG",
        "PANW", "CRWD", "S",
        "NOW", "ADBE", "CRM",
    ],

    "ShortName": [
        "Constellation", "GE Vernova", "Vistra",
        "NVIDIA", "AMD", "Broadcom", "TSMC",
        "アドバンテスト", "東京エレクトロン",
        "ASML", "ARM", "Micron",
        "SKハイニックス", "キオクシア",
        "Equinix", "Digital Rty", "Supermicro",
        "Microsoft", "Amazon", "Alphabet", "Meta",
        "Palantir", "Snowflake", "Datadog",
        "Palo Alto", "CrowdStrike", "SentinelOne",
        "ServiceNow", "Adobe", "Salesforce",
    ],
}

df = pd.DataFrame(data_structure)


# =========================================================
# 3. 騰落率計算関数
# =========================================================

def calc_period_change(series):
    """期間の最初と最後の終値から騰落率を計算する。"""

    clean_series = series.dropna()

    if len(clean_series) >= 2:

        start_val = float(clean_series.iloc[0])
        end_val = float(clean_series.iloc[-1])

        if start_val > 0:

            pct = (
                (end_val - start_val)
                / start_val
                * 100.0
            )

            return pct, f"{pct:+.2f}%"

    return 0.0, "+0.00%"


# =========================================================
# 4. 為替レート取得
# =========================================================

try:

    jpy_history = yf.Ticker("USDJPY=X").history(
        period="5d",
        auto_adjust=False,
    )

    krw_history = yf.Ticker("USDKRW=X").history(
        period="5d",
        auto_adjust=False,
    )

    fx_jpy = (
        float(jpy_history["Close"].dropna().iloc[-1])
        if not jpy_history.empty
        else 150.0
    )

    fx_krw = (
        float(krw_history["Close"].dropna().iloc[-1])
        if not krw_history.empty
        else 1350.0
    )

except Exception as e:

    print(f"為替取得エラー: {e}")

    fx_jpy = 150.0
    fx_krw = 1350.0


# =========================================================
# 5. 株価・時価総額取得
# =========================================================

print("株価データを取得しています...")


market_caps = []

val_1d, val_1w, val_1m, val_ytd = [], [], [], []

lbl_1d, lbl_1w, lbl_1m, lbl_ytd = [], [], [], []


for name, symbol in zip(
    df["ShortName"],
    df["Symbol"],
):

    print(f"取得中: {name} ({symbol})")

    # データ取得失敗時の初期値
    usd_cap = 500.0

    v1d, l1d = 0.0, "+0.00%"
    v1w, l1w = 0.0, "+0.00%"
    v1m, l1m = 0.0, "+0.00%"
    vytd, lytd = 0.0, "+0.00%"

    try:

        tk = yf.Ticker(symbol)

        info = tk.info

        raw_cap = info.get("marketCap", 0) or 0

        currency = info.get("currency", "USD")

        # ---------------------------------------------
        # 時価総額を億ドル単位に換算
        # ---------------------------------------------

        if raw_cap > 0:

            if currency == "JPY":

                usd_cap = raw_cap / fx_jpy / 10**8

            elif currency == "KRW":

                usd_cap = raw_cap / fx_krw / 10**8

            else:

                usd_cap = raw_cap / 10**8

        # ---------------------------------------------
        # 1日騰落率
        # ---------------------------------------------

        prev_close = (
            info.get("previousClose", 0)
            or info.get("regularMarketPreviousClose", 0)
        )

        current_price = (
            info.get("currentPrice", 0)
            or info.get("regularMarketPrice", 0)
        )

        if prev_close > 0 and current_price > 0:

            v1d = (
                (current_price - prev_close)
                / prev_close
                * 100.0
            )

            l1d = f"{v1d:+.2f}%"

        else:

            h1 = tk.history(
                period="7d",
                interval="1d",
                auto_adjust=False,
            )["Close"].dropna()

            if len(h1) >= 2:

                v1d, l1d = calc_period_change(
                    h1.tail(2)
                )

        # ---------------------------------------------
        # 1週間騰落率
        # ---------------------------------------------

        hw = tk.history(
            period="1mo",
            interval="1d",
            auto_adjust=False,
        )["Close"].dropna()

        if len(hw) >= 2:

            v1w, l1w = calc_period_change(
                hw.tail(min(len(hw), 6))
            )

        # ---------------------------------------------
        # 1ヶ月騰落率
        # ---------------------------------------------

        hm = tk.history(
            period="1mo",
            interval="1d",
            auto_adjust=False,
        )["Close"].dropna()

        v1m, l1m = calc_period_change(hm)

        # ---------------------------------------------
        # 年初来騰落率
        # ---------------------------------------------

        hy = tk.history(
            period="ytd",
            interval="1d",
            auto_adjust=False,
        )["Close"].dropna()

        vytd, lytd = calc_period_change(hy)

    except Exception as e:

        print(f"  ⚠️ 取得エラー: {symbol} / {e}")

    market_caps.append(usd_cap)

    val_1d.append(v1d)
    lbl_1d.append(l1d)

    val_1w.append(v1w)
    lbl_1w.append(l1w)

    val_1m.append(v1m)
    lbl_1m.append(l1m)

    val_ytd.append(vytd)
    lbl_ytd.append(lytd)


df["MarketCap"] = market_caps

df["V_1D"] = val_1d
df["V_1W"] = val_1w
df["V_1M"] = val_1m
df["V_YTD"] = val_ytd

df["L_1D"] = lbl_1d
df["L_1W"] = lbl_1w
df["L_1M"] = lbl_1m
df["L_YTD"] = lbl_ytd


# =========================================================
# 6. カラースケール
# =========================================================

custom_colorscale = [
    [0.00, "#A30000"],
    [0.35, "#D62728"],
    [0.47, "#331515"],
    [0.50, "#222222"],
    [0.53, "#153315"],
    [0.65, "#2CA02C"],
    [1.00, "#00A300"],
]


def get_auto_scale_range(values_list):

    valid_values = [
        float(v)
        for v in values_list
        if pd.notna(v)
    ]

    if not valid_values:
        return [-5.0, 5.0]

    v_max = max(
        abs(max(valid_values)),
        abs(min(valid_values)),
    )

    limit = max(v_max, 5.0)

    return [-limit, limit]


range_1d = get_auto_scale_range(df["V_1D"].tolist())
range_1w = get_auto_scale_range(df["V_1W"].tolist())
range_1m = get_auto_scale_range(df["V_1M"].tolist())
range_ytd = get_auto_scale_range(df["V_YTD"].tolist())


# =========================================================
# 7. Treemap作成関数
# =========================================================

def create_treemap(value_col, label_col, color_range):

    temp_fig = px.treemap(
        df,
        path=[
            px.Constant("全AIバリューチェーン"),
            "Category",
            "ShortName",
        ],
        values="MarketCap",
        color=value_col,
        color_continuous_scale=custom_colorscale,
        color_continuous_midpoint=0,
        range_color=color_range,
        custom_data=[
            "Symbol",
            "MarketCap",
            label_col,
        ],
    )

    # 親階層の色をクリア
    colors = list(temp_fig.data[0].marker.colors)

    parent_ids = set(temp_fig.data[0].parents)

    for idx, node_id in enumerate(temp_fig.data[0].ids):

        if node_id in parent_ids:
            colors[idx] = None

    temp_fig.data[0].marker.colors = colors

    temp_fig.update_traces(
        texttemplate="<b>%{label}</b><br>(%{customdata[2]})",

        hovertemplate=(
            "<b>%{label}</b> (%{customdata[0]})"
            "<br>騰落率: %{customdata[2]}"
            "<br>時価総額: %{customdata[1]:,.0f}億ドル"
            "<extra></extra>"
        ),

        insidetextfont=dict(
            size=11.7,
            color="white",
        ),

        marker=dict(
            line=dict(
                width=1.5,
                color="black",
            )
        ),
    )

    return temp_fig.data[0]


trace_1d = create_treemap("V_1D", "L_1D", range_1d)
trace_1w = create_treemap("V_1W", "L_1W", range_1w)
trace_1m = create_treemap("V_1M", "L_1M", range_1m)
trace_ytd = create_treemap("V_YTD", "L_YTD", range_ytd)


# =========================================================
# 8. Figure作成
# =========================================================

fig = go.Figure()

fig.add_trace(trace_1d)
fig.add_trace(trace_1w)
fig.add_trace(trace_1m)
fig.add_trace(trace_ytd)

fig.data[0].visible = True
fig.data[1].visible = False
fig.data[2].visible = False
fig.data[3].visible = False


# カラーバーはcoloraxisに統一
fig.update_traces(
    marker=dict(
        coloraxis="coloraxis"
    )
)


fig.update_layout(

    # ★重要：Plotly側のタイトルを明示的に削除
    title=None,

    coloraxis=dict(
        colorscale=custom_colorscale,
        cmin=range_1d[0],
        cmax=range_1d[1],

        colorbar=dict(
            title=dict(
                text="1日騰落率 (%)",
                font=dict(
                    color="white",
                    size=13,
                ),
            ),

            tickfont=dict(
                color="white",
            ),

            x=1.01,
        ),
    ),

    font=dict(
        size=11.7,
        color="white",
    ),

    template="plotly_dark",

    paper_bgcolor="#080b0d",
    plot_bgcolor="#080b0d",

    autosize=True,

    # タイトルを削除したので上部余白を縮小
    margin=dict(
        t=10,
        l=10,
        r=100,
        b=10,
    ),

    uniformtext=dict(
        minsize=8,
        mode="hide",
    ),
)


# =========================================================
# 9. Plotly HTML生成
# =========================================================

print("HTMLを生成しています...")


plot_html = fig.to_html(
    include_plotlyjs="cdn",
    full_html=False,

    config={
        "responsive": True,
        "displaylogo": False,
    },

    div_id="heatmap-chart",

    default_height="100%",
    default_width="100%",
)


# =========================================================
# 10. HTML全体
# =========================================================

html_template = r"""
<!DOCTYPE html>
<html lang="ja">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1"
>

<title>AIバリューチェーン 期間別ヒートマップ</title>

<style>

* {
    box-sizing: border-box;
}

html,
body {
    margin: 0;
    padding: 0;

    width: 100%;
    height: 100%;

    overflow: hidden;

    background: #080b0d;
    color: #f0f5f3;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        "Noto Sans JP",
        sans-serif;
}

.topbar {
    width: 100%;
    height: 76px;

    display: flex;
    justify-content: space-between;
    align-items: center;

    gap: 16px;

    padding: 10px 20px;

    background: #0b1012;
    border-bottom: 1px solid #29363a;
}

.page-title {
    font-size: 21px;
    font-weight: 700;
    color: #f0f5f3;
}

.period-buttons {
    display: flex;
    gap: 6px;
    align-items: center;

    padding: 4px;

    border: 1px solid #29363a;
    border-radius: 8px;

    background: #151e22;
}

.period-btn {
    min-width: 76px;

    padding: 10px 14px;

    border: 1px solid transparent;
    border-radius: 6px;

    background: transparent;
    color: #a0b0b2;

    font-size: 14px;
    font-weight: 700;

    cursor: pointer;
}

.period-btn:hover {
    background: #243239;
    color: #ffffff;
}

.period-btn.active {
    background: #289dff;
    color: #ffffff;
    border-color: #289dff;
}

.chart-container {
    width: 100%;
    height: calc(100vh - 76px);

    padding: 0;
    margin: 0;

    overflow: hidden;
}

#heatmap-chart {
    width: 100% !important;
    height: 100% !important;
}

.js-plotly-plot,
.plot-container,
.svg-container {
    max-width: 100%;
}

@media (max-width: 700px) {

    .topbar {
        height: auto;
        min-height: 110px;

        padding: 10px;

        align-items: flex-start;
        flex-direction: column;
    }

    .page-title {
        font-size: 17px;
    }

    .period-buttons {
        width: 100%;

        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .period-btn {
        min-width: 0;
        padding: 9px 4px;
        font-size: 12px;
    }

    .chart-container {
        height: calc(100vh - 110px);
    }
}

</style>

</head>

<body>

<header class="topbar">

    <div class="page-title">
        AIバリューチェーン 期間別ヒートマップ
    </div>

    <nav
        class="period-buttons"
        aria-label="表示期間"
    >

        <button
            type="button"
            class="period-btn active"
            data-period="0"
        >
            1日
        </button>

        <button
            type="button"
            class="period-btn"
            data-period="1"
        >
            1週間
        </button>

        <button
            type="button"
            class="period-btn"
            data-period="2"
        >
            1ヶ月
        </button>

        <button
            type="button"
            class="period-btn"
            data-period="3"
        >
            年初来
        </button>

    </nav>

</header>

<main class="chart-container">

__PLOT_HTML__

</main>

<script>

const periodSettings = [
    {
        title: "1日騰落率 (%)",
        cmin: __RANGE_1D_MIN__,
        cmax: __RANGE_1D_MAX__
    },
    {
        title: "1週間騰落率 (%)",
        cmin: __RANGE_1W_MIN__,
        cmax: __RANGE_1W_MAX__
    },
    {
        title: "1ヶ月騰落率 (%)",
        cmin: __RANGE_1M_MIN__,
        cmax: __RANGE_1M_MAX__
    },
    {
        title: "年初来騰落率 (%)",
        cmin: __RANGE_YTD_MIN__,
        cmax: __RANGE_YTD_MAX__
    }
];


function changePeriod(index) {

    const visible = [
        false,
        false,
        false,
        false
    ];

    visible[index] = true;

    const settings = periodSettings[index];

    Plotly.update(
        "heatmap-chart",

        {
            visible: visible
        },

        {
            "coloraxis.cmin": settings.cmin,
            "coloraxis.cmax": settings.cmax,
            "coloraxis.colorbar.title.text": settings.title
        }
    );

    document.querySelectorAll(".period-btn").forEach(
        (button, buttonIndex) => {

            button.classList.toggle(
                "active",
                buttonIndex === index
            );
        }
    );
}


document.querySelectorAll(".period-btn").forEach(
    button => {

        button.addEventListener("click", () => {

            changePeriod(
                Number(button.dataset.period)
            );

        });
    }
);


window.addEventListener("resize", () => {

    const chart = document.getElementById(
        "heatmap-chart"
    );

    if (chart) {
        Plotly.Plots.resize(chart);
    }

});

</script>

</body>
</html>
"""


# =========================================================
# 11. 値を埋め込んで保存
# =========================================================

html_content = html_template.replace(
    "__PLOT_HTML__",
    plot_html,
)

replacements = {
    "__RANGE_1D_MIN__": range_1d[0],
    "__RANGE_1D_MAX__": range_1d[1],

    "__RANGE_1W_MIN__": range_1w[0],
    "__RANGE_1W_MAX__": range_1w[1],

    "__RANGE_1M_MIN__": range_1m[0],
    "__RANGE_1M_MAX__": range_1m[1],

    "__RANGE_YTD_MIN__": range_ytd[0],
    "__RANGE_YTD_MAX__": range_ytd[1],
}

for placeholder, value in replacements.items():

    html_content = html_content.replace(
        placeholder,
        str(value),
    )


HTML_FILE.write_text(
    html_content,
    encoding="utf-8",
)


print()
print("=" * 55)
print("✅ HTMLの生成が完了しました")
print(f"📄 出力先: {HTML_FILE}")
print("=" * 55)
