import os
import csv
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import pandas as pd
import pytz
import sys

LINE_TOKEN = os.getenv("LINE_TOKEN")
LOG_FILE = "trade_log.csv"

# ----------------------
# LINE送信
# ----------------------
def send_line(msg):
    if not LINE_TOKEN:
        print("LINE_TOKENが設定されていません")
        return
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(url, headers=headers, json={"messages":[{"type":"text","text":msg}]}, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"LINE送信エラー: {e}")

# ----------------------
# 決算銘柄取得
# ----------------------
def get_codes():
    try:
        url = "https://kabutan.jp/warning/?mode=1_2"
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
# テクニカル評価
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
    except Exception as e:
        print(f"{code} trend_reversalエラー: {e}")
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
    except Exception as e:
        print(f"{code} volume_checkエラー: {e}")
    return 0

# ----------------------
# PER / PEG
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
        if growth and growth > 0:
            peg = per / (growth*100)
            if peg < 1: score += 1
        return score
    except Exception as e:
        print(f"{code} valuationエラー: {e}")
        return 0

# ----------------------
# PDF/進捗簡易スコア
# ----------------------
def pdf_score(code):
    try:
        url = f"https://irbank.net/{code}"
        txt = requests.get(url, timeout=5).text
        score = 0
        if "進捗率" in txt: score += 2
        if "上方修正" in txt: score += 2
        return score
    except Exception as e:
        print(f"{code} pdf_scoreエラー: {e}")
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
def save_log(results):
    file_exists = os.path.isfile(LOG_FILE)
    jst = pytz.timezone('Asia/Tokyo')
    today = datetime.now(jst).strftime("%Y-%m-%d")
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "code", "rank", "score"])
        for r in results:
            writer.writerow([today, r[0], r[1], r[2]])

# ----------------------
# 週間ランキング
# ----------------------
def weekly_ranking(date_filter=None):
    if not os.path.exists(LOG_FILE): return "データなし\n"
    data = {}
    with open(LOG_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if date_filter and row["date"] != date_filter: continue
            code = row["code"]
            score = int(row["score"])
            data.setdefault(code, []).append(score)
    if not data: return "該当データなし\n"
    avg_scores = [(c, sum(v)/len(v)) for c,v in data.items()]
    avg_scores.sort(key=lambda x: x[1], reverse=True)
    msg = "【週間ランキング】\n"
    for i,(c,s) in enumerate(avg_scores[:10]):
        msg += f"{i+1}. {c} ({round(s,1)})\n"
    return msg + "\n"

# ----------------------
# 勝率分布
# ----------------------
def win_rate(date_filter=None):
    if not os.path.exists(LOG_FILE): return "勝率データなし\n"
    count = {"◎":0,"○":0,"△":0,"×":0}
    with open(LOG_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if date_filter and row["date"] != date_filter: continue
            count[row["rank"]] += 1
    total = sum(count.values())
    msg = "【勝率分布】\n"
    for k,v in count.items():
        if total > 0: msg += f"{k}: {round(v/total*100,1)}%\n"
    return msg + "\n"

# ----------------------
# 来週監視銘柄
# ----------------------
def next_watchlist(date_filter=None):
    if not os.path.exists(LOG_FILE): return "監視銘柄なし\n"
    scores = {}
    with open(LOG_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if date_filter and row["date"] != date_filter: continue
            code = row["code"]
            score = int(row["score"])
            scores[code] = scores.get(code,0)+score
    sorted_list = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    msg = "【来週監視銘柄】\n"
    for c,s in sorted_list[:10]: msg += f"{c}\n"
    return msg

# ----------------------
# 過去日ログ通知
# ----------------------
def send_past_log(date_str):
    if not os.path.exists(LOG_FILE):
        send_line("ログファイルがありません")
        return
    data = []
    with open(LOG_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["date"] == date_str:
                data.append(f"{row['code']} {row['rank']}({row['score']})")
    if not data:
        send_line(f"{date_str} の有効な決算なし")
        return
    msg = f"【決算結果 {date_str}】\n" + "\n".join(data[:10])
    msg += "\n" + weekly_ranking(date_str)
    msg += win_rate(date_str)
    msg += next_watchlist(date_str)
    send_line(msg)

# ----------------------
# メイン処理
# ----------------------
def run_screening():
    jst = pytz.timezone('Asia/Tokyo')
    today_wd = datetime.now(jst).weekday()
    codes = get_codes()

    if today_wd >= 5:  # 土日 → 週まとめ
        msg = "📊週次レポート\n\n"
        msg += weekly_ranking()
        msg += win_rate()
        msg += next_watchlist()
        send_line(msg)
        return

    if not codes:
        send_line("本日有効な決算なし")
        return

    results = []
    for c in codes:
        rank, score = evaluate(c)
        results.append((c, rank, score))
    results.sort(key=lambda x: x[2], reverse=True)
    save_log(results)

    msg = "【決算初動スクリーニング】★直後\n"
    for r in results[:10]:
        msg += f"{r[0]} {r[1]}({r[2]})\n"
    msg += "\n" + weekly_ranking()
    msg += win_rate()
    msg += next_watchlist()
    send_line(msg)

# ----------------------
# 実行
# ----------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 過去日指定
        send_past_log(sys.argv[1])
    else:
        # 当日決算
        run_screening()
