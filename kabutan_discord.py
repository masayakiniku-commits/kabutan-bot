import requests
from bs4 import BeautifulSoup
import datetime
import os

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

def get_kabutan():
    url = "https://kabutan.jp/news/marketnews/?category=2"
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    items = soup.select(".news_list li")
    results = []

    today = datetime.datetime.now().strftime("%m/%d")

    for item in items:
        text = item.get_text()
        if today in text:
            title = item.find("a").text

            # 銘柄コード抽出
            code = ""
            import re
            m = re.search(r"\((\d{4}[A-Z]?)\)", title)
            if m:
                code = m.group(1)

            # 会社名（コード前）
            name = title.split("(")[0].strip()

            results.append(f"{code} {name}")

    return list(set(results))


def send_discord(message):
    requests.post(WEBHOOK_URL, json={"content": message})


def main():
    stocks = get_kabutan()

    now = datetime.datetime.now()
    weekday = now.weekday()  # 月0

    # 平日
    if weekday < 5:
        if stocks:
            msg = "📊 本日の決算銘柄\n" + "\n".join(stocks)
        else:
            msg = "📊 本日決算なし"
        send_discord(msg)

    # 土日 → まとめ（簡易）
    else:
        msg = "📊 今週の決算（簡易）\n※平日データ参照"
        send_discord(msg)


if __name__ == "__main__":
    main()
