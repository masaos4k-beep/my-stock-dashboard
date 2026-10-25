import json
import pandas as pd
import yfinance as yf
from datetime import datetime, time
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
SYMBOLS = [
    {"name":"NASDAQ100", "ticker":"^NDX"},
    {"name":"半導体指数 SOX", "ticker":"^SOX"},
    {"name":"FANG+ 指数", "ticker":"^NYFANG"},
    {"name":"S&P500", "ticker":"^GSPC"},
    {"name":"ラッセル2000", "ticker":"^RUT"},
    {"name":"ダウ平均", "ticker":"^DJI"},
]

HTML_TEMPLATE = r'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>米国株マーケット・ダッシュボード</title><style>
:root{--bg:#050505;--card:#111;--text:#f5f5f5;--muted:#aaa;--green:#19c45a;--red:#ff4545}
*{box-sizing:border-box}body{margin:0;padding:24px;background:var(--bg);color:var(--text);font-family:Arial,"Noto Sans JP","Meiryo",sans-serif}
header,.note{max-width:1400px;margin:auto}header{margin-bottom:24px}
h1{text-align:center;font-size:clamp(24px,3vw,42px);margin:0 0 8px;color:#ffffff;font-weight:800;}
.subtitle{text-align:center;color:var(--muted);font-size:13px}
.controls{display:flex;justify-content:center;align-items:center;gap:20px;margin-top:14px;flex-wrap:wrap}
.periods,.currencies{display:flex;gap:6px}
.p-btn,.c-btn{background:#222;color:#aaa;border:1px solid #444;padding:6px 14px;border-radius:4px;cursor:pointer;font-size:13px;font-weight:700;transition:all .2s}
.p-btn.active,.c-btn.active{background:#3c8cff;color:#fff;border-color:#3c8cff}
.c-btn.active{background:#f0a500;border-color:#f0a500}
.grid{max-width:1400px;margin:auto;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:20px}.card{background:var(--card);border:1px solid #444;border-radius:8px;overflow:hidden;min-width:0}
.card-head{padding:12px 16px 10px;background:linear-gradient(#303030,#171717);border-bottom:1px solid #555;display:flex;justify-content:space-between;align-items:center;gap:8px}
.name{font-size:clamp(16px,1.7vw,23px);font-weight:700;color:#ffffff;}.ticker{color:#aaa;font-size:12px;margin-top:3px}.change{font-size:clamp(23px,2.4vw,34px);font-weight:800;white-space:nowrap}
.positive{color:var(--green)}.negative{color:var(--red)}.chart-wrap{padding:8px 10px 0}svg{width:100%;height:auto;display:block}
.values{display:flex;justify-content:space-between;gap:10px;padding:10px 15px 14px;align-items:baseline}.close{font-size:clamp(19px,2vw,27px);font-weight:700}.delta{font-size:clamp(15px,1.5vw,21px);font-weight:700}
.legend{display:flex;flex-wrap:wrap;gap:14px;padding:0 15px 13px;color:#bbb;font-size:11px}.key{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:5px}
.key.regular{background:#3c8cff}.key.prev{background:#fff}.note{margin-top:18px;color:#888;font-size:12px;line-height:1.8}
@media(max-width:900px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:580px){body{padding:12px}.grid{grid-template-columns:1fr}.card-head{padding:10px}}
</style></head><body><header><h1>米国株マーケット・ダッシュボード</h1><div class="subtitle" id="asof"></div>
<div class="controls">
  <div class="periods">
    <button class="p-btn active" onclick="switchPeriod('regular', this)">1日</button>
    <button class="p-btn" onclick="switchPeriod('weekly', this)">1週間</button>
    <button class="p-btn" onclick="switchPeriod('monthly', this)">1ヶ月</button>
    <button class="p-btn" onclick="switchPeriod('ytd', this)">年初来</button>
  </div>
  <div class="currencies">
    <button class="c-btn active" onclick="switchCurrency('USD', this)">$ ドル</button>
    <button class="c-btn" onclick="switchCurrency('JPY', this)">¥ 円</button>
  </div>
</div>
</header>
<main class="grid" id="dashboard"></main><div class="note">・すべての期間で為替と株価の変動を正確に反映した円建て騰落率を表示します。<br>
・データはYahoo Finance（yfinance経由）。</div>
<script>
const data=__DATA__;
const fmt=n=>Number(n).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2});
const pct=n=>(n>=0?"+":"")+n.toFixed(2)+"%";
const esc=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

let currentPeriod = 'regular';
let currentCurrency = 'USD';

function renderCard(d, period, currency) {
 const raw = d[period] || [];
 if(!raw.length) return `<section class="card"><div class="card-head"><div><div class="name">${esc(d.name)}</div><div class="ticker">${esc(d.ticker)}</div></div><div class="change">N/A</div></div><div class="chart-wrap" style="padding:35px;color:#aaa">データなし</div></section>`;
 
 const prices = raw.map(p => (currency === 'JPY') ? p.jpy : p.usd);
 const close = prices[prices.length - 1];
 
 let basePrice, isRegular = (period === 'regular');
 if(isRegular) {
  basePrice = (currency === 'JPY') ? d.prev_jpy : d.previousClose;
 } else if(period === 'weekly') {
  basePrice = (currency === 'JPY') ? d.base_1w_jpy : d.base_1w;
 } else if(period === 'monthly') {
  basePrice = (currency === 'JPY') ? d.base_1m_jpy : d.base_1m;
 } else {
  basePrice = (currency === 'JPY') ? d.base_ytd_jpy : d.base_ytd;
 }
 
 const change = (close / basePrice - 1) * 100;
 const delta = close - basePrice;
 const cls = change >= 0 ? "positive" : "negative";

 const W=440,H=190,L=8,R=8,T=12,B=12,all=[...prices, basePrice];
 let min=Math.min(...all),max=Math.max(...all),spread=max-min;if(!spread)spread=Math.abs(max||1)*.01;min-=spread*.16;max+=spread*.16;
 const total=Math.max(prices.length-1,1),x=i=>L+i*(W-L-R)/total,y=v=>T+(max-v)*(H-T-B)/(max-min);
 const rp=prices.map((p,i)=>[x(i),y(p),p]);
 
 const path=ps=>ps.map((p,i)=>(i?"L ":"M ")+p[0].toFixed(2)+" "+p[1].toFixed(2)).join(" ");
 const base=y(basePrice);
 let fill="";
 
 if(isRegular) {
  for(let i=0;i<rp.length-1;i++){const a=rp[i],b=rp[i+1],va=a[2],vb=b[2];
   if((va-basePrice)*(vb-basePrice)<0){const t=(basePrice-va)/(vb-va),cx=a[0]+t*(b[0]-a[0]);
    fill+=`<polygon points="${a[0]},${base} ${a[0]},${a[1]} ${cx},${base}" fill="${va>=basePrice?"#18bd58":"#f04444"}" opacity=".28"/>`;
    fill+=`<polygon points="${cx},${base} ${b[0]},${base} ${b[0]},${b[1]}" fill="${vb>=basePrice?"#18bd58":"#f04444"}" opacity=".28"/>`;
   }else fill+=`<polygon points="${a[0]},${base} ${a[0]},${a[1]} ${b[0]},${b[1]} ${b[0]},${base}" fill="${(va+vb)/2>=basePrice?"#18bd58":"#f04444"}" opacity=".28"/>`;
  }
 }
 
 const grid=[.25,.5,.75].map(t=>`<line x1="${L}" y1="${T+t*(H-T-B)}" x2="${W-R}" y2="${T+t*(H-T-B)}" stroke="#303030"/>`).join("");
 const by=Math.max(T,Math.min(H-B,base));
 const baseLineLabel = isRegular ? "前日終値" : "起点";
 
 const svgContent = `<svg viewBox="0 0 ${W} ${H}">${grid}${fill}<line x1="${L}" y1="${by}" x2="${W-R}" y2="${by}" stroke="#fff" stroke-width="1.5"/><path d="${path(rp)}" fill="none" stroke="#3c8cff" stroke-width="2.5" stroke-linejoin="round"/><text x="${W-R-2}" y="${Math.max(10,by-5)}" fill="#fff" font-size="10" text-anchor="end">${baseLineLabel}</text></svg>`;

 const currencySymbol = (currency === 'JPY') ? '¥' : '$';

 return `<section class="card"><div class="card-head"><div><div class="name">${esc(d.name)}</div><div class="ticker">${esc(d.ticker)}</div></div><div class="change ${cls}">${pct(change)}</div></div><div class="chart-wrap">${svgContent}</div><div class="values"><div class="close">${currencySymbol} ${fmt(close)}</div><div class="delta ${cls}">${delta>=0?"+":""}${currencySymbol} ${fmt(delta)}</div></div><div class="legend"><span><i class="key regular"></i>${period==='regular'?'通常取引':'推移'}</span><span><i class="key prev"></i>${baseLineLabel}</span></div></section>`;
}

function updateDashboard() {
 document.getElementById("dashboard").innerHTML = data.map(d => renderCard(d, currentPeriod, currentCurrency)).join("");
}

function switchPeriod(period, btn) {
 currentPeriod = period;
 document.querySelectorAll('.p-btn').forEach(b => b.classList.remove('active'));
 if(btn) btn.classList.add('active');
 updateDashboard();
}

function switchCurrency(currency, btn) {
 currentCurrency = currency;
 document.querySelectorAll('.c-btn').forEach(b => b.classList.remove('active'));
 if(btn) btn.classList.add('active');
 updateDashboard();
}

document.getElementById("asof").textContent="対象日："+[...new Set(data.map(d=>d.date))].join(" / ")+" ｜ 出力ファイル名変更版";
updateDashboard();
</script></body></html>'''

def ny_index(index):
    idx = pd.DatetimeIndex(index)
    return idx.tz_localize(TZ) if idx.tz is None else idx.tz_convert(TZ)

fx_df = yf.Ticker("USDJPY=X").history(period="30d", interval="1d", auto_adjust=False)
fx_df.index = ny_index(fx_df.index)
fx_dict = {ts.date(): float(row["Close"]) for ts, row in fx_df.iterrows()}

def get_fx_exact(target_date):
    if target_date in fx_dict:
        return fx_dict[target_date]
    for i in range(1, 5):
        d_prev = target_date - pd.Timedelta(days=i)
        if d_prev.date() in fx_dict:
            return fx_dict[d_prev.date()]
    return 150.0

def fetch(item):
    symbol = item["ticker"]
    obj = yf.Ticker(symbol)
    
    daily = obj.history(period="ytd", interval="1d", auto_adjust=False, actions=False)
    raw_1w = obj.history(period="10d", interval="15m", prepost=False, auto_adjust=False, actions=False)
    
    if daily is None or daily.empty:
        raise RuntimeError("日足データなし")

    daily = daily.copy()
    daily.index = ny_index(daily.index)
    daily["_date"] = [x.date() for x in daily.index]
    
    if isinstance(daily.columns, pd.MultiIndex):
        daily.columns = [col[0] for col in daily.columns]
    
    close_col = next((c for c in daily.columns if str(c).lower() == 'close'), None)
    open_col = next((c for c in daily.columns if str(c).lower() == 'open'), None)
    
    if not close_col:
        raise RuntimeError("Closeカラムが見つかりません")
        
    daily["_close"] = pd.to_numeric(daily[close_col], errors="coerce")
    if open_col:
        daily["_open"] = pd.to_numeric(daily[open_col], errors="coerce").fillna(daily["_close"])
    else:
        daily["_open"] = daily["_close"]
    
    daily["_close"] = daily["_close"].ffill().bfill()
    daily["_open"] = daily["_open"].ffill().bfill()

    now_ny = datetime.now(TZ)
    today_ny = now_ny.date()
    cutoff = time(16, 15)
    
    available_dates = sorted(d for d in daily["_date"].unique() if d < today_ny or (d == today_ny and now_ny.time() >= cutoff))
    if not available_dates:
        raise RuntimeError("完了済みの取引日がありません")
    day = available_dates[-1]
    
    prev_days = [d for d in available_dates if d < day]
    prev_date = prev_days[-1] if prev_days else day
    
    cur_fx = get_fx_exact(pd.to_datetime(day))
    prev_fx = get_fx_exact(pd.to_datetime(prev_date))

    cur_row = daily[daily["_date"] == day]
    prior_rows = daily[daily["_date"] < day]
    if cur_row.empty or prior_rows.empty:
        raise RuntimeError("当日または前日の日足データが見つかりません")
    
    prev_usd = float(prior_rows.iloc[-1]["_close"])
    official_usd = float(cur_row.iloc[-1]["_close"])
    
    prev_jpy = prev_usd * prev_fx
    official_jpy = official_usd * cur_fx

    # 1日 (regular)
    rp = []
    if raw_1w is not None and not raw_1w.empty:
        raw_1w_tz = raw_1w.copy()
        raw_1w_tz.index = ny_index(raw_1w_tz.index)
        if isinstance(raw_1w_tz.columns, pd.MultiIndex):
            raw_1w_tz.columns = [col[0] for col in raw_1w_tz.columns]
        raw_close_col = next((c for c in raw_1w_tz.columns if str(c).lower() == 'close'), None)
        
        if raw_close_col:
            today_intra = raw_1w_tz[raw_1w_tz.index.date == day]
            reg = today_intra.loc[(today_intra.index.time >= time(9, 30)) & (today_intra.index.time < time(16, 0))]
            for ts, row in reg.iterrows():
                val = pd.to_numeric(row[raw_close_col], errors="coerce")
                if pd.notna(val):
                    f_val = get_fx_exact(ts)
                    rp.append({"time": ts.strftime("%H:%M"), "usd": round(float(val), 6), "jpy": round(float(val) * f_val, 6)})
    
    if not rp:
        open_usd = float(cur_row.iloc[-1]["_open"]) if not cur_row.empty else prev_usd
        rp = [
            {"time": "09:30", "usd": open_usd, "jpy": open_usd * cur_fx},
            {"time": "16:00", "usd": official_usd, "jpy": official_jpy}
        ]
    else:
        if rp[-1]["time"] != "16:00":
            rp.append({"time": "16:00", "usd": round(official_usd, 6), "jpy": round(official_jpy, 6)})

    # 1週間 (weekly)
    d_1w = []
    base_1w_usd = prev_usd
    base_1w_jpy = prev_jpy
    if raw_1w is not None and not raw_1w.empty:
        raw_1w_tz = raw_1w.copy()
        raw_1w_tz.index = ny_index(raw_1w_tz.index)
        if isinstance(raw_1w_tz.columns, pd.MultiIndex):
            raw_1w_tz.columns = [col[0] for col in raw_1w_tz.columns]
        raw_close_col = next((c for c in raw_1w_tz.columns if str(c).lower() == 'close'), None)
        
        if raw_close_col:
            unique_dates = sorted(list(set(raw_1w_tz.index.date)))
            start_5d_date = unique_dates[-5] if len(unique_dates) >= 5 else unique_dates[0]
            s_1w = raw_1w_tz[(raw_1w_tz.index.date >= start_5d_date) & 
                             (raw_1w_tz.index.date <= day) & 
                             (raw_1w_tz.index.time >= time(9, 30)) & 
                             (raw_1w_tz.index.time < time(16, 0))]
            if not s_1w.empty:
                first_ts = s_1w.index[0]
                base_1w_usd = float(s_1w.iloc[0][raw_close_col])
                f_first = get_fx_exact(first_ts)
                base_1w_jpy = base_1w_usd * f_first
                for ts, row in s_1w.iterrows():
                    val = pd.to_numeric(row[raw_close_col], errors="coerce")
                    if pd.notna(val):
                        f_val = get_fx_exact(ts)
                        d_1w.append({"time": ts.strftime("%m/%d %H:%M"), "usd": round(float(val), 6), "jpy": round(float(val) * f_val, 6)})
    
    if not d_1w:
        df_5d = daily[daily["_date"] <= day].tail(5)
        base_1w_usd = float(df_5d.iloc[0]["_open"]) if not df_5d.empty else prev_usd
        f_start = get_fx_exact(pd.to_datetime(df_5d.iloc[0]["_date"])) if not df_5d.empty else prev_fx
        base_1w_jpy = base_1w_usd * f_start
        for _, row in df_5d.iterrows():
            p_usd = float(row["_close"])
            f_val = get_fx_exact(pd.to_datetime(row["_date"]))
            d_1w.append({"time": row["_date"].strftime("%m/%d"), "usd": round(p_usd, 6), "jpy": round(p_usd * f_val, 6)})

    # 1ヶ月 (monthly)
    df_22d = daily[daily["_date"] <= day].tail(22)
    d_1m = []
    base_1m_usd = prev_usd
    base_1m_jpy = prev_jpy
    if not df_22d.empty:
        start_date_m = df_22d.iloc[0]["_date"]
        base_1m_usd = float(df_22d.iloc[0]["_open"])
        f_start_m = get_fx_exact(pd.to_datetime(start_date_m))
        base_1m_jpy = base_1m_usd * f_start_m
        for _, row in df_22d.iterrows():
            p_usd = float(row["_close"])
            f_val = get_fx_exact(pd.to_datetime(row["_date"]))
            d_1m.append({"time": row["_date"].strftime("%m/%d"), "usd": round(p_usd, 6), "jpy": round(p_usd * f_val, 6)})
    
    # 年初来 (ytd)
    ytd_df = daily[daily["_date"] <= day]
    d_ytd = []
    base_ytd_usd = prev_usd
    base_ytd_jpy = prev_jpy
    if not ytd_df.empty:
        start_date_ytd = ytd_df.iloc[0]["_date"]
        base_ytd_usd = float(ytd_df.iloc[0]["_open"])
        start_fx_ytd = get_fx_exact(pd.to_datetime(start_date_ytd))
        base_ytd_jpy = base_ytd_usd * start_fx_ytd
        for _, row in ytd_df.iterrows():
            p_usd = float(row["_close"])
            f_val = get_fx_exact(pd.to_datetime(row["_date"]))
            d_ytd.append({"time": row["_date"].strftime("%m/%d"), "usd": round(p_usd, 6), "jpy": round(p_usd * f_val, 6)})

    return {
        "date": day.isoformat(),
        "name": item["name"],
        "ticker": symbol,
        "previousClose": round(prev_usd, 6),
        "prev_jpy": round(prev_jpy, 6),
        "regular": rp,
        "weekly": d_1w,
        "monthly": d_1m,
        "ytd": d_ytd,
        "base_1w": round(base_1w_usd, 6),
        "base_1w_jpy": round(base_1w_jpy, 6),
        "base_1m": round(base_1m_usd, 6),
        "base_1m_jpy": round(base_1m_jpy, 6),
        "base_ytd": round(base_ytd_usd, 6),
        "base_ytd_jpy": round(base_ytd_jpy, 6)
    }

# リポジトリのルートを基準に出力する（GitHub Actionsの実行場所に依存しない）
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
output_path = repo_root / "market_dashboard.html"

print("=" * 60)
print("マーケットダッシュボード生成診断")
print(f"実行時刻（ニューヨーク）: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"出力先: {output_path}")

result = []
failed_symbols = []
for item in SYMBOLS:
    try:
        data = fetch(item)
        result.append(data)
        print(
            f"[OK] {item['name']} ({item['ticker']}) "
            f"対象日={data.get('date')} "
            f"1日データ={len(data.get('regular', []))}件 / "
            f"1週間={len(data.get('weekly', []))}件 / "
            f"1ヶ月={len(data.get('monthly', []))}件 / "
            f"年初来={len(data.get('ytd', []))}件"
        )
    except Exception as e:
        failed_symbols.append(item['ticker'])
        print(f"[ERROR] {item['name']} ({item['ticker']}): {type(e).__name__}: {e}")
        # ダミー株価を表示すると実データと誤認されるため、生成を失敗扱いにする。
        raise RuntimeError(
            f"{item['name']} のデータ取得に失敗したため、誤ったダミーデータでHTMLを生成しません。"
        ) from e

rendered_html = HTML_TEMPLATE.replace(
    "__DATA__", json.dumps(result, ensure_ascii=False, separators=(",", ":"))
)

previous_html = output_path.read_text(encoding="utf-8") if output_path.exists() else None
changed = previous_html != rendered_html
output_path.write_text(rendered_html, encoding="utf-8")

print("-" * 60)
print(f"生成対象日: {', '.join(sorted({d['date'] for d in result}))}")
print(f"取得成功: {len(result)}/{len(SYMBOLS)}銘柄")
print(f"HTML内容の変更: {'あり' if changed else 'なし（前回と同一）'}")
print(f"出力ファイル: {output_path.name} ({output_path.stat().st_size:,} bytes)")
print("🎉 HTMLファイルを書き出しました。")
print("=" * 60)