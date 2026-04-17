#!/usr/bin/env python3
"""
cctv_monitor - 桃園機場 CCTV 串流監控系統
Main Crawler Script
"""

import re
import sys
import time
import logging
import requests
from datetime import datetime
from typing import List, Dict, Tuple, Optional

import schedule

from config import CCTV_URL, FETCH_INTERVAL_MINUTES, DATA_RETENTION_DAYS, LINE_NOTIFY_TOKEN, LOG_FILE
from database import init_database, insert_stream_log, cleanup_old_records

# Logging 設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def send_line_notify(message: str) -> bool:
    """發送 LINE Notify 通知"""
    if not LINE_NOTIFY_TOKEN:
        logger.warning("⚠️ LINE_NOTIFY_TOKEN 未設定，略過通知")
        return False
    
    try:
        url = "https://notify-api.line.me/api/notify"
        headers = {"Authorization": f"Bearer {LINE_NOTIFY_TOKEN}"}
        data = {"message": message}
        response = requests.post(url, headers=headers, data=data, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ LINE Notify 發送成功")
            return True
        else:
            logger.error(f"❌ LINE Notify 發送失敗: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ LINE Notify 錯誤: {e}")
        return False


def fetch_cctv_data() -> Optional[str]:
    """抓取 CCTV 網頁資料"""
    try:
        response = requests.get(CCTV_URL, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        logger.error("❌ 連線逾時")
        send_line_notify(f"🚨 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] CCTV 爬蟲連線逾時！")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 抓取失敗: {e}")
        send_line_notify(f"🚨 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] CCTV 爬蟲連線錯誤: {e}")
        return None


def parse_cctv_data(content: str) -> List[Dict]:
    """解析 CCTV 資料"""
    # 伺服器區塊的正則表達式
    server_pattern = r"Server:\s*([\d.]+)\s*\(([^)]+)\)"
    channels_pattern = r"Running Channels:\s*(\d+)"
    
    servers = []
    current_server = None
    
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        
        # 匹配伺服器
        server_match = re.match(server_pattern, line)
        if server_match:
            if current_server:
                servers.append(current_server)
            current_server = {
                "ip": server_match.group(1),
                "name": server_match.group(2),
                "streams": 0
            }
            continue
        
        # 匹配串流數量
        channels_match = re.match(channels_pattern, line)
        if channels_match and current_server:
            current_server["streams"] = int(channels_match.group(1))
    
    if current_server:
        servers.append(current_server)
    
    return servers


def check_anomalies(servers: List[Dict]) -> List[str]:
    """檢查異常並回傳警告訊息"""
    alerts = []
    
    for server in servers:
        if server["streams"] == 0:
            alerts.append(f"⚠️ {server['name']} ({server['ip']}) 串流為 0！")
    
    return alerts


def run_crawler_job():
    """執行一次爬蟲任務"""
    logger.info("=" * 50)
    logger.info(f"🔍 開始抓取 CCTV 資料 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 抓取資料
    content = fetch_cctv_data()
    if not content:
        logger.error("❌ 無法取得資料，任務結束")
        return
    
    # 解析資料
    servers = parse_cctv_data(content)
    logger.info(f"📊 解析到 {len(servers)} 台伺服器")
    
    if not servers:
        logger.warning("⚠️ 未解析到任何伺服器")
        send_line_notify(f"🚨 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] CCTV 資料解析失敗！")
        return
    
    # 寫入資料庫
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_streams = 0
    
    for server in servers:
        insert_stream_log(
            timestamp=timestamp,
            server_ip=server["ip"],
            server_name=server["name"],
            stream_count=server["streams"]
        )
        total_streams += server["streams"]
        logger.info(f"  ✅ {server['name']}: {server['streams']} streams")
    
    logger.info(f"📈 總串流數: {total_streams}")
    
    # 檢查異常
    alerts = check_anomalies(servers)
    if alerts:
        alert_msg = f"🚨 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] CCTV 監控異常\n\n" + "\n".join(alerts)
        logger.warning("\n".join(alerts))
        send_line_notify(alert_msg)
    
    # 檢查是否需要清理舊資料 (每天凌晨執行一次)
    current_hour = datetime.now().hour
    if current_hour == 0:
        logger.info("🧹 執行每日資料清理...")
        cleanup_old_records(DATA_RETENTION_DAYS)
    
    logger.info(f"✅ 任務完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """主程式"""
    print("=" * 50)
    print("🚨 桃園機場 CCTV 串流監控系統")
    print("=" * 50)
    
    # 初始化資料庫
    logger.info("初始化資料庫...")
    init_database()
    
    # 立即執行一次
    logger.info("執行初次抓取...")
    run_crawler_job()
    
    # 設定排程
    logger.info(f"⏰ 設定排程：每 {FETCH_INTERVAL_MINUTES} 分鐘抓取一次")
    schedule.every(FETCH_INTERVAL_MINUTES).minutes.do(run_crawler_job)
    
    # 持續執行
    logger.info("🔄 開始監控迴圈 (按 Ctrl+C 終止)")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n👋 監控系統已停止")
        sys.exit(0)


if __name__ == "__main__":
    main()
