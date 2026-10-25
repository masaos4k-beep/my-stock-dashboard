from pathlib import Path

import pandas as pd
import yfinance as yf
import plotly.graph_objects as go


# =========================================================
# 1. 出力先設定
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "ai_value_chain_global_map.html"


# =========================================================
# 2. AIバリューチェーン構造
# =========================================================

data_structure = {
    "Category": (
        ["電力"] * 3
        + ["半導体"] * 11
        + ["データセンター"] * 3
        + ["クラウド"] * 4
        + ["セキュリティ"] * 3
        + ["分析"] * 3
        + ["サービス"] * 3
    ),

    "Symbol": [
        # 電力
        "CEG", "GEV", "VST",

        # 半導体
        "NVDA", "AMD", "AVGO", "TSM",
        "6857.T", "8035.T", "ASML", "ARM",
        "MU", "000660.KS", "KXIAY",

        # データセンター
        "EQIX", "DLR", "SMCI",

        # クラウド
        "MSFT", "AMZN", "GOOGL", "META",

        # セキュリティ
        "PANW", "CRWD", "ZS",

        # 分析
        "PLTR", "SNOW", "DDOG",

        # サービス
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
        "Palo Alto", "CrowdStrike", "Zscaler",
        "Palantir", "Snowflake", "Datadog",
        "ServiceNow", "Adobe", "Salesforce",
    ],

    "Display_Name": [
        "CEG", "GEV", "VST",
        "NVDA", "AMD", "AVGO", "TSMC",
        "アドバンテスト", "東京エレクトロン",
        "ASML", "ARM", "Micron",
        "SKハイニックス", "キオクシア",
        "EQIX", "DLR", "SMCI",
        "MSFT", "AMZN", "GOOGL", "META",
        "PANW", "CRWD", "ZS",
        "PLTR", "SNOW", "DDOG",
        "NOW", "ADBE", "CRM",
    ],

    "Country": [
        "USA", "USA", "USA",

        "USA", "USA", "USA", "Taiwan",
        "Japan", "Japan", "Netherlands", "UK",
        "USA", "South Korea", "Japan",

        "USA", "USA", "USA",

        "USA", "USA", "USA", "USA",

        "USA", "USA", "USA",

        "USA", "USA", "USA",

        "USA", "USA", "USA",
    ],
}

df = pd.DataFrame(data_structure)

print(f"対象銘柄数: {len(df)}")


# =========================================================
# 3. 地図上の配置基準
# =========================================================

country_anchors = {
    "USA": {"lat": 54.0, "lon": -128.0},
    "Japan": {"lat": 36.0, "lon": 138.0},
    "Taiwan": {"lat": 23.5, "lon": 121.0},
    "Netherlands": {"lat": 52.3, "lon": 9.0},
    "UK": {"lat": 54.0, "lon": -6.0},
    "South Korea": {"lat": 36.0, "lon": 127.8},
}


# =========================================================
# 4. 騰落率計算関数
# =========================================================

def calc_period_change(series):
    clean_series = series.dropna()

    if len(clean_series) >= 2:
        start_val = float(clean_series.iloc[0])
        end_val = float(clean_series.iloc[-1])

        if start_val > 0:
            pct = (end_val - start_val) / start_val * 100.0
            return pct, f"{pct:+.2f}%"

    return 0.0, "+0.00%"


# =========================================================
# 5. 為替レート取得
# =========================================================

print("為替レートを取得しています...")

try:
    jpy_data = yf.Ticker("USDJPY=X").history(
        period="5d",
        auto_adjust=False,
    )["Close"].dropna()

    krw_data = yf.Ticker("USDKRW=X").history(
        period="5d",
        auto_adjust=False,
    )["Close"].dropna()

    fx_jpy = float(jpy_data.iloc[-1]) if not jpy_data.empty else 150.0
    fx_krw = float(krw_data.iloc[-1]) if not krw_data.empty else 1350.0

except Exception as e:
    print(f"為替取得エラー: {e}")
    fx_jpy = 150.0
    fx_krw = 1350.0


# =========================================================
# 6. 株価・時価総額取得
# =========================================================

print("株価データを取得しています...")


market_caps = []

val_1d, val_1w, val_1m, val_ytd = [], [], [], []
lbl_1d, lbl_1w, lbl_1m, lbl_ytd = [], [], [], []


for _, row in df.iterrows():

    name = row["ShortName"]
    symbol = row["Symbol"]

    print(f"取得中: {name} ({symbol})")

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

        # 時価総額を億ドルに換算
        if raw_cap > 0:

            if currency == "JPY":
                usd_cap = raw_cap / fx_jpy / 10**8

            elif currency == "KRW":
                usd_cap = raw_cap / fx_krw / 10**8

            else:
                usd_cap = raw_cap / 10**8

        # 1日騰落率
        prev_close = (
            info.get("previousClose")
            or info.get("regularMarketPreviousClose")
        )

        current_price = (
            info.get("regularMarketPrice")
            or info.get("currentPrice")
        )

        if prev_close and current_price and prev_close > 0:

            v1d = (current_price - prev_close) / prev_close * 100.0
            l1d = f"{v1d:+.2f}%"

        else:

            h1 = tk.history(
                period="7d",
                interval="1d",
                auto_adjust=False,
            )["Close"].dropna()

            if len(h1) >= 2:
                v1d, l1d = calc_period_change(h1.tail(2))

        # 1週間騰落率
        hw = tk.history(
            period="1mo",
            interval="1d",
            auto_adjust=False,
        )["Close"].dropna()

        if len(hw) >= 2:
            v1w, l1w = calc_period_change(hw.tail(min(len(hw), 6)))

        # 1ヶ月騰落率
        hm = tk.history(
            period="1mo",
            interval="1d",
            auto_adjust=False,
        )["Close"].dropna()

        v1m, l1m = calc_period_change(hm)

        # 年初来騰落率
        hy = tk.history(
            period="ytd",
            interval="1d",
            auto_adjust=False,
        )["Close"].dropna()

        vytd, lytd = calc_period_change(hy)

    except Exception as e:
        print(f"  取得エラー: {symbol}: {e}")

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
# 7. 騰落率の色設定
# =========================================================

custom_colorscale = [
    [0.00, "#a30000"],
    [0.35, "#d62728"],
    [0.47, "#331515"],
    [0.50, "#222222"],
    [0.53, "#153315"],
    [0.65, "#2ca02c"],
    [1.00, "#00a300"],
]


def get_auto_scale_range(values_list):

    valid_values = [
        float(v)
        for v in values_list
        if pd.notna(v)
    ]

    if not valid_values:
        return [-5.0, 5.0]

    max_abs = max(abs(max(valid_values)), abs(min(valid_values)))
    limit = max(max_abs, 5.0)

    return [-limit, limit]


range_1d = get_auto_scale_range(df["V_1D"].tolist())
range_1w = get_auto_scale_range(df["V_1W"].tolist())
range_1m = get_auto_scale_range(df["V_1M"].tolist())
range_ytd = get_auto_scale_range(df["V_YTD"].tolist())


# =========================================================
# 8. 地図上の企業・カテゴリー配置
# =========================================================

def create_map_trace_data(v_col, l_col):

    lats, lons = [], []
    names, hovers, values = [], [], []
    text_positions = []

    cat_lats, cat_lons, cat_texts, cat_text_positions, cat_text_sizes = [], [], [], [], []

    # ---------------------------------------------
    # 米国
    # ---------------------------------------------

    usa_df = df[df["Country"] == "USA"]

    if not usa_df.empty:

        categories = list(usa_df["Category"].unique())

        row_step = 12.5
        col_step = 11.0
        label_offset = 27.0

        anchor = country_anchors["USA"]

        for c_idx, cat in enumerate(categories):

            base_row_lat = anchor["lat"] - c_idx * row_step
            cat_text_lon = anchor["lon"] - 17.0

            cat_lats.append(base_row_lat)
            cat_lons.append(cat_text_lon)
            cat_texts.append(f"<b>{cat}</b>")
            # 米国のカテゴリー名は右寄せにして、画面左端で切れないようにする
            cat_text_positions.append("middle left")
            cat_text_sizes.append(10)

            cat_items = usa_df[usa_df["Category"] == cat]

            for elem_idx, (_, item) in enumerate(cat_items.iterrows()):

                circle_lat = base_row_lat
                circle_lon = (
                    anchor["lon"]
                    + label_offset
                    + elem_idx * col_step
                )

                lats.append(circle_lat)
                lons.append(circle_lon)
                names.append(item["Display_Name"])
                values.append(item[v_col])
                text_positions.append("top center")

                hovers.append(
                    f"<b>{item['ShortName']}</b> ({item['Symbol']})<br>"
                    f"カテゴリー: {item['Category']}<br>"
                    f"国: {item['Country']}<br>"
                    f"時価総額: {item['MarketCap']:,.0f}億ドル<br>"
                    f"騰落率: <b>{item[l_col]}</b>"
                )

    # ---------------------------------------------
    # 欧州
    # ---------------------------------------------

    cat_lats.append(64.0)
    cat_lons.append(3.0)
    cat_texts.append("<b>半導体</b>")
    cat_text_positions.append("middle left")
    cat_text_sizes.append(12)

    for country in ["UK", "Netherlands"]:

        country_df = df[df["Country"] == country]
        anchor = country_anchors[country]

        for _, item in country_df.iterrows():

            lats.append(anchor["lat"])
            lons.append(anchor["lon"])
            names.append(item["Display_Name"])
            values.append(item[v_col])
            text_positions.append("top center")

            hovers.append(
                f"<b>{item['ShortName']}</b> ({item['Symbol']})<br>"
                f"カテゴリー: {item['Category']}<br>"
                f"国: {item['Country']}<br>"
                f"時価総額: {item['MarketCap']:,.0f}億ドル<br>"
                f"騰落率: <b>{item[l_col]}</b>"
            )

    # ---------------------------------------------
    # アジア
    # ---------------------------------------------

    cat_lats.append(48.0)
    cat_lons.append(138.0)
    cat_texts.append("<b>半導体</b>")
    cat_text_positions.append("middle left")
    cat_text_sizes.append(12)

    asia_countries = ["Taiwan", "Japan", "South Korea"]
    jp_elem_idx = 0

    for country in asia_countries:

        country_df = df[df["Country"] == country]
        anchor = country_anchors[country]

        for _, item in country_df.iterrows():

            if country == "Japan":

                if jp_elem_idx == 0:
                    lat_offset = 2.0
                    text_position = "top center"

                elif jp_elem_idx == 1:
                    lat_offset = -2.0
                    text_position = "bottom center"

                else:
                    lat_offset = 2.0
                    text_position = "top center"

                circle_lat = anchor["lat"] + lat_offset
                circle_lon = anchor["lon"] + jp_elem_idx * 9.0

                jp_elem_idx += 1

            else:

                circle_lat = anchor["lat"]
                circle_lon = anchor["lon"]
                text_position = "top center"

            lats.append(circle_lat)
            lons.append(circle_lon)
            names.append(item["Display_Name"])
            values.append(item[v_col])
            text_positions.append(text_position)

            hovers.append(
                f"<b>{item['ShortName']}</b> ({item['Symbol']})<br>"
                f"カテゴリー: {item['Category']}<br>"
                f"国: {item['Country']}<br>"
                f"時価総額: {item['MarketCap']:,.0f}億ドル<br>"
                f"騰落率: <b>{item[l_col]}</b>"
            )

    return (
        lats,
        lons,
        names,
        hovers,
        values,
        text_positions,
        cat_lats,
        cat_lons,
        cat_texts,
        cat_text_positions,
        cat_text_sizes,
    )


# =========================================================
# 9. 期間別の地図トレース
# =========================================================

periods = [
    ("1日", "V_1D", "L_1D", range_1d, "1日騰落率 (%)"),
    ("1週間", "V_1W", "L_1W", range_1w, "1週間騰落率 (%)"),
    ("1ヶ月", "V_1M", "L_1M", range_1m, "1ヶ月騰落率 (%)"),
    ("年初来", "V_YTD", "L_YTD", range_ytd, "年初来騰落率 (%)"),
]

fig = go.Figure()

for idx, (_, v_col, l_col, p_range, colorbar_title) in enumerate(periods):

    (
        lats,
        lons,
        names,
        hovers,
        values,
        text_positions,
        cat_lats,
        cat_lons,
        cat_texts,
        cat_text_positions,
        cat_text_sizes,
    ) = create_map_trace_data(v_col, l_col)

    is_visible = idx == 0

    # 企業マーカー
    fig.add_trace(
        go.Scattergeo(
            lat=lats,
            lon=lons,

            mode="markers+text",

            text=names,
            textposition=text_positions,

            textfont=dict(
                size=9,
                color="#f0f5f3",
            ),

            showlegend=False,

            marker=dict(
                size=13,
                color=values,
                colorscale=custom_colorscale,
                cmin=p_range[0],
                cmax=p_range[1],
                cmid=0,
                opacity=0.95,

                line=dict(
                    width=1,
                    color="#d5e0e3",
                ),

                colorbar=dict(
                    title=dict(
                        text=colorbar_title,
                        font=dict(
                            size=12,
                            color="#f0f5f3",
                        ),
                    ),

                    tickfont=dict(
                        size=11,
                        color="#c1d0d4",
                    ),

                    thickness=15,
                    len=0.72,
                    x=1.01,
                ),
            ),

            hovertext=hovers,
            hovertemplate="%{hovertext}<extra></extra>",

            visible=is_visible,
        )
    )

    # カテゴリーラベル
    fig.add_trace(
        go.Scattergeo(
            lat=cat_lats,
            lon=cat_lons,

            mode="text",

            text=cat_texts,
            textposition=cat_text_positions,

            textfont=dict(
                size=cat_text_sizes,
                color="#31c487",
            ),

            hoverinfo="none",
            showlegend=False,

            visible=is_visible,
        )
    )


# =========================================================
# 10. レイアウト
# =========================================================

fig.update_layout(

    # HTML側にタイトルを置くため、Plotly側は非表示
    title=None,

    autosize=True,

    template="plotly_dark",

    paper_bgcolor="#080b0d",
    plot_bgcolor="#080b0d",

    showlegend=False,

    geo=dict(
        showframe=False,

        showcoastlines=True,
        coastlinecolor="#52636b",

        projection_type="equirectangular",
        scope="world",

        showland=True,
        landcolor="#182328",

        showocean=True,
        oceancolor="#080d12",

        showlakes=True,
        lakecolor="#080d12",

        showcountries=True,
        countrycolor="#34444b",
    ),

    margin=dict(
        t=8,
        l=8,
        r=90,
        b=8,
    ),
)


# =========================================================
# 11. HTML用のPlotlyグラフを生成
# =========================================================

plot_html = fig.to_html(
    include_plotlyjs="cdn",
    full_html=False,

    config={
        "responsive": True,
        "displaylogo": False,
    },

    div_id="global-map-chart",

    default_height="100%",
    default_width="100%",
)


# =========================================================
# 12. HTML全体
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

<title>AIバリューチェーン・グローバルマップ</title>

<style>

* {
    box-sizing: border-box;
}

html,
body {
    width: 100%;
    height: 100%;

    margin: 0;
    padding: 0;

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
    height: 70px;

    display: flex;
    align-items: center;
    justify-content: space-between;

    gap: 16px;
    padding: 10px 20px;

    background: #0b1012;
    border-bottom: 1px solid #29363a;
}

.page-title {
    font-size: 20px;
    font-weight: 700;
    white-space: nowrap;
}

.period-buttons {
    display: flex;
    align-items: center;
    gap: 5px;

    padding: 4px;

    background: #151e22;
    border: 1px solid #29363a;
    border-radius: 9px;
}

.period-btn {
    min-width: 78px;

    padding: 10px 14px;

    border: 1px solid transparent;
    border-radius: 6px;

    background: transparent;
    color: #a0b0b2;

    font-size: 14px;
    font-weight: 700;

    cursor: pointer;
    transition:
        background 0.15s ease,
        color 0.15s ease;
}

.period-btn:hover {
    background: #26343a;
    color: #ffffff;
}

.period-btn.active {
    background: #289dff;
    color: #ffffff;
    border-color: #289dff;
}

.map-container {
    width: 100%;
    height: calc(100vh - 70px);

    margin: 0;
    padding: 0;

    overflow: hidden;
}

#global-map-chart {
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
        min-height: 108px;

        padding: 10px;

        flex-direction: column;
        align-items: stretch;

        gap: 8px;
    }

    .page-title {
        font-size: 16px;
        white-space: normal;
    }

    .period-buttons {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));

        width: 100%;
    }

    .period-btn {
        min-width: 0;
        padding: 9px 4px;
        font-size: 12px;
    }

    .map-container {
        height: calc(100vh - 108px);
    }
}

</style>

</head>

<body>

<header class="topbar">

    <div class="page-title">
        AIバリューチェーン・グローバルマップ
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

<main class="map-container">

__PLOT_HTML__

</main>

<script>

const periodSettings = [
    {
        cmin: __RANGE_1D_MIN__,
        cmax: __RANGE_1D_MAX__
    },
    {
        cmin: __RANGE_1W_MIN__,
        cmax: __RANGE_1W_MAX__
    },
    {
        cmin: __RANGE_1M_MIN__,
        cmax: __RANGE_1M_MAX__
    },
    {
        cmin: __RANGE_YTD_MIN__,
        cmax: __RANGE_YTD_MAX__
    }
];


function changePeriod(index) {

    const visible = [
        false, false,
        false, false,
        false, false,
        false, false
    ];

    visible[index * 2] = true;
    visible[index * 2 + 1] = true;

    const settings = periodSettings[index];

    Plotly.restyle(
        "global-map-chart",
        {
            visible: visible
        }
    );

    Plotly.restyle(
        "global-map-chart",
        {
            "marker.cmin": settings.cmin,
            "marker.cmax": settings.cmax
        },
        [0, 2, 4, 6]
    ).then(() => {

        // 表示対象のトレースに対応するカラーバーを更新
        Plotly.relayout(
            "global-map-chart",
            {
                "title": ""
            }
        );

    });

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
        "global-map-chart"
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
# 13. HTMLへデータを埋め込んで保存
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


OUTPUT_FILE.write_text(
    html_content,
    encoding="utf-8",
)

print()
print("=" * 55)
print("HTMLの生成が完了しました")
print(f"出力先: {OUTPUT_FILE}")
print("=" * 55)
