const chips = document.querySelectorAll('.filter-chip');
const cards = document.querySelectorAll('.content-card');
chips.forEach(chip => chip.addEventListener('click', () => {
  const selected = chip.dataset.filter;
  chips.forEach(item => item.classList.toggle('active', item === chip));
  cards.forEach(card => { card.hidden = selected !== 'すべて' && card.dataset.category !== selected; });
}));
const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('.main-nav');
menuButton.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', String(open));
});
nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  nav.classList.remove('open');
  menuButton.setAttribute('aria-expanded', 'false');
}));
document.getElementById('year').textContent = new Date().getFullYear();
// 準備中カードはリンク先へ移動しないようにします。
document.querySelectorAll('[data-placeholder="true"]').forEach(card => {
  card.addEventListener('click', event => event.preventDefault());
});


// articles.json は scripts/build_article_index.py で生成します。
async function loadLatestArticles() {
  const container = document.getElementById('latest-articles-grid');
  if (!container) return;
  try {
    const response = await fetch('articles.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('記事一覧を取得できませんでした');
    const articles = await response.json();
    const sorted = [...articles].sort((a, b) => (b.date || '').localeCompare(a.date || '')).slice(0, 6);
    if (!sorted.length) {
      container.innerHTML = '<p class="article-empty">記事はまだありません。記事を追加すると、ここに自動表示されます。</p>';
      return;
    }
    container.innerHTML = '';
    sorted.forEach(article => {
      const card = document.createElement('article');
      card.className = 'article-card';
      const link = document.createElement('a');
      link.className = 'article-card-link';
      link.href = article.url;
      const category = document.createElement('span');
      category.className = 'tag';
      category.textContent = article.category || '記事';
      const title = document.createElement('h3');
      title.textContent = article.title || 'タイトル未設定';
      const date = document.createElement('time');
      date.className = 'article-date';
      date.dateTime = article.date || '';
      date.textContent = article.date ? article.date.replaceAll('-', '/') : '';
      const description = document.createElement('p');
      description.textContent = article.description || '';
      const more = document.createElement('span');
      more.className = 'card-link';
      more.textContent = '記事を読む ↗';
      link.append(category, title, date, description, more);
      card.appendChild(link);
      container.appendChild(card);
    });
  } catch (error) {
    container.innerHTML = '<p class="article-empty">記事一覧を読み込めませんでした。articles.json が作成されているか確認してください。</p>';
    console.error(error);
  }
}
loadLatestArticles();

/* ========================================
MARKET WATCH：株価・ニュース自動表示
======================================== */

(() => {
const reportUrl = "market_report.html";
const dashboardFrame = document.getElementById("market-watch-source");
const indicesContainer = document.getElementById("market-watch-indices");
const headlinesContainer = document.getElementById("market-watch-headlines");
const dateContainer = document.getElementById("market-watch-date");

if (!dashboardFrame || !indicesContainer || !headlinesContainer) {
return;
}

const indexDefinitions = [
{
key: "sp500",
label: "S&P 500",
matches: ["S&P 500", "S&P500", "SP500"]
},
{
key: "nasdaq100",
label: "NASDAQ 100",
matches: ["NASDAQ-100", "NASDAQ 100", "NASDAQ100"]
},
{
key: "sox",
label: "SOX 半導体指数",
matches: ["SOX", "Philadelphia Semiconductor", "半導体指数"]
}
];

function normalizeText(value) {
return String(value || "")
.normalize("NFKC")
.replace(/[\s‐-‒–—−]/g, "")
.toUpperCase();
}

function findIndexCard(doc, definition) {
const cards = [...doc.querySelectorAll("#dashboard .card")];

return cards.find(card => {
  const nameElement = card.querySelector(".name");
  const tickerElement = card.querySelector(".ticker");
  const cardText = normalizeText(
    (nameElement?.textContent || "") + " " +
    (tickerElement?.textContent || "")
  );

  return definition.matches.some(match =>
    cardText.includes(normalizeText(match))
  );
});

}

function readChange(card) {
const changeElement = card?.querySelector(".change");

if (!changeElement) return null;

const text = changeElement.textContent.trim();

// 実際の騰落率表記だけを受け付ける
const match = text.match(/[+\-＋−]?\s*\d+(?:[.,]\d+)?\s*%/);

return match ? match[0].replace(/\s/g, "").replace(",", ".") : null;

}

function classifyChange(value) {
if (!value) return "market-watch-neutral";

const number = Number(
  value.replace("%", "").replace("＋", "+").replace("−", "-")
);

if (!Number.isFinite(number)) return "market-watch-neutral";
if (number > 0) return "market-watch-positive";
if (number < 0) return "market-watch-negative";

return "market-watch-neutral";

}

function renderIndices() {
try {
const doc = dashboardFrame.contentDocument;

  if (!doc || !doc.querySelector("#dashboard .card")) {
    return false;
  }

  const results = indexDefinitions.map(definition => {
    const card = findIndexCard(doc, definition);

    return {
      ...definition,
      change: readChange(card)
    };
  });

  indicesContainer.replaceChildren();

  results.forEach(item => {
    const link = document.createElement("a");
    link.className = "market-watch-index";
    link.href = reportUrl;
    link.setAttribute("aria-label", item.label + "の市場分析を見る");

    const name = document.createElement("span");
    name.className = "market-watch-index-name";
    name.textContent = item.label;

    const change = document.createElement("span");
    change.className =
      "market-watch-index-change " + classifyChange(item.change);

    // 値を確認できない場合は推測値を表示しない
    change.textContent = item.change || "取得できません";

    link.append(name, change);
    indicesContainer.appendChild(link);
  });

  if (dateContainer) {
    const asof = doc.querySelector("#asof");
    dateContainer.textContent =
      asof?.textContent.trim() || "ダッシュボードの表示データ";
  }

  return true;
} catch (error) {
  console.warn("市場ダッシュボードの読み取りに失敗しました。", error);
  return false;
}

}

async function loadHeadlines() {
try {
const response = await fetch("market_analysis.json", {
cache: "no-store"
});

  if (!response.ok) {
    throw new Error("market_analysis.json の取得に失敗しました");
  }

  const data = await response.json();
  const drivers = Array.isArray(data.drivers) ? data.drivers : [];

  headlinesContainer.replaceChildren();

  const titles = drivers
    .map(item => item?.title)
    .filter(title => typeof title === "string" && title.trim());

  if (titles.length === 0) {
    const li = document.createElement("li");
    li.textContent = "現在、表示できるニュース見出しはありません。";
    headlinesContainer.appendChild(li);
    return;
  }

  titles.forEach(title => {
    const li = document.createElement("li");
    const link = document.createElement("a");
    const text = document.createElement("span");
    const arrow = document.createElement("span");

    link.href = reportUrl;
    text.textContent = title.trim();
    arrow.className = "market-watch-arrow";
    arrow.textContent = "↗";

    link.append(text, arrow);
    li.appendChild(link);
    headlinesContainer.appendChild(li);
  });
} catch (error) {
  console.error("ニュース見出しの取得に失敗しました。", error);

  headlinesContainer.replaceChildren();

  const li = document.createElement("li");
  li.textContent = "ニュース見出しを取得できませんでした。";
  headlinesContainer.appendChild(li);
}

}

function waitForDashboard(attempt = 0) {
if (renderIndices()) return;

if (attempt >= 20) {
  indicesContainer.replaceChildren();

  const message = document.createElement("p");
  message.className = "market-watch-loading";
  message.textContent =
    "株価データを読み取れませんでした。市場分析ページでご確認ください。";

  indicesContainer.appendChild(message);
  return;
}

window.setTimeout(() => waitForDashboard(attempt + 1), 1000);

}

dashboardFrame.addEventListener("load", () => {
waitForDashboard();
});

// キャッシュ済みなどですでに読み込みが終わっている場合にも対応
if (dashboardFrame.contentDocument?.readyState === "complete") {
waitForDashboard();
}

loadHeadlines();
})();
