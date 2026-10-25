from pathlib import Path
import datetime
import json

import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ==================================================
# 1. ファイル設定
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CSV_FILE = BASE_DIR / "data" / "forward_pe_3indices_2026.csv"

OUTPUT_FILE = BASE_DIR / "3indices_eps_price_chart.html"


# ==================================================
# 2. CSV読み込み
# ==================================================

print(f"CSVを読み込みます: {CSV_FILE}")

if not CSV_FILE.exists():
    raise FileNotFoundError(
        f"CSVファイルが見つかりません: {CSV_FILE}"
    )

df_pe = pd.read_csv(CSV_FILE)

required_columns = [
    "Date",
    "SP500_Forward_PE",
    "NASDAQ100_Forward_PE",
    "SOX_Forward_PE",
]

missing_columns = [
    col for col in required_columns
    if col not in df_pe.columns
]

if missing_columns:
    raise ValueError(
        f"CSVに必要な列がありません: {missing_columns}"
    )

df_pe["Date"] = pd.to_datetime(
    df_pe["Date"],
    errors="coerce"
)

for col in required_columns[1:]:
    df_pe[col] = pd.to_numeric(
        df_pe[col],
        errors="coerce"
    )

df_pe = (
    df_pe.dropna(subset=["Date"])
    .sort_values("Date")
    .set_index("Date")
)

if df_pe.empty:
    raise ValueError("CSVに有効なデータがありません。")


# ==================================================
# 3. 日付設定
# ==================================================

current_year = datetime.datetime.now().year

start_date = f"{current_year}-01-01"

# yfinanceのendは原則として指定日を含まないため、
# 翌日を指定して本日までのデータ取得を試みる
tomorrow = datetime.date.today() + datetime.timedelta(days=1)
end_date = tomorrow.strftime("%Y-%m-%d")


# ==================================================
# 4. 指数設定
# ==================================================

index_info = {
    "SP500": {
        "name": "S&P 500",
        "ticker": "^GSPC",
        "pe_col": "SP500_Forward_PE",
        "price_origin": 5000,
        "eps_origin": 200,
        "price_color": "#FF9800",
        "eps_color": "#B0B0B0",
    },

    "NASDAQ100": {
        "name": "NASDAQ 100",
        "ticker": "^NDX",
        "pe_col": "NASDAQ100_Forward_PE",
        "price_origin": 15000,
        "eps_origin": 500,
        "price_color": "#FF9800",
        "eps_color": "#B0B0B0",
    },

    "SOX": {
        "name": "SOX（半導体）",
        "ticker": "^SOX",
        "pe_col": "SOX_Forward_PE",
        "price_origin": 3000,
        "eps_origin": 100,
        "price_color": "#FF9800",
        "eps_color": "#B0B0B0",
    },
}


# ==================================================
# 5. 株価と予想EPSを計算
# ==================================================

processed_data = {}

for key, info in index_info.items():

    print(
        f"Yahoo Financeから {info['name']} "
        f"({info['ticker']}) の株価を取得中..."
    )

    try:
        ticker_obj = yf.Ticker(info["ticker"])

        df_price = ticker_obj.history(
            start=start_date,
            end=end_date
        )

        if df_price.empty:
            print(
                f"警告: {info['name']} の株価データがありません。"
            )
            continue

        # タイムゾーンを除去
        df_price.index = (
            pd.to_datetime(df_price.index)
            .tz_localize(None)
        )

        df_price = df_price[["Close"]].rename(
            columns={"Close": "Price"}
        )

        # 株価データと予想PERデータを結合
        df_comb = df_price.join(
            df_pe[[info["pe_col"]]],
            how="left"
        )

        # 予想PERの欠損を補間
        df_comb["Forward_PE"] = (
            df_comb[info["pe_col"]]
            .ffill()
            .bfill()
        )

        # EPS = 株価 ÷ 予想PER
        df_comb["Forward_EPS"] = (
            df_comb["Price"] / df_comb["Forward_PE"]
        )

        df_comb = df_comb.dropna(
            subset=["Price", "Forward_EPS"]
        )

        if df_comb.empty:
            print(
                f"警告: {info['name']} のEPSを計算できません。"
            )
            continue

        processed_data[key] = df_comb

        print(
            f"{info['name']}: "
            f"{len(df_comb)}件のデータを取得しました。"
        )

    except Exception as e:
        print(
            f"警告: {info['name']} のデータ取得に失敗しました: {e}"
        )


if not processed_data:
    raise RuntimeError(
        "株価データを取得できませんでした。"
    )


# ==================================================
# 6. チャート作成
# ==================================================

fig = make_subplots(
    specs=[[{"secondary_y": True}]]
)

available_keys = list(processed_data.keys())

# 初期表示する指数
initial_key = (
    "SP500" if "SP500" in processed_data
    else available_keys[0]
)

trace_map = {}

for key in available_keys:

    info = index_info[key]
    df_item = processed_data[key]

    visible = (key == initial_key)

    # 株価
    fig.add_trace(
        go.Scatter(
            x=df_item.index,
            y=df_item["Price"],
            mode="lines",
            name=f"{info['name']} 株価",
            line=dict(
                color=info["price_color"],
                width=2.5,
            ),
            hovertemplate=(
                "%{x|%Y/%m/%d}<br>"
                "<b>株価: $%{y:,.2f}</b>"
                "<extra></extra>"
            ),
            visible=visible,
        ),
        secondary_y=False,
    )

    price_trace_index = len(fig.data) - 1

    # 予想EPS
    fig.add_trace(
        go.Scatter(
            x=df_item.index,
            y=df_item["Forward_EPS"],
            mode="lines+markers",
            name=f"{info['name']} 予想EPS",
            line=dict(
                color=info["eps_color"],
                width=2.0,
            ),
            marker=dict(
                size=4,
                color=info["eps_color"],
            ),
            hovertemplate=(
                "%{x|%Y/%m/%d}<br>"
                "<b>予想EPS: $%{y:.2f}</b>"
                "<extra></extra>"
            ),
            visible=visible,
        ),
        secondary_y=True,
    )

    eps_trace_index = len(fig.data) - 1

    trace_map[key] = {
        "price": price_trace_index,
        "eps": eps_trace_index,
    }


# ==================================================
# 7. 各指数の軸設定を作成
# ==================================================

chart_configs = {}

for key in available_keys:

    info = index_info[key]
    df_item = processed_data[key]

    price_max = round(
        df_item["Price"].max() * 1.12,
        -2
    )

    eps_max = round(
        df_item["Forward_EPS"].max() * 1.12,
        -1
    )

    # 最小値を最大値より小さく保つ
    if price_max <= info["price_origin"]:
        price_max = info["price_origin"] + 100

    if eps_max <= info["eps_origin"]:
        eps_max = info["eps_origin"] + 10

    chart_configs[key] = {
        "name": info["name"],
        "price_origin": info["price_origin"],
        "price_max": price_max,
        "eps_origin": info["eps_origin"],
        "eps_max": eps_max,
        "price_trace": trace_map[key]["price"],
        "eps_trace": trace_map[key]["eps"],
    }


# ==================================================
# 8. 初期レイアウト
# ==================================================

init = chart_configs[initial_key]

fig.update_layout(
    title=dict(
        text=(
            f"<b>{init['name']} 株価 & 1年予想EPS "
            f"年初来推移（{current_year}年）</b>"
        ),
        x=0.02,
        xanchor="left",
        y=0.97,
        yanchor="top",
        font=dict(
            size=18,
            color="#FFFFFF",
        ),
    ),

    template="plotly_dark",

    paper_bgcolor="#111111",
    plot_bgcolor="#1A1A1A",

    # レスポンシブ対応
    autosize=True,
    height=520,

    xaxis=dict(
        range=[
            f"{current_year}-01-01",
            f"{current_year}-12-31",
        ],
        tickformat="%Y/%m",
        hoverformat="%Y/%m/%d",
        dtick="M1",
        gridcolor="#333333",
        linecolor="#666666",
    ),

    hovermode="x unified",

    hoverlabel=dict(
        bgcolor="#1E1E1E",
        font_size=13,
        font_color="#FFFFFF",
    ),

    # 凡例をチャートの上部左側に配置
    legend=dict(
        orientation="h",
        yanchor="top",
        y=1.0,
        xanchor="left",
        x=0.02,
        font=dict(
            size=11,
            color="#FFFFFF",
        ),
        bgcolor="rgba(17,17,17,0.75)",
    ),

    # タイトルと凡例のための上部余白
    margin=dict(
        l=65,
        r=65,
        t=105,
        b=55,
    ),

    showlegend=True,

    transition=dict(duration=0),
)

# 左軸：株価
fig.update_yaxes(
    title_text="株価 ($)",
    range=[
        init["price_origin"],
        init["price_max"],
    ],
    tickprefix="$",
    gridcolor="#333333",
    linecolor="#666666",
    secondary_y=False,
)

# 右軸：予想EPS
fig.update_yaxes(
    title_text="1年予想 EPS ($)",
    range=[
        init["eps_origin"],
        init["eps_max"],
    ],
    tickprefix="$",
    showgrid=False,
    linecolor="#666666",
    secondary_y=True,
)


# ==================================================
# 9. HTML出力
# ==================================================

fig.write_html(
    str(OUTPUT_FILE),
    include_plotlyjs="cdn",
    full_html=True,
    config={
        "responsive": True,
        "displaylogo": False,
    },
)


# ==================================================
# 10. カスタムボタンをHTMLに追加
# ==================================================

html = OUTPUT_FILE.read_text(encoding="utf-8")

js_configs = {}

for key in available_keys:
    js_configs[key] = chart_configs[key]

js_configs_json = json.dumps(
    js_configs,
    ensure_ascii=False,
)

# トレース数と表示設定をJavaScriptへ渡す
trace_count = len(fig.data)

button_labels = {
    "SP500": "S&P 500",
    "NASDAQ100": "NASDAQ 100",
    "SOX": "SOX（半導体）",
}

button_html = """
<style>
.index-button-area {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    padding: 10px 20px 4px;
    box-sizing: border-box;
    background: #111111;
}

.index-button {
    background-color: #292929;
    color: #DDDDDD;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: bold;
    cursor: pointer;
}

.index-button.active {
    background-color: #1677FF;
    color: #FFFFFF;
    border-color: #1677FF;
}

.index-button:hover {
    border-color: #66AAFF;
}

@media (max-width: 600px) {
    .index-button-area {
        justify-content: center;
        gap: 4px;
        padding: 8px;
    }

    .index-button {
        padding: 8px 12px;
        font-size: 12px;
    }
}
</style>

<div class="index-button-area">
    __BUTTONS__
</div>

<script>
(function () {

    const configs = __CONFIGS__;
    const initialKey = "__INITIAL_KEY__";

    function initializeChart() {

        const plot = document.querySelector(".plotly-graph-div");

        if (!plot || !window.Plotly) {
            setTimeout(initializeChart, 100);
            return;
        }

        const buttonArea = document.querySelector(
            ".index-button-area"
        );

        // ボタン領域をチャートの直前に配置
        if (buttonArea && plot.parentElement) {
            plot.parentElement.insertBefore(
                buttonArea,
                plot
            );
        }

        function selectIndex(key) {

            const config = configs[key];

            if (!config) {
                return;
            }

            const visibility = Array(
                __TRACE_COUNT__
            ).fill(false);

            visibility[config.price_trace] = true;
            visibility[config.eps_trace] = true;

            // 株価とEPSを切り替える
            Plotly.restyle(
                plot,
                {visible: visibility}
            );

            // タイトルと左右のY軸を切り替える
            Plotly.relayout(plot, {
                "title.text":
                    "<b>" + config.name
                    + " 株価 & 1年予想EPS "
                    + "年初来推移（__CURRENT_YEAR__年）</b>",

                "yaxis.range": [
                    config.price_origin,
                    config.price_max
                ],

                "yaxis2.range": [
                    config.eps_origin,
                    config.eps_max
                ]
            });

            // 選択中のボタンを青色にする
            document.querySelectorAll(
                ".index-button"
            ).forEach(function (button) {

                button.classList.toggle(
                    "active",
                    button.dataset.index === key
                );
            });
        }

        document.querySelectorAll(
            ".index-button"
        ).forEach(function (button) {

            button.addEventListener(
                "click",
                function () {
                    selectIndex(button.dataset.index);
                }
            );
        });

        // 初期表示を同期
        selectIndex(initialKey);
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initializeChart
        );
    } else {
        initializeChart();
    }

})();
</script>
"""

button_parts = []

for key in available_keys:
    label = button_labels[key]

    active_class = (
        " active" if key == initial_key else ""
    )

    button_parts.append(
        f'<button class="index-button{active_class}" '
        f'data-index="{key}">{label}</button>'
    )

button_html = (
    button_html
    .replace(
        "__BUTTONS__",
        "\n".join(button_parts),
    )
    .replace(
        "__CONFIGS__",
        js_configs_json,
    )
    .replace(
        "__INITIAL_KEY__",
        initial_key,
    )
    .replace(
        "__TRACE_COUNT__",
        str(trace_count),
    )
    .replace(
        "__CURRENT_YEAR__",
        str(current_year),
    )
)

html = html.replace(
    "<body>",
    "<body>\n" + button_html,
    1,
)

OUTPUT_FILE.write_text(
    html,
    encoding="utf-8",
)

print(f"HTMLチャートを出力しました: {OUTPUT_FILE}")
