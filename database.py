"""
cctv_monitor - 桃園機場 CCTV 串流監控系統
Database Module (SQLite)
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional
from contextlib import contextmanager

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """取得資料庫連線"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_cursor():
    """上下文管理器：自動管理連線"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """初始化資料庫結構"""
    with get_cursor() as cursor:
        # stream_logs 資料表：記錄每台伺服器的串流數量
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stream_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                server_ip TEXT NOT NULL,
                server_name TEXT NOT NULL,
                stream_count INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 維修記錄資料表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT UNIQUE NOT NULL,
                report_date TEXT NOT NULL,
                completion_date TEXT,
                system_category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 建立索引加速查詢
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stream_logs_timestamp 
            ON stream_logs(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stream_logs_server 
            ON stream_logs(server_ip)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_maintenance_status 
            ON maintenance_records(status)
        """)

        print("✅ 資料庫初始化完成")


def insert_stream_log(timestamp: str, server_ip: str, server_name: str, stream_count: int):
    """寫入一筆串流記錄"""
    with get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO stream_logs (timestamp, server_ip, server_name, stream_count)
            VALUES (?, ?, ?, ?)
        """, (timestamp, server_ip, server_name, stream_count))


def insert_maintenance_record(
    case_number: str,
    report_date: str,
    system_category: str,
    completion_date: Optional[str] = None,
    status: str = "pending",
    description: Optional[str] = None
):
    """寫入維修記錄"""
    with get_cursor() as cursor:
        cursor.execute("""
            INSERT INTO maintenance_records 
            (case_number, report_date, completion_date, system_category, status, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (case_number, report_date, completion_date, system_category, status, description))


def update_maintenance_record(
    case_number: str,
    completion_date: Optional[str] = None,
    status: Optional[str] = None,
    description: Optional[str] = None
):
    """更新維修記錄"""
    with get_cursor() as cursor:
        updates = []
        params = []
        if completion_date:
            updates.append("completion_date = ?")
            params.append(completion_date)
        if status:
            updates.append("status = ?")
            params.append(status)
        if description:
            updates.append("description = ?")
            params.append(description)
        updates.append("updated_at = CURRENT_TIMESTAMP")
        
        params.append(case_number)
        cursor.execute(f"""
            UPDATE maintenance_records 
            SET {', '.join(updates)}
            WHERE case_number = ?
        """, params)


def cleanup_old_records(days: int = 90):
    """清理超過指定天數的串流記錄"""
    with get_cursor() as cursor:
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("DELETE FROM stream_logs WHERE timestamp < ?", (cutoff_date,))
        deleted = cursor.rowcount
        print(f"🗑️ 已刪除 {deleted} 筆超過 {days} 天的舊記錄")
        return deleted


def get_recent_logs(limit: int = 100):
    """取得最近的串流記錄"""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT * FROM stream_logs 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()


def get_server_summary():
    """取得各伺服器最新串流統計"""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT server_ip, server_name, 
                   MAX(stream_count) as max_streams,
                   MIN(stream_count) as min_streams,
                   AVG(stream_count) as avg_streams
            FROM stream_logs 
            WHERE timestamp >= date('now', '-1 day')
            GROUP BY server_ip
        """)
        return cursor.fetchall()


def get_monthly_stats(year: int, month: int) -> dict:
    """取得指定月份的串流統計"""
    with get_cursor() as cursor:
        # 計算該月的開始和結束時間
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{month+1:02d}-01"
        
        # 1. 總記錄數 (成功抓取次數)
        cursor.execute("""
            SELECT COUNT(DISTINCT timestamp) as fetch_count
            FROM stream_logs 
            WHERE timestamp >= ? AND timestamp < ?
        """, (start_date, end_date))
        fetch_count = cursor.fetchone()['fetch_count']
        
        # 2. 計算可用率 (假設每 10 分鐘應該抓一次)
        # 一個月大約多少個 10 分鐘區間
        total_expected = cursor.execute("""
            SELECT (julianday(?) - julianday(?)) * 24 * 6 as intervals
        """, (end_date, start_date)).fetchone()['intervals']
        availability = (fetch_count / total_expected * 100) if total_expected > 0 else 0
        
        # 3. 平均串流負載 (所有伺服器的平均)
        cursor.execute("""
            SELECT AVG(stream_count) as avg_load,
                   SUM(stream_count) as total_streams
            FROM stream_logs 
            WHERE timestamp >= ? AND timestamp < ?
        """, (start_date, end_date))
        result = cursor.fetchone()
        avg_load = result['avg_load'] or 0
        total_streams = result['total_streams'] or 0
        
        # 4. 各伺服器平均串流 (用於 TOP 3)
        cursor.execute("""
            SELECT server_name, AVG(stream_count) as avg_count
            FROM stream_logs 
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY server_name
            ORDER BY avg_count DESC
            LIMIT 3
        """, (start_date, end_date))
        top_servers = cursor.fetchall()
        
        # 5. 總案件數 (視為抓取次數)
        cursor.execute("""
            SELECT COUNT(DISTINCT case_number) as total_cases
            FROM maintenance_records
            WHERE report_date >= ? AND report_date < ?
        """, (start_date, end_date))
        
        return {
            'year': year,
            'month': month,
            'fetch_count': fetch_count,
            'availability': availability,
            'avg_load': avg_load,
            'total_streams': total_streams,
            'top_servers': top_servers,
            'total_expected': int(total_expected)
        }


def get_quarterly_stats(year: int, quarter: int) -> dict:
    """取得指定季度的串流統計"""
    month_map = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    start_month, end_month = month_map[quarter]
    
    with get_cursor() as cursor:
        start_date = f"{year}-{start_month:02d}-01"
        if end_month == 12:
            end_date = f"{year+1}-01-01"
        else:
            end_date = f"{year}-{end_month+1:02d}-01"
        
        # 1. 總記錄數
        cursor.execute("""
            SELECT COUNT(DISTINCT timestamp) as fetch_count
            FROM stream_logs 
            WHERE timestamp >= ? AND timestamp < ?
        """, (start_date, end_date))
        fetch_count = cursor.fetchone()['fetch_count']
        
        # 2. 可用率
        total_expected = cursor.execute("""
            SELECT (julianday(?) - julianday(?)) * 24 * 6 as intervals
        """, (end_date, start_date)).fetchone()['intervals']
        availability = (fetch_count / total_expected * 100) if total_expected > 0 else 0
        
        # 3. 平均串流負載
        cursor.execute("""
            SELECT AVG(stream_count) as avg_load,
                   SUM(stream_count) as total_streams
            FROM stream_logs 
            WHERE timestamp >= ? AND timestamp < ?
        """, (start_date, end_date))
        result = cursor.fetchone()
        avg_load = result['avg_load'] or 0
        total_streams = result['total_streams'] or 0
        
        # 4. TOP 3 伺服器
        cursor.execute("""
            SELECT server_name, AVG(stream_count) as avg_count
            FROM stream_logs 
            WHERE timestamp >= ? AND timestamp < ?
            GROUP BY server_name
            ORDER BY avg_count DESC
            LIMIT 3
        """, (start_date, end_date))
        top_servers = cursor.fetchall()
        
        return {
            'year': year,
            'quarter': quarter,
            'fetch_count': fetch_count,
            'availability': availability,
            'avg_load': avg_load,
            'total_streams': total_streams,
            'top_servers': top_servers,
            'total_expected': int(total_expected),
            'months': list(range(start_month, end_month + 1))
        }


def get_available_periods() -> list:
    """取得資料庫中有資料的年份/季度列表"""
    with get_cursor() as cursor:
        cursor.execute("""
            SELECT DISTINCT 
                strftime('%Y', timestamp) as year,
                CASE 
                    WHEN CAST(strftime('%m', timestamp) AS INTEGER) BETWEEN 1 AND 3 THEN 'Q1'
                    WHEN CAST(strftime('%m', timestamp) AS INTEGER) BETWEEN 4 AND 6 THEN 'Q2'
                    WHEN CAST(strftime('%m', timestamp) AS INTEGER) BETWEEN 7 AND 9 THEN 'Q3'
                    ELSE 'Q4'
                END as quarter
            FROM stream_logs
            ORDER BY year DESC, quarter DESC
        """)
        return cursor.fetchall()


if __name__ == "__main__":
    init_database()
