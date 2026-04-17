"""
cctv_monitor - 桃園機場 CCTV 串流監控系統
Configuration Module
"""

import os
from pathlib import Path

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

# Log file path
LOG_FILE = LOG_DIR / "crawler.log"
