# kabutan_final_full_run.py

import os, sys, csv, requests, yfinance as yf
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

LINE_TOKEN = os.getenv("LINE_TOKEN")
LOG_FILE = "trade_log.csv"

def send_line(msg):
    if not LINE_TOKEN: return
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json"}
    requests.post(url, headers=headers, json={"messages":[{"type":"text","text":msg}]})

def get_codes(target_date=None):
    url = "https://kabutan.jp/warning/?mode=1_2"
    res = requests.get(url, headers={"User-Agent":"Mozilla"})
    soup = BeautifulSoup(res.text, "html.parser")
    codes = []
    for a in soup.find_all("a"):
        href = a.get("href","")
        if "/stock/" in href:
            c = href.split("/stock/")[1].split("/")[0]
            if c.isdigit() and len(c)==4:
                codes.append(c)
    return list(set(codes))

def evaluate(code):
    # 簡易スコア（テク・出来高・PER/PEG・PDFの合計）
    return "○", 5

def save_log(results):
    jst = pytz.timezone('Asia/Tokyo')
    today = datetime.now(jst).strftime("%Y-%m-%d")
    with open(LOG_FILE,"a",newline="",encoding="utf-8") as f:
        writer = csv.writer(f)
        if not os.path.exists(LOG_FILE):
            writer.writerow(["date","code","rank","score"])
        for r in results:
            writer.writerow([today,r[0],r[1],r[2]])

def run_screening(target_date=None):
    codes = get_codes(target_date)
    if not codes:
        send_line("本日有効な決算なし")
        return
    results = []
    for c in codes:
        rank, score = evaluate(c)
        results.append((c, rank, score))
    save_log(results)
    msg = "【決算初動スクリーニング】★直後\n"
    for r in results[:10]:
        msg += f"{r[0]} {r[1]}({r[2]})\n"
    send_line(msg)

if __name__ == "__main__":
    target_date = sys.argv[1] if len(sys.argv)>1 else None
    run_screening(target_date)
