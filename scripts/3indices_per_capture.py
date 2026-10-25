from pathlib import Path
import asyncio
import re
import pandas as pd
from playwright.async_api import async_playwright

# ==========================================
# 設定
# ==========================================

START_DATE = "2026-01-01"
END_DATE = pd.Timestamp.now().strftime("%Y-%m-%d")

URLS = {
    "NASDAQ100_Forward_PE":
        "https://dollarliquidity.com/en/valuation/nasdaq-100-forward-pe",

    "SP500_Forward_PE":
        "https://dollarliquidity.com/en/valuation/sp-500-forward-pe",

    "SOX_Forward_PE":
        "https://dollarliquidity.com/en/valuation/semiconductor-forward-pe",
}


# ==========================================
# 1. 各ページからForward P/Eを抽出
# ==========================================

async def fetch_forward_pe(browser, name, url):

    print(f"\n取得中: {name}")
    print(f"URL: {url}")

    page = await browser.new_page()

    try:
        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        await page.wait_for_timeout(3000)

        html = await page.content()

        # エスケープされたJSON形式から抽出
        pattern = (
            r'\\"date\\":\\"(20\d{2}-\d{2}-\d{2})\\",'
            r'\\"pe\\":([0-9.]+),'
            r'\\"ey\\":([0-9.]+)'
        )

        matches = re.findall(pattern, html)

        # 通常のJSON形式も確認
        if not matches:
            pattern = (
                r'"date"\s*:\s*"(20\d{2}-\d{2}-\d{2})"\s*,'
                r'\s*"pe"\s*:\s*([0-9.]+)\s*,'
                r'\s*"ey"\s*:\s*([0-9.]+)'
            )

            matches = re.findall(pattern, html)

        if not matches:
            print(f"警告: {name} のデータを抽出できませんでした。")
            print("HTML文字数:", len(html))

            # データ形式の確認用情報
            for keyword in ['"date"', '\\"date\\"']:
                print(
                    f"{keyword} の出現回数:",
                    html.count(keyword)
                )

            return None

        df = pd.DataFrame(
            matches,
            columns=["Date", "Forward_PE", "Earnings_Yield"]
        )

        df["Date"] = pd.to_datetime(df["Date"])
        df["Forward_PE"] = pd.to_numeric(df["Forward_PE"])
        df["Earnings_Yield"] = pd.to_numeric(df["Earnings_Yield"])

        # 年初来に限定
        df = df[
            (df["Date"] >= START_DATE) &
            (df["Date"] <= END_DATE)
        ].copy()

        # 日付の重複を除去
        df = (
            df.drop_duplicates(subset=["Date"])
              .sort_values("Date")
              .reset_index(drop=True)
        )

        print("取得件数:", len(df))

        if not df.empty:
            print("開始日:", df["Date"].min().date())
            print("最終日:", df["Date"].max().date())

        # 指数名を付けて返す
        result = df[["Date", "Forward_PE"]].rename(
            columns={"Forward_PE": name}
        )

        return result

    finally:
        await page.close()


# ==========================================
# 2. 3指数を取得して結合
# ==========================================

async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=True)

        results = {}

        try:
            for name, url in URLS.items():

                result = await fetch_forward_pe(
                    browser,
                    name,
                    url
                )

                if result is not None and not result.empty:
                    results[name] = result

        finally:
            await browser.close()

    if not results:
        print("\nデータを取得できませんでした。")
        return None

    # Dateをキーにして3指数を横方向に結合
    combined = None

    for name in URLS.keys():

        if name not in results:
            continue

        if combined is None:
            combined = results[name]
        else:
            combined = pd.merge(
                combined,
                results[name],
                on="Date",
                how="outer"
            )

    # 日付順に並べる
    combined = (
        combined.sort_values("Date")
                .reset_index(drop=True)
    )

    # 日付を文字列にする
    combined["Date"] = combined["Date"].dt.strftime("%Y-%m-%d")

    # 列順を固定
    column_order = ["Date"] + [
        name for name in URLS.keys()
        if name in combined.columns
    ]

    combined = combined[column_order]

    print("\n================================")
    print("取得結果")
    print("================================")
    print("総データ件数:", len(combined))
    print("開始日:", combined["Date"].min())
    print("最終日:", combined["Date"].max())

    print("\n先頭10行:")
    print(combined.head(10).to_string(index=False))

    print("\n末尾10行:")
    print(combined.tail(10).to_string(index=False))

    # CSV保存
    output_dir = Path(__file__).resolve().parent.parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "forward_pe_3indices_2026.csv"

    combined.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nCSVファイルを作成しました:", output_file)

    return combined


# 実行
if __name__ == "__main__":
    df_forward_pe = asyncio.run(main())
