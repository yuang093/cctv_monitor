#!/usr/bin/env python3
"""
測試腳本：驗證爬蟲邏輯
"""

import sys
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')

from database import init_database, get_recent_logs, get_server_summary, cleanup_old_records

def main():
    print("=" * 50)
    print("🧪 CCTV 監控系統測試")
    print("=" * 50)
    
    # 初始化資料庫
    print("\n1️⃣ 初始化資料庫...")
    init_database()
    
    # 顯示最近記錄
    print("\n2️⃣ 最近串流記錄 (前10筆):")
    logs = get_recent_logs(limit=10)
    if logs:
        for log in logs:
            print(f"  {log['timestamp']} | {log['server_name']} | {log['stream_count']} streams")
    else:
        print("  (尚無資料)")
    
    # 顯示伺服器統計
    print("\n3️⃣ 伺服器統計 (過去24小時):")
    summary = get_server_summary()
    if summary:
        for row in summary:
            print(f"  {row['server_name']} | 平均: {row['avg_streams']:.1f} | 範圍: {row['min_streams']}-{row['max_streams']}")
    else:
        print("  (尚無資料)")
    
    # 測試清理功能
    print("\n4️⃣ 測試清理功能 (保留90天)...")
    cleanup_old_records(90)
    
    print("\n✅ 測試完成!")

if __name__ == "__main__":
    main()
