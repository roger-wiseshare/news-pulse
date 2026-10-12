"""抓取跑馬燈用的行情，輸出 quotes.json（給 Blogger 讀取）。
資料來源：Yahoo Finance 公開報價（約延遲 15 到 20 分鐘）。只用 Python 標準函式庫。
任何一檔抓不到時，沿用 quotes.json 裡上一次的數值並標記 stale，不會讓整條跑馬燈消失。
"""
import json, os, sys, time, urllib.request, urllib.parse
from datetime import datetime, timezone

SYMBOLS = [
    ("^TWII", "加權指數", 2),
    ("2330.TW", "台積電", 2),
    ("2454.TW", "聯發科", 2),
    ("2317.TW", "鴻海", 2),
    ("2308.TW", "台達電", 2),
    ("2347.TW", "聯強", 2),
    ("^DJI", "道瓊", 2),
    ("^SOX", "費城半導體", 2),
    ("^GSPC", "標普500", 2),
    ("^NDX", "那斯達克100", 2),
    ("TWD=X", "美元/台幣", 3),
    ("BTC-USD", "比特幣", 0),
]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "quotes.json")
UA = "Mozilla/5.0 (compatible; QuotesBot/1.0)"


def fetch(sym):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=1d&range=5d" % urllib.parse.quote(sym)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.load(r)
            res = j["chart"]["result"][0]
            price = res["meta"]["regularMarketPrice"]
            closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
            if len(closes) >= 2 and abs(closes[-1] - price) <= 1e-6 * max(1.0, abs(price)):
                prev = closes[-2]
            elif closes:
                prev = closes[-1]
            else:
                prev = res["meta"].get("chartPreviousClose", price)
            return float(price), float(price) - float(prev), float(res["meta"].get("regularMarketTime", 0))
        except Exception as e:
            print("retry", sym, attempt, e, file=sys.stderr)
            time.sleep(2 * (attempt + 1))
    return None


def main():
    try:
        old = {i["k"]: i for i in json.load(open(OUT, encoding="utf-8")).get("items", [])}
    except Exception:
        old = {}
    items = []
    for sym, name, nd in SYMBOLS:
        got = fetch(sym)
        if got:
            price, chg, t = got
            prev = price - chg
            items.append({"k": sym, "n": name, "p": round(price, nd), "c": round(chg, nd),
                          "pct": round(chg / prev * 100, 2) if prev else 0, "d": nd})
        elif sym in old:
            o = dict(old[sym]); o["stale"] = True
            items.append(o)
    if not items:
        print("no data", file=sys.stderr); sys.exit(1)
    out = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "items": items}
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("ok", len(items), "items")


if __name__ == "__main__":
    main()
