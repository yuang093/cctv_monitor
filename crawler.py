#!/usr/bin/env python3
"""
cctv_monitor - 桃園機場 CCTV 串流監控系統
Main Crawler Script v2 (增強錯誤處理)
"""

import re
import sys
import time
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

import schedule

from config import (
    CCTV_URL, FETCH_INTERVAL_MINUTES, DATA_RETENTION_DAYS, 
    LINE_NOTIFY_TOKEN, LOG_FILE, DB_PATH,
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED,
    ALERT_ZERO_STREAM, ALERT_SPIKE_THRESHOLD, ALERT_MIN_HISTORY_HOURS
)
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

# ========== 錯誤處理常數 ==========
MAX_RETRIES = 3
RETRY_DELAY_BASE = 5  # 秒（指數退避基數）
REQUEST_TIMEOUT = 30   # 請求超時秒數
HEALTH_CHECK_INTERVAL = 6  # 健康檢查間隔（小時）


def send_notify(message: str, channel: str = "LINE") -> bool:
    """發送通知（LINE 或 Telegram）"""
    if channel == "LINE":
        return send_line_notify(message)
    elif channel == "TG" and TELEGRAM_ENABLED:
        return send_telegram(message)
    return False


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


def send_telegram(message: str) -> bool:
    """發送 Telegram 通知"""
    if not TELEGRAM_ENABLED:
        logger.debug("⚠️ Telegram 未啟用")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            logger.info("✅ Telegram 通知發送成功")
            return True
        else:
            logger.error(f"❌ Telegram 發送失敗: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Telegram 錯誤: {e}")
        return False


def health_check() -> bool:
    """健康檢查：驗證資料庫和磁碟空間"""
    try:
        # 檢查資料庫檔案是否存在且可讀
        if not DB_PATH.exists():
            logger.error(f"❌ 資料庫檔案不存在: {DB_PATH}")
            return False
        
        # 檢查磁碟空間（預估需要 > 100MB）
        import shutil
        stat = shutil.disk_usage("/")
        if stat.free < 100 * 1024 * 1024:
            logger.error(f"❌ 磁碟空間不足: {stat.free / (1024**3):.1f} GB")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ 健康檢查失敗: {e}")
        return False


def fetch_cctv_data_with_retry() -> Optional[str]:
    """抓取 CCTV 網頁資料（含重試機制）"""
    last_error = None
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(f"🌐 第 {attempt} 次嘗試抓取 CCTV 資料...")
            
            response = requests.get(CCTV_URL, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # 驗證回應內容不為空
            if not response.text.strip():
                logger.error("❌ 回應內容為空")
                last_error = "回應內容為空"
                continue
            
            # 驗證是否為預期的資料格式
            if "Server:" not in response.text:
                logger.error("❌ 回應格式不符合預期")
                last_error = "回應格式不符"
                continue
            
            logger.info(f"✅ 第 {attempt} 次嘗試成功")
            return response.text
            
        except requests.exceptions.Timeout:
            logger.error(f"❌ 第 {attempt} 次嘗試：連線逾時 ({REQUEST_TIMEOUT}s)")
            last_error = "連線逾時"
        except requests.exceptions.ConnectionError as e:
            logger.error(f"❌ 第 {attempt} 次嘗試：連線錯誤 - {e}")
            last_error = "連線錯誤"
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ 第 {attempt} 次嘗試：HTTP 錯誤 - {e}")
            last_error = f"HTTP {e.response.status_code}"
        except Exception as e:
            logger.error(f"❌ 第 {attempt} 次嘗試：未知錯誤 - {e}")
            last_error = str(e)
        
        # 指數退避等待
        if attempt < MAX_RETRIES:
            wait_time = RETRY_DELAY_BASE * (2 ** (attempt - 1))
            logger.info(f"⏳ 等待 {wait_time} 秒後重試...")
            time.sleep(wait_time)
    
    # 所有嘗試都失敗
    error_msg = f"🚨 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] CCTV 爬蟲失敗\n\n嘗試 {MAX_RETRIES} 次皆失敗\n最後錯誤: {last_error}"
    logger.error(f"❌ 最終失敗: {last_error}")
    send_notify(error_msg)
    return None


def parse_cctv_data(content: str) -> List[Dict]:
    """解析 CCTV 資料（含驗證）"""
    if not content:
        return []
    
    server_pattern = r"Server:\s*([\d.]+)\s*\(([^)]+)\)"
    channels_pattern = r"Running Channels:\s*(\d+)"
    
    servers = []
    current_server = None
    line_count = 0
    
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        line_count += 1
        
        # 匹配伺服器
        server_match = re.match(server_pattern, line)
        if server_match:
            if current_server:
                servers.append(current_server)
            current_server = {
                "ip": server_match.group(1),
                "name": server_match.group(2).strip(),
                "streams": 0
            }
            continue
        
        # 匹配串流數量
        channels_match = re.match(channels_pattern, line)
        if channels_match and current_server:
            try:
                current_server["streams"] = int(channels_match.group(1))
            except ValueError:
                logger.warning(f"⚠️ 無法解析串流數: {channels_match.group(1)}")
    
    if current_server:
        servers.append(current_server)
    
    # 驗證解析結果
    if not servers:
        logger.error("❌ 無法解析到任何伺服器")
    elif len(servers) < 7:
        logger.warning(f"⚠️ 解析到的伺服器數量不足: {len(servers)}/7")
    
    logger.info(f"📊 解析完成：{len(servers)} 台伺服器 ({line_count} 行文字)")
    return servers


def check_anomalies(servers: List[Dict], previous_state: Optional[dict] = None) -> List[str]:
    """檢查異常並回傳警告訊息"""
    alerts = []
    
    for server in servers:
        # 串流為 0 的異常
        if ALERT_ZERO_STREAM and server["streams"] == 0:
            alerts.append(f"⚠️ <code>{server['name']}</code> 串流為 0！")
        
        # 串流異常飆升（相較歷史平均超過閾值）
        if previous_state and server["name"] in previous_state:
            prev_avg = previous_state[server["name"]]
            if prev_avg > 0 and server["streams"] > prev_avg * ALERT_SPIKE_THRESHOLD:
                alerts.append(f"📈 <code>{server['name']}</code> 串流異常飆升: {prev_avg:.0f} → {server['streams']}")
    
    return alerts


def get_previous_state() -> Optional[dict]:
    """取得各伺服器上一個時間點的平均串流（用於異常比較）"""
    try:
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT server_name, AVG(stream_count) as avg_count
            FROM stream_logs
            WHERE timestamp >= datetime('now', '-2 hours')
              AND timestamp < datetime('now', '-1 hour')
            GROUP BY server_name
        """)
        
        state = {row[0].strip(): row[1] for row in cursor.fetchall()}
        conn.close()
        
        return state if state else None
    except Exception as e:
        logger.warning(f"⚠️ 無法取得歷史狀態: {e}")
        return None


def run_crawler_job():
    """執行一次爬蟲任務（增強錯誤處理）"""
    try:
        logger.info("=" * 50)
        logger.info(f"🔍 開始抓取 CCTV 資料 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 健康檢查（每 6 小時一次）
        if not hasattr(run_crawler_job, '_last_health_check'):
            run_crawler_job._last_health_check = 0
        
        current_hour = datetime.now().hour
        if current_hour % 6 == 0 and current_hour != run_crawler_job._last_health_check:
            run_crawler_job._last_health_check = current_hour
            if not health_check():
                send_notify("🚨 CCTV 監控系統健康檢查失敗！")
        
        # 取得歷史狀態（用於異常比較）
        previous_state = get_previous_state()
        
        # 抓取資料
        content = fetch_cctv_data_with_retry()
        if not content:
            logger.error("❌ 無法取得資料，任務結束")
            return
        
        # 解析資料
        servers = parse_cctv_data(content)
        if not servers:
            send_notify(f"🚨 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] CCTV 資料解析失敗！")
            return
        
        # 寫入資料庫
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_streams = 0
        success_count = 0
        
        for server in servers:
            try:
                insert_stream_log(
                    timestamp=timestamp,
                    server_ip=server["ip"],
                    server_name=server["name"],
                    stream_count=server["streams"]
                )
                success_count += 1
                total_streams += server["streams"]
                logger.info(f"  ✅ {server['name']}: {server['streams']} streams")
            except Exception as e:
                logger.error(f"  ❌ 寫入失敗 {server['name']}: {e}")
        
        logger.info(f"📈 總串流數: {total_streams} (成功率: {success_count}/{len(servers)})")
        
        # 檢查異常
        alerts = check_anomalies(servers, previous_state)
        if alerts:
            alert_msg = f"🚨 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] CCTV 監控異常\n\n" + "\n".join(alerts)
            logger.warning("\n".join(alerts))
            send_notify(alert_msg)
        
        # 檢查是否需要清理舊資料（每天凌晨執行一次）
        if current_hour == 0:
            logger.info("🧹 執行每日資料清理...")
            try:
                cleanup_old_records(DATA_RETENTION_DAYS)
            except Exception as e:
                logger.error(f"❌ 清理舊資料失敗: {e}")
        
        logger.info(f"✅ 任務完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        raise
    except Exception as e:
        logger.exception(f"❌ 任務執行錯誤: {e}")
        send_notify(f"🚨 [{datetime.now().strftime('%Y-%m-%d %H:%M')}] CCTV 爬蟲異常: {e}")


def main():
    """主程式（含自動重啟機制）"""
    restart_count = 0
    max_restarts_per_hour = 5
    
    while True:
        try:
            print("=" * 50)
            print("🚨 桃園機場 CCTV 串流監控系統 v2")
            print("=" * 50)
            
            # 初始化資料庫
            logger.info("初始化資料庫...")
            try:
                init_database()
            except Exception as e:
                logger.error(f"❌ 資料庫初始化失敗: {e}")
                send_notify(f"🚨 資料庫初始化失敗: {e}")
                time.sleep(60)
                continue
            
            # 立即執行一次
            logger.info("執行初次抓取...")
            run_crawler_job()
            
            # 設定排程
            logger.info(f"⏰ 設定排程：每 {FETCH_INTERVAL_MINUTES} 分鐘抓取一次")
            schedule.every(FETCH_INTERVAL_MINUTES).minutes.do(run_crawler_job)
            
            # 持續執行
            logger.info("🔄 開始監控迴圈...")
            restart_count = 0  # 成功啟動後重置計數
            
            while True:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("\n👋 監控系統已停止")
            sys.exit(0)
            
        except Exception as e:
            logger.exception(f"❌ 主程式錯誤: {e}")
            restart_count += 1
            
            if restart_count > max_restarts_per_hour:
                error_msg = f"🚨 CCTV 爬蟲一小時內重啟 {restart_count} 次，已達上限。請檢查系統狀態。"
                logger.error(error_msg)
                send_notify(error_msg)
                time.sleep(3600)  # 等 1 小時再試
            else:
                logger.info(f"⏳ 10 秒後重啟... (今日第 {restart_count} 次)")
                time.sleep(10)


if __name__ == "__main__":
    main()
