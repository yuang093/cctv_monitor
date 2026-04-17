#!/usr/bin/env python3
"""
產生串流測試假資料
用於預覽串流使用分析報告 UI
"""

import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_database, insert_stream_log

# 伺服器設定 (與實際 CCTV 系統一致)
SERVERS = [
    ("10.23.200.1", "BC-1"),
    ("10.23.200.2", "BC-2"),
    ("10.23.200.3", "BC-3"),
    ("10.23.200.4", "BC-4"),
    ("10.23.200.5", "BC-5"),
    ("10.23.200.6", "BC-6"),
    ("10.23.200.7", "BC-7"),
]

# 基礎負載範圍 (每台伺服器的常態)
BASE_LOADS = {
    "BC-1": (8, 12),    # 10左右
    "BC-2": (14, 18),   # 16左右
    "BC-3": (13, 17),   # 15左右
    "BC-4": (10, 14),   # 12左右
    "BC-5": (13, 17),   # 15左右
    "BC-6": (22, 26),   # 24左右 (最忙碌)
    "BC-7": (11, 15),   # 13左右
}

def generate_dummy_data():
    print("=" * 50)
    print("🧪 產生串流測試假資料")
    print("=" * 50)
    
    # 初始化資料庫
    init_database()
    
    # 產生 2025 Q4 ~ 2026 Q2 的假資料
    periods = [
        ("2025", 4),  # 2025 Q4
        ("2026", 1),  # 2026 Q1
        ("2026", 2),  # 2026 Q2
    ]
    
    total_records = 0
    
    for year, quarter in periods:
        print(f"\n📅 {year} Q{quarter}")
        
        # 決定季度日期範圍
        if year == "2025" and quarter == 4:
            start_date = datetime(2025, 10, 1)
            end_date = datetime(2025, 12, 31)
        elif year == "2026" and quarter == 1:
            start_date = datetime(2026, 1, 1)
            end_date = datetime(2026, 3, 31)
        else:  # 2026 Q2
            start_date = datetime(2026, 4, 1)
            end_date = datetime(2026, 6, 30)
        
        # 每 10 分鐘一筆 (每天 144 筆, 每季約 13,000 筆)
        # 為了不要太多資料，我們改成每小時一筆
        current = start_date.replace(minute=0, second=0)
        
        records_this_quarter = 0
        fetch_failures = 0  # 模擬少許失敗 (5% 失敗率)
        
        while current <= end_date:
            # 5% 機率-fetch 失敗 (這筆不寫入, 代表系統可用率)
            if random.random() < 0.05:
                fetch_failures += 1
                current += timedelta(hours=1)
                continue
            
            timestamp_str = current.strftime("%Y-%m-%d %H:%M:%S")
            
            for ip, name in SERVERS:
                # 根據伺服器特性產生隨機負載
                min_load, max_load = BASE_LOADS[name]
                # 加入一些時間變化 (白天高一點，晚上低一點)
                hour_factor = 1.0 + 0.2 * (1 - abs(current.hour - 12) / 6)
                stream_count = int(random.randint(min_load, max_load) * hour_factor)
                
                insert_stream_log(
                    timestamp=timestamp_str,
                    server_ip=ip,
                    server_name=name,
                    stream_count=stream_count
                )
                records_this_quarter += 1
            
            current += timedelta(hours=1)
        
        total_records += records_this_quarter
        
        # 計算這個季度的可用率
        expected_records = int((end_date - start_date).total_seconds() / 3600) * len(SERVERS)
        availability = (records_this_quarter / expected_records) * 100 if expected_records > 0 else 0
        
        print(f"  📊 記錄數: {records_this_quarter:,}")
        print(f"  ❌ 失敗次數: {fetch_failures}")
        print(f"  📈 可用率: {availability:.1f}%")
    
    print(f"\n✅ 完成！共產生 {total_records:,} 筆記錄")

if __name__ == "__main__":
    generate_dummy_data()
