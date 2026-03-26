# .github/workflows/kabutan_screening.yml
name: Kabutan 決算通知

# 手動実行と毎日定時実行
on:
  workflow_dispatch:
  schedule:
    - cron: '0 0 0 * * *'  # UTC 0時 → JST 9時に変更する場合は調整可

env:
  FORCE_JAVASCRIPT_ACTIONS_TO_NODE24: true  # Node.js 24 強制
  LINE_TOKEN: ${{ secrets.LINE_TOKEN }}      # GitHub Secrets に登録済み

jobs:
  screening:
    runs-on: ubuntu-latest

    steps:
      - name: リポジトリをチェックアウト
        uses: actions/checkout@v3

      - name: Python セットアップ
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: 必要ライブラリをインストール
        run: |
          python -m pip install --upgrade pip
          pip install requests beautifulsoup4 yfinance pytz

      - name: スクリーニングスクリプト実行
        run: |
          python kabutan_final_full_run_notify.py
