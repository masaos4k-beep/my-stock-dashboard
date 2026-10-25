from pathlib import Path
import datetime
import json

import pandas as pd
import plotly.graph_objects as go


# ==================================================
# 1. ファイル設定
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

CSV_FILE = BASE_DIR / "data" / "forward_pe_3indices_2026.csv"

OUTPUT_FILE = BASE_DIR / "3indices_per_chart_chart.html"


# ==================================================
# 2. CSV読み込み
# ==================================================

if not CSV_FILE.exists():
    raise FileNotFoundError(
        f"CSVファイルが見つかりません: {CSV_FILE}"
    )

df = pd.read_csv(CSV_FILE)

required_columns = [
    "Date",
    "SP500_Forward_PE",
    "NASDAQ100_Forward_PE",
    "SOX_Forward_PE",
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"CSVに必要な列がありません: {missing_columns}"
    )

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

for col in required_columns[1:]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = (
    df.dropna(subset=["Date"])
      .sort_values("Date")
      .set_index("Date")
)

if df.empty:
    raise ValueError("CSVに有効なデータがありません。")

current_year = datetime.datetime.now().year

x_start = f"{current_year}-01-01"
x_end = f"{current_year}-12-31"


# ==================================================
# 3. 指数ごとのPER設定
# ==================================================

index_configs = {
    "SP500": {
        "name": "S&P 500",
        "column": "SP500_Forward_PE",
        "y_range": [15, 27],
        "line_color": "#FFB000",
        "marker_color": "#FFD700",
        "zones": [
            {
                "y0": 15,
                "y1": 18,
                "label": "割安感が強い",
                "detail": "18倍未満",
                "color": "rgba(0, 140, 255, 0.18)",
                "text_color": "#64C8FF",
            },
            {
                "y0": 18,
                "y1": 20,
                "label": "やや割安",
                "detail": "18～20倍",
                "color": "rgba(0, 180, 160, 0.16)",
                "text_color": "#5CE1D2",
            },
            {
                "y0": 20,
                "y1": 22,
                "label": "妥当な水準",
                "detail": "20～22倍",
                "color": "rgba(120, 120, 120, 0.18)",
                "text_color": "#FFFFFF",
            },
            {
                "y0": 22,
                "y1": 24,
                "label": "やや割高",
                "detail": "22～24倍",
                "color": "rgba(255, 170, 0, 0.16)",
                "text_color": "#FFC04D",
            },
            {
                "y0": 24,
                "y1": 27,
                "label": "割高感が強い",
                "detail": "24倍超",
                "color": "rgba(255, 60, 60, 0.18)",
                "text_color": "#FF6B6B",
            },
        ],
        "thresholds": [18, 20, 22, 24],
    },

    "NASDAQ100": {
        "name": "NASDAQ 100",
        "column": "NASDAQ100_Forward_PE",
        "y_range": [17, 32],
        "line_color": "#00CC96",
        "marker_color": "#98FB98",
        "zones": [
            {
                "y0": 17,
                "y1": 20,
                "label": "割安感が強い",
                "detail": "20倍未満",
                "color": "rgba(0, 140, 255, 0.18)",
                "text_color": "#64C8FF",
            },
            {
                "y0": 20,
                "y1": 23,
                "label": "やや割安",
                "detail": "20～23倍",
                "color": "rgba(0, 180, 160, 0.16)",
                "text_color": "#5CE1D2",
            },
            {
                "y0": 23,
                "y1": 26,
                "label": "妥当な水準",
                "detail": "23～26倍",
                "color": "rgba(120, 120, 120, 0.18)",
                "text_color": "#FFFFFF",
            },
            {
                "y0": 26,
                "y1": 29,
                "label": "やや割高",
                "detail": "26～29倍",
                "color": "rgba(255, 170, 0, 0.16)",
                "text_color": "#FFC04D",
            },
            {
                "y0": 29,
                "y1": 32,
                "label": "割高感が強い",
                "detail": "29倍超",
                "color": "rgba(255, 60, 60, 0.18)",
                "text_color": "#FF6B6B",
            },
        ],
        "thresholds": [20, 23, 26, 29],
    },

    "SOX": {
        "name": "SOX（半導体）",
        "column": "SOX_Forward_PE",
        "y_range": [15, 30],
        "line_color": "#3399FF",
        "marker_color": "#ADD8E6",
        "zones": [
            {
                "y0": 15,
                "y1": 18,
                "label": "割安感が強い",
                "detail": "18倍未満",
                "color": "rgba(0, 140, 255, 0.18)",
                "text_color": "#64C8FF",
            },
            {
                "y0": 18,
                "y1": 21,
                "label": "やや割安",
                "detail": "18～21倍",
                "color": "rgba(0, 180, 160, 0.16)",
                "text_color": "#5CE1D2",
            },
            {
                "y0": 21,
                "y1": 24,
                "label": "妥当な水準",
                "detail": "21～24倍",
                "color": "rgba(120, 120, 120, 0.18)",
                "text_color": "#FFFFFF",
            },
            {
                "y0": 24,
                "y1": 27,
                "label": "やや割高",
                "detail": "24～27倍",
                "color": "rgba(255, 170, 0, 0.16)",
                "text_color": "#FFC04D",
            },
            {
                "y0": 27,
                "y1": 30,
                "label": "割高感が強い",
                "detail": "27倍超",
                "color": "rgba(255, 60, 60, 0.18)",
                "text_color": "#FF6B6B",
            },
        ],
        "thresholds": [18, 21, 24, 27],
    },
}


# ==================================================
# 4. PERゾーンと注釈を生成
# ==================================================

def build_shapes_and_annotations(config):
    shapes = []
    annotations = []

    for zone in config["zones"]:

        y0 = zone["y0"]
        y1 = zone["y1"]

        # 背景ゾーン
        shapes.append({
            "type": "rect",
            "xref": "paper",
            "yref": "y",
            "x0": 0,
            "x1": 1,
            "y0": y0,
            "y1": y1,
            "fillcolor": zone["color"],
            "line": {"width": 0},
            "layer": "below",
        })

        # ゾーンの説明文
        annotations.append({
            "xref": "paper",
            "x": 0.012,
            "yref": "y",
            "y": y1 - (y1 - y0) * 0.32,
            "text": (
                f"{zone['label']}（{zone['detail']}）"
            ),
            "showarrow": False,
            "xanchor": "left",
            "yanchor": "middle",
            "font": {
                "color": zone["text_color"],
                "size": 12,
            },
        })

    # 水平基準線
    for value in config["thresholds"]:
        shapes.append({
            "type": "line",
            "xref": "paper",
            "yref": "y",
            "x0": 0,
            "x1": 1,
            "y0": value,
            "y1": value,
            "line": {
                "color": "rgba(200, 200, 200, 0.45)",
                "width": 1,
                "dash": "dash",
            },
        })

        # 右端のPER数値
        annotations.append({
            "xref": "paper",
            "x": 1.005,
            "yref": "y",
            "y": value,
            "text": str(value),
            "showarrow": False,
            "xanchor": "left",
            "font": {
                "color": "#CCCCCC",
                "size": 10,
            },
        })

    return shapes, annotations


# ==================================================
# 5. Plotlyチャートを生成
# ==================================================

fig = go.Figure()

for key, config in index_configs.items():

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[config["column"]],
            mode="lines+markers",
            name=config["name"],
            line={
                "color": config["line_color"],
                "width": 2,
            },
            marker={
                "color": config["marker_color"],
                "size": 5,
            },
            visible=(key == "SP500"),
            connectgaps=False,
            hovertemplate=(
                "%{x|%Y-%m-%d}<br>"
                + config["name"]
                + " 予想PER: %{y:.2f}倍"
                + "<extra></extra>"
            ),
        )
    )


# ==================================================
# 6. 初期レイアウト
# ==================================================

initial_config = index_configs["SP500"]

initial_shapes, initial_annotations = (
    build_shapes_and_annotations(initial_config)
)

fig.update_layout(
    title={
        "text": f"S&P 500 1年予想PER 推移（{current_year}年）",
        "x": 0.015,
        "xanchor": "left",
        "font": {
            "color": "#FFFFFF",
            "size": 20,
        },
    },

    template="plotly_dark",

    paper_bgcolor="#111111",
    plot_bgcolor="#1A1A1A",

    # チャート本体の高さ
    height=520,
    autosize=True,

    xaxis={
        "title": "",
        "range": [x_start, x_end],
        "tickformat": "%m月",
        "dtick": "M1",
        "showgrid": True,
        "gridcolor": "#333333",
        "color": "#DDDDDD",
        "automargin": True,
    },

    yaxis={
        "title": "予想PER（倍）",
        "range": initial_config["y_range"],
        "showgrid": True,
        "gridcolor": "#333333",
        "color": "#DDDDDD",
        "automargin": True,
    },

    shapes=initial_shapes,
    annotations=initial_annotations,

    margin={
        "l": 60,
        "r": 65,
        "t": 65,
        "b": 45,
    },

    showlegend=False,
)


# ==================================================
# 7. HTMLを書き出す
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
# 8. HTMLに指数選択ボタンを追加
# ==================================================

html = OUTPUT_FILE.read_text(encoding="utf-8")

# JavaScriptから参照する指数設定
js_configs = {}

for key, config in index_configs.items():
    shapes, annotations = build_shapes_and_annotations(config)

    js_configs[key] = {
        "name": config["name"],
        "y_range": config["y_range"],
        "shapes": shapes,
        "annotations": annotations,
    }

js_configs_json = json.dumps(
    js_configs,
    ensure_ascii=False,
)


custom_html = """
<style>
html, body {
    margin: 0;
    padding: 0;
    background: #111111;
    color: #FFFFFF;
    font-family: Arial, "Noto Sans JP", sans-serif;
}

.index-button-area {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    padding: 10px 20px;
    box-sizing: border-box;
    background: #111111;
}

.index-button {
    background: #292929;
    color: #DDDDDD;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: bold;
    cursor: pointer;
}

.index-button.active {
    background: #1677FF;
    color: #FFFFFF;
    border-color: #1677FF;
}

.index-button:hover {
    border-color: #66AAFF;
}

#chart-container {
    width: 100%;
}

@media (max-width: 600px) {
    .index-button-area {
        justify-content: center;
        padding: 8px;
        gap: 4px;
    }

    .index-button {
        padding: 8px 12px;
        font-size: 12px;
    }
}
</style>

<div class="index-button-area">
    <button class="index-button active" data-index="SP500">
        S&amp;P 500
    </button>
    <button class="index-button" data-index="NASDAQ100">
        NASDAQ 100
    </button>
    <button class="index-button" data-index="SOX">
        SOX（半導体）
    </button>
</div>

<script>
(function () {
    const configs = __INDEX_CONFIGS__;

    function initializeChart() {
        const plot = document.querySelector(".plotly-graph-div");

        if (!plot || !window.Plotly) {
            setTimeout(initializeChart, 100);
            return;
        }

        // ボタンをチャートの上に独立して配置
        const buttonArea = document.querySelector(".index-button-area");

        if (buttonArea && plot.parentElement) {
            plot.parentElement.insertBefore(buttonArea, plot);
        }

        // 画面幅に応じてチャートの高さを設定
        function resizeChart() {
            const width = window.innerWidth;

            let height;

            if (width < 600) {
                height = 430;
            } else if (width < 1000) {
                height = 470;
            } else {
                height = 520;
            }

            Plotly.relayout(plot, {
                height: height,
                autosize: true
            });
        }

        function selectIndex(key) {
            const config = configs[key];

            if (!config) {
                return;
            }

            const keys = ["SP500", "NASDAQ100", "SOX"];

            const visibility = keys.map(function (item) {
                return item === key;
            });

            // 表示する指数を切り替え
            Plotly.restyle(plot, {
                visible: visibility
            });

            // タイトル・PER軸・ゾーン・説明文をまとめて更新
            Plotly.relayout(plot, {
                "title.text":
                    config.name
                    + " 1年予想PER 推移（__CURRENT_YEAR__年）",

                "yaxis.range": config.y_range,

                "shapes": config.shapes,

                "annotations": config.annotations
            });

            // 選択中ボタンを青色にする
            document.querySelectorAll(".index-button").forEach(
                function (button) {
                    button.classList.toggle(
                        "active",
                        button.dataset.index === key
                    );
                }
            );
        }

        document.querySelectorAll(".index-button").forEach(
            function (button) {
                button.addEventListener("click", function () {
                    selectIndex(button.dataset.index);
                });
            }
        );

        resizeChart();

        window.addEventListener("resize", resizeChart);
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

custom_html = (
    custom_html
    .replace("__INDEX_CONFIGS__", js_configs_json)
    .replace("__CURRENT_YEAR__", str(current_year))
)

# ボタン用HTMLをbodyの先頭に挿入
html = html.replace(
    "<body>",
    "<body>\n" + custom_html,
    1,
)

OUTPUT_FILE.write_text(html, encoding="utf-8")

print(f"HTMLチャートを出力しました: {OUTPUT_FILE}")
