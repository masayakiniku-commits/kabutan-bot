import os
import requests

LINE_TOKEN = os.getenv("AT8/sZVSAvpq9yHtgu5cuvNlQw1mvJK4byjJM26Svi/g6TI+voMu0em4c950/QpNfW0s9rSNY7zXZDHysDxIbTidKov7J/9K033SJ0N+s9RjCJrdQBzAgVJ3g6CrLcWOyMflb84/qAjeIaBDEzdAfwdB04t89/1O/w1cDnyilFU=")

def send_line(msg):
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"message": msg}
    requests.post(url, headers=headers, data=data)

if __name__ == "__main__":
    send_line("テスト通知：GitHub Actions成功")
