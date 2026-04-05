import os
import csv
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
import pytz
import sys

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
LOG_FILE = "trade_log.csv"

# ----------------------
# 日付取得
# ----------------------
def get_target_date():
    if len(sys.argv) > 1:
        return sys.argv[1]
    else:
        jst = pytz.timezone("Asia/Tokyo")
        return datetime.now(jst).strftime("%Y-%m-%d")

# ----------------------
# Discord送信
# ----------------------
def send_discord(msg):
    if not DISCORD_WEBHOOK_URL:
        print("Webhook未設定")
        return

    data = {
        "embeds": [{
            "title": "📊 決算初動スクリーニング",
            "description": f"```{msg}```",
            "color": 5814783
        }]
    }

    try:
        res = requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"Discord送信エラー: {e}")

# ----------------------
# 決算銘柄取得
# ----------------------
def get_codes(date):
    try:
        url = f"https://kabutan.jp/warning/?mode=1_2&date={date.replace('-','')}"
        res = requests.get(url, headers={"User-Agent":"Mozilla"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        codes = []
        for a in soup.find_all("a"):
            href = a.get("href","")
            if "/stock/" in href:
                c = href.split("/stock/")[1].split("/")[0]
                if c.isdigit() and len(c)==4:
                    codes.append(c)

        return list(set(codes))

    except Exception as e:
        print(f"銘柄取得エラー: {e}")
        return []

# ----------------------
# テクニカル
# ----------------------
def trend_reversal(code):
    try:
        df = yf.Ticker(f"{code}.T").history(period="1y")
        if len(df) < 200: return 0

        close = df["Close"]
        ma200 = close.rolling(200).mean()
        ma25 = close.rolling(25).mean()
        ma5 = close.rolling(5).mean()

        price = close.iloc[-1]
        kairi = (price - ma200.iloc[-1]) / ma200.iloc[-1] * 100

        score = 0
        if price < ma200.iloc[-1]: score += 1
        if -20 < kairi < -5: score += 1
        if ma25.iloc[-1] >= ma25.iloc[-5]: score += 1
        if price > ma5.iloc[-1]: score += 1

        return score
    except:
        return 0

# ----------------------
# 出来高
# ----------------------
def volume_check(code):
    try:
        df = yf.Ticker(f"{code}.T").history(period="1mo")
        v = df["Volume"]

        if v.iloc[-1] > v.mean()*2: return 2
        elif v.iloc[-1] > v.mean(): return 1

    except:
        return 0

# ----------------------
# バリュエーション
# ----------------------
def valuation(code):
    try:
        info = yf.Ticker(f"{code}.T").info
        per = info.get("trailingPE")
        growth = info.get("earningsGrowth")

        score = 0

        if per:
            if per < 20: score += 2
            elif per < 40: score += 1

        if per and growth and growth > 0:
            peg = per / (growth*100)
            if peg < 1: score += 1

        return score
    except:
        return 0

# ----------------------
# IR簡易スコア
# ----------------------
def pdf_score(code):
    try:
        url = f"https://irbank.net/{code}"
        txt = requests.get(url, timeout=5).text

        score = 0
        if "進捗率" in txt: score += 2
        if "上方修正" in txt: score += 2

        return score
    except:
        return 0

# ----------------------
# 総合評価
# ----------------------
def evaluate(code):
    score = trend_reversal(code) + volume_check(code) + valuation(code) + pdf_score(code)

    if score >= 8: rank = "◎"
    elif score >= 5: rank = "○"
    elif score >= 3: rank = "△"
    else: rank = "×"

    return rank, score

# ----------------------
# ログ保存
# ----------------------
def save_log(results, date):
    file_exists = os.path.isfile(LOG_FILE)

    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["date", "code", "rank", "score"])

        for r in results:
            writer.writerow([date, r[0], r[1], r[2]])

# ----------------------
# メイン
# ----------------------
def run_screening():
    target_date = get_target_date()
    codes = get_codes(target_date)

    if not codes:
        send_discord(f"本日決算なし ({target_date})")
        return

    results = []

    for c in codes:
        rank, score = evaluate(c)
        results.append((c, rank, score))

    results.sort(key=lambda x: x[2], reverse=True)
    save_log(results, target_date)

    msg = f"★直後 ({target_date})\n"
    for r in results[:10]:
        msg += f"{r[0]} {r[1]}({r[2]})\n"

    send_discord(msg)

# ----------------------
# 実行
# ----------------------
if __name__ == "__main__":
    run_screening()
