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
