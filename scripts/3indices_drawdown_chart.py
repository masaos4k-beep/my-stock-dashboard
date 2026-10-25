#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S&P 500・NASDAQ 100・SOX の年初来ドローダウン比較チャートを作成する。
出力ファイル: 3indices_drawdown_chart.html

必要ライブラリ:
    pip install yfinance pandas plotly
"""

from pathlib import Path
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import yfinance as yf


OUTPUT_FILE = Path("3indices_drawdown_chart.html")
YEAR = date.today().year

# Yahoo Finance の指数シンボル
INDICES = [
    {
        "label": "S&P 500",
        "ticker": "^GSPC",
        "title": "S&P 500",
    },
    {
        "label": "NASDAQ 100",
        "ticker": "^NDX",
        "title": "NASDAQ 100",
    },
    {
        "label": "SOX (半導体株指数)",
        "ticker": "^SOX",
        "title": "SOX (半導体株指数)",
    },
]
USDJPY_TICKER = "JPY=X"

BACKGROUND = "#111111"
ORANGE = "#FF9900"
CYAN = "#00E5FF"


def download_close(ticker: str, start: str, end: str) -> pd.Series:
    """Yahoo Finance から日次終値を取得する。"""
    data = yf.download(
        ticker,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if data.empty:
        raise RuntimeError(
            f"{ticker} のデータを取得できませんでした。"
            "ティッカーや通信環境を確認してください。"
        )

    close = data["Close"]
    # yfinance のバージョンによって Close が DataFrame になる場合に対応
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = pd.to_numeric(close, errors="coerce").dropna()
    close.name = ticker
    return close


def drawdown(series: pd.Series) -> pd.Series:
    """年初来の最高値を基準にドローダウン率を計算する。"""
    running_peak = series.cummax()
    return (series / running_peak - 1.0) * 100.0


def main() -> None:
    start = f"{YEAR}-01-01"
    # yfinance の end は排他的なので、翌年1月1日を指定
    end = f"{YEAR + 1}-01-01"

    print(f"{YEAR}年の指数データを取得しています...")
    fx = download_close(USDJPY_TICKER, start, end).rename("USDJPY")

    fig = go.Figure()
    visibility_groups = []

    for index_number, item in enumerate(INDICES):
        close_usd = download_close(item["ticker"], start, end)
        # 為替データのない日を補完し、指数データの日付に揃える
        fx_aligned = fx.reindex(close_usd.index).ffill().bfill()
        close_jpy = close_usd * fx_aligned

        dd_jpy = drawdown(close_jpy)
        dd_usd = drawdown(close_usd)

        max_jpy = float(dd_jpy.min())
        max_usd = float(dd_usd.min())

        visible = index_number == 0
        first_trace = len(fig.data)

        fig.add_trace(
            go.Scatter(
                x=dd_jpy.index,
                y=dd_jpy,
                mode="lines",
                name=f"{item['label']}（円建て）[最大: {max_jpy:.2f}%]",
                line=dict(color=ORANGE, width=2),
                fill="tozeroy",
                fillcolor="rgba(255, 153, 0, 0.25)",
                visible=visible,
                hovertemplate="%{x|%Y/%m/%d}<br>円建て DD: %{y:.2f}%<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=dd_usd.index,
                y=dd_usd,
                mode="lines",
                name=f"{item['label']}（ドル建て）[最大: {max_usd:.2f}%]",
                line=dict(color=CYAN, width=2.5, dash="dot"),
                visible=visible,
                hovertemplate="%{x|%Y/%m/%d}<br>ドル建て DD: %{y:.2f}%<extra></extra>",
            )
        )

        group = [False] * (len(INDICES) * 2)
        group[first_trace] = True
        group[first_trace + 1] = True
        visibility_groups.append(group)

    buttons = []
    for item, visible_group in zip(INDICES, visibility_groups):
        buttons.append(
            dict(
                label=item["label"],
                method="update",
                args=[
                    {"visible": visible_group},
                    {"title.text": f"<b>{item['title']} 年初来ドローダウン推移 ({YEAR}年)</b>"},
                ],
            )
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BACKGROUND,
        plot_bgcolor=BACKGROUND,
        font=dict(color="#FFFFFF", family="Arial, sans-serif"),
        title=dict(
            text=f"<b>{INDICES[0]['title']} 年初来ドローダウン推移 ({YEAR}年)</b>",
            x=0.02,
            xanchor="left",
            y=0.98,
            yanchor="top",
        ),
        # ボタンはグラフ下部に配置。下余白を確保し、タイトルとは別領域にする。
        margin=dict(l=65, r=35, t=90, b=115),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis=dict(
            range=[start, end],
            type="date",
            showgrid=True,
            gridcolor="#333333",
            dtick="M1",
            tickformat="%b",
        ),
        yaxis=dict(
            title=dict(text="ドローダウン (%)"),
            ticksuffix="%",
            showgrid=True,
            gridcolor="#333333",
            zerolinecolor="#FF5555",
            zerolinewidth=1.5,
        ),
        hovermode="x unified",
        autosize=True,
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                buttons=buttons,
                x=0.5,
                xanchor="center",
                y=-0.16,
                yanchor="top",
                bgcolor="#2A2A2A",
                bordercolor="#444444",
                borderwidth=1,
                font=dict(color="#FFFFFF", size=13),
                active=0,
                showactive=True,
            )
        ],
    )

    # ブラウザ幅に左右されずボタンが下部に表示されるよう、レスポンシブ設定を有効化。
    fig.write_html(
        OUTPUT_FILE,
        include_plotlyjs="cdn",
        full_html=True,
        config={"responsive": True, "displaylogo": False},
    )

    # Plotly の選択状態を明示的に着色。クリック時の選択色を安定させる。
    html = OUTPUT_FILE.read_text(encoding="utf-8")
    style = r"""
<style>
html, body { margin: 0; padding: 0; background: #111111; }
.plotly-graph-div { width: 100% !important; }
g.updatemenu-button rect {
    fill: #2A2A2A !important;
    stroke: #444444 !important;
}
g.updatemenu-button text { fill: #CCCCCC !important; }
g.updatemenu-button.selected rect {
    fill: #007ACC !important;
    stroke: #00AFFF !important;
}
g.updatemenu-button.selected text {
    fill: #FFFFFF !important;
    font-weight: bold !important;
}
</style>
"""
    script = r"""
<script>
(function () {
  function setupPlotlyButtons() {
    document.querySelectorAll(".plotly-graph-div").forEach(function (graph) {
      if (graph.dataset.bottomButtonColorReady === "1") return;
      const buttons = graph.querySelectorAll("g.updatemenu-button");
      if (!buttons.length) return;
      graph.dataset.bottomButtonColorReady = "1";

      function setSelected(button) {
        graph.querySelectorAll("g.updatemenu-button").forEach(function (item) {
          item.classList.toggle("selected", item === button);
        });
      }

      setSelected(buttons[0]);
      graph.addEventListener("click", function (event) {
        const button = event.target.closest("g.updatemenu-button");
        if (button && graph.contains(button)) {
          window.setTimeout(function () { setSelected(button); }, 80);
        }
      });
    });
  }

  const observer = new MutationObserver(setupPlotlyButtons);
  observer.observe(document.documentElement, {childList: true, subtree: true});
  document.addEventListener("DOMContentLoaded", setupPlotlyButtons);
  window.addEventListener("load", setupPlotlyButtons);
  window.setInterval(setupPlotlyButtons, 500);
})();
</script>
"""
    html = html.replace("</head>", style + "\n</head>", 1)
    html = html.replace("</body>", script + "\n</body>", 1)
    OUTPUT_FILE.write_text(html, encoding="utf-8")

    print(f"HTMLを作成しました: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
