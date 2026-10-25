# Beyond the Headlines — Homepage

日本語の投資・経済分析サイト向け、静的なトップページです。HTML/CSS/JavaScriptのみで動作し、GitHub PagesやVercelに配置できます。

## ファイル構成
- `index.html` — ページ本文、カテゴリー、コンテンツカード
- `styles.css` — レスポンシブデザイン
- `script.js` — カテゴリーフィルター、スマートフォン用メニュー
- `assets/hero-banner.png` — ご提供いただいた画像

## コンテンツのリンクを追加する
`index.html` 内で、対象カードの `href="#"` を実際のURLに置き換えてください。カードのタイトル、説明文、`data-category` も必要に応じて変更します。

例：
```html
<a class="content-card" href="https://your-project.vercel.app/" data-category="株式市場">
```

リンクを設定したカードは、`data-placeholder="true"` を削除し、カード内の「準備中」も「コンテンツを見る」などに変更してください。

## Vercelへのデプロイ
1. このフォルダの中身をGitHubリポジトリのルートにアップロードします。
2. VercelでそのGitHubリポジトリをImportします。
3. フレームワークは `Other`（または静的サイト）を選び、Build Commandは空欄、Output Directoryは `.` にします。
4. Deployを実行します。

ビルド工程が不要な静的サイトです。Google Fontsを読み込む設定があるため、フォントの表示にはインターネット接続が必要です。


## 記事を追加してトップページへ自動表示する

このサイトでは、記事HTMLを `articles/` に追加し、Pythonスクリプトで `articles.json` を生成します。トップページはこのJSONを読み込み、最新6件を自動表示します。`articles.html` では記事一覧全件を表示します。

### 記事追加の手順
1. `templates/article-template.html` をコピーし、`articles/` 内に `my-article.html` などの名前で保存します。
2. 記事HTMLの `<title>`、`<meta name="article-date">`、`<meta name="article-category">`、`<meta name="description">` を編集します。
3. 記事本文を書き、必要なチャートへの相対リンクを設定します（例：`../sp500_drawdown_style.html`）。
4. リポジトリのルートで `python scripts/build_article_index.py` を実行します。
5. `articles/` の新しい記事と、更新された `articles.json` をGitHubへpushします。
6. Vercelが自動デプロイし、トップページに最新記事が表示されます。

### 注意点
- 記事を追加しただけでは一覧は更新されません。`build_article_index.py` を実行し、生成された `articles.json` もGitHubへ反映してください。
- 記事の日付は `YYYY-MM-DD` 形式で指定してください。
- トップページは最新6件、記事一覧ページは全記事を表示します。
- 現在の分析コンテンツ一覧は維持し、記事一覧とは別のエリアにしています。
