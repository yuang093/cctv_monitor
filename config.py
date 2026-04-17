"""
cctv_monitor - 桃園機場 CCTV 串流監控系統
Configuration Module
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv(Path(__file__).parent / ".env")

# Project paths
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "cctv_monitor.db"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Crawler settings
CCTV_URL = "https://cctv.taoyuan-airport.com/v2/bcstat"
FETCH_INTERVAL_MINUTES = 10  # 爬蟲抓取間隔
DATA_RETENTION_DAYS = 90      # 資料保留天數

# LINE Notify settings
LINE_NOTIFY_TOKEN = os.getenv("LINE_NOTIFY_TOKEN", "")

# Telegram settings (從環境變數讀取)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# Alert settings
ALERT_ZERO_STREAM = True       # 串流為 0 時警示
ALERT_SPIKE_THRESHOLD = 1.5   # 異常飆升閾值（相較歷史平均）
ALERT_MIN_HISTORY_HOURS = 2   # 歷史資料最少小時數

# Log file path
LOG_FILE = LOG_DIR / "crawler.log"
