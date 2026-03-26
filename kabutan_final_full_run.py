import os
import sys
import csv
from datetime import datetime
import pytz
import requests
from bs4 import BeautifulSoup
import yfinance as yf

LINE_TOKEN = os.getenv("LINE_TOKEN")  # GitHub Secrets に登録
LOG_FILE = "trade_log.csv"

# ----------------------
# LINE送信
# ----------------------
def send_line(msg):
    if not LINE_TOKEN:
        print("LINE_TOKENが設定されていません")
        return
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    try:
        res = requests.post(url, headers=headers, data={"message": msg}, timeout=10)
        res.raise_for_status()
        print(f"LINE送信成功: {msg[:30]}...")
    except Exception as e:
        print(f"LINE送信エラー: {e}")

# ----------------------
# 今日の決算銘柄取得
# ----------------------
def get_today_codes():
    try:
        url = "https://kabutan.jp/warning/?mode=1_2"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        codes = []
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if "/stock/" in href:
                c = href.split("/stock/")[1].split("/")[0]
                if c.isdigit() and len(c) == 4:
                    codes.append(c)
        codes = list(set(codes))
        print(f"本日の決算銘柄取得: {codes}")
        return codes
    except Exception as e:
        print(f"銘柄取得エラー: {e}")
        return []

# ----------------------
# 決算評価（簡易）
# ----------------------
def evaluate(code):
    return "○", 5

# ----------------------
# ログ保存
# ----------------------
def save_log(results, date_str):
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["date", "code", "rank", "score"])
        for r in results:
            writer.writerow([date_str, r[0], r[1], r[2]])
    print(f"{date_str} の結果をログ保存しました")

# ----------------------
# 過去日の通知
# ----------------------
def notify_past(date_str):
    if not os.path.exists(LOG_FILE):
        send_line(f"{date_str} のログなし")
        return
    results = []
    with open(LOG_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["date"] == date_str:
                results.append((row["code"], row["rank"], row["score"]))
    if not results:
        send_line(f"{date_str} 本日有効な決算なし")
        return
    msg = f"【{date_str} 決算結果】\n"
    for r in results[:10]:
        msg += f"{r[0]} {r[1]}({r[2]})\n"
    send_line(msg)

# ----------------------
# メイン処理
# ----------------------
def run_screening(target_date=None):
    jst = pytz.timezone("Asia/Tokyo")
    today_str = datetime.now(jst).strftime("%Y-%m-%d")
    date_str = target_date if target_date else today_str

    if target_date:
        notify_past(date_str)
        return

    codes = get_today_codes()
    if not codes:
        send_line("本日有効な決算なし")
        return

    results = []
    for c in codes:
        rank, score = evaluate(c)
        results.append((c, rank, score))
    save_log(results, date_str)

    msg = f"【{date_str} 決算初動スクリーニング】★直後\n"
    for r in results[:10]:
        msg += f"{r[0]} {r[1]}({r[2]})\n"
    send_line(msg)

if __name__ == "__main__":
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    run_screening(target_date)
