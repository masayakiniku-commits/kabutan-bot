from datetime import datetime
import os
import requests

# ─ LINE送信用の関数 ─
LINE_TOKEN = os.getenv("xp3qfxCz2ILHsMtWnZbVMRrfnn0R1C1XxkFBrbF69KG26seKKAt7OGE8VUj5NpGcfW0s9rSNY7zXZDHysDxIbTidKov7J/9K033SJ0N+s9Sus+s4U5AnVS8MAmLm1SMXmRzQH/ERO5ogmsneL7NuHwdB04t89/1O/w1cDnyilFU=")  # GitHub Secrets に設定済み
LINE_API = "https://notify-api.line.me/api/notify"

def send_line(message):
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"message": message}
    resp = requests.post(LINE_API, headers=headers, data=data)
    if resp.status_code == 200:
        print("LINE通知成功")
    else:
        print("LINE通知失敗", resp.status_code, resp.text)

# ─ ダミー銘柄で通知テスト ─
def run_screening():
    # 通常は get_codes() で取得するが、テスト用に固定銘柄を使用
    codes = ["9999", "1234", "5678"]  # ダミー銘柄

    results = []
    for c in codes:
        # 評価関数もテスト用に固定値
        rank = "◎"
        score = 100
        results.append((c, rank, score))

    results.sort(key=lambda x: x[2], reverse=True)

    # メッセージ作成
    msg = f"📊 {datetime.today().strftime('%Y-%m-%d')} 決算初動スクリーニング（テスト用）\n"
    for r in results:
        msg += f"{r[0]} {r[1]}({r[2]})\n"

    send_line(msg)

# ─ 実行 ─
if __name__ == "__main__":
    run_screening()
