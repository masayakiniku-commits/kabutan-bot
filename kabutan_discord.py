import requests
from bs4 import BeautifulSoup
import datetime
import os
import re

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")


# =========================
# 決算一覧取得
# =========================
def get_kabutan_list():
    url = "https://kabutan.jp/news/marketnews/?category=2"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    items = soup.select(".news_list li")
    results = []

    today = datetime.datetime.now().strftime("%m/%d")

    for item in items:
        text = item.get_text()
        if today in text:
            a = item.find("a")
            title = a.text
            link = "https://kabutan.jp" + a["href"]

            m = re.search(r"\((\d{4}[A-Z]?)\)", title)
            code = m.group(1) if m else "----"
            name = title.split("(")[0].strip()

            results.append((code, name, link))

    return results


# =========================
# 詳細取得
# =========================
def get_detail(link):
    res = requests.get(link)
    soup = BeautifulSoup(res.text, "html.parser")

    text = soup.get_text()

    sales = extract_percent(text, "売上")
    profit = extract_percent(text, "営業利益")
    progress = extract_percent(text, "進捗")
    per = extract_number(text, "PER")

    # ★追加：EPS成長
    eps_growth = extract_percent(text, "EPS")

    return sales, profit, progress, per, eps_growth


# =========================
# 抽出系
# =========================
def extract_percent(text, keyword):
    m = re.search(keyword + r".*?([\+\-]?\d+\.?\d*)％", text)
    return float(m.group(1)) if m else None


def extract_number(text, keyword):
    m = re.search(keyword + r".*?(\d+\.?\d*)", text)
    return float(m.group(1)) if m else None


# =========================
# 評価ロジック
# =========================
def evaluate(sales, profit, progress, per, eps_growth):
    score = 0

    # 売上・利益成長
    if sales and sales > 10:
        score += 1
    if profit and profit > 10:
        score += 1

    # 鈍化（最重要）
    if profit and profit < 5:
        score -= 1

    # 進捗率
    if progress:
        if progress > 70:
            score += 1
        elif progress < 40:
            score -= 1

    # PER
    if per:
        if per > 40:
            score -= 1
        elif per < 20:
            score += 1

    # ★PEG（EPS成長から算出）
    if eps_growth and per:
        peg = per / eps_growth if eps_growth != 0 else 999
        if peg < 1:
            score += 1
        elif peg > 2:
            score -= 1

    # 判定
    if score >= 3:
        return "◎"
    elif score == 2:
        return "○"
    elif score == 1:
        return "△"
    else:
        return "×"


# =========================
# メイン
# =========================
def main():
    if not WEBHOOK_URL:
        raise ValueError("DISCORD_WEBHOOK 未設定")

    stocks = get_kabutan_list()

    if not stocks:
        send("📊 本日決算なし")
        return

    messages = []

    for code, name, link in stocks[:10]:
        try:
            sales, profit, progress, per, eps_growth = get_detail(link)
            eval_mark = evaluate(sales, profit, progress, per, eps_growth)

            msg = f"{eval_mark} {code} {name}\n"
            msg += f"売上:{sales}% 利益:{profit}% 進捗:{progress}% PER:{per} EPS成長:{eps_growth}%"

            messages.append(msg)

        except Exception:
            messages.append(f"× {code} {name}（取得失敗）")

    send("📊 決算分析\n\n" + "\n\n".join(messages))


# =========================
# Discord送信
# =========================
def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg})


if __name__ == "__main__":
    main()
