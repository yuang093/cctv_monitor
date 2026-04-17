#!/usr/bin/env python3
"""
產生測試假資料的腳本
用於預覽維修分析報告 UI
"""

import sys
import os
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_database, insert_maintenance_record

# 系統類別
SYSTEMS = ["廣播系統", "網路設備", "攝影機", "伺服器", "其他"]

# 假資料產生
def generate_dummy_data():
    print("=" * 50)
    print("🧪 產生測試假資料")
    print("=" * 50)
    
    # 初始化資料庫
    init_database()
    
    # 產生 2025 Q4 ~ 2026 Q2 的假資料
    quarters = [
        ("2025", 4),  # 2025 Q4
        ("2026", 1),  # 2026 Q1
        ("2026", 2),  # 2026 Q2 (目前季度)
    ]
    
    total_created = 0
    
    for year, quarter in quarters:
        print(f"\n📅 {year} Q{quarter}")
        
        # 決定該季的天數範圍
        if year == "2025" and quarter == 4:
            start_date = datetime(2025, 10, 1)
            end_date = datetime(2025, 12, 31)
        elif year == "2026" and quarter == 1:
            start_date = datetime(2026, 1, 1)
            end_date = datetime(2026, 3, 31)
        else:  # 2026 Q2
            start_date = datetime(2026, 4, 1)
            end_date = datetime(2026, 6, 30)
        
        # 每季產生 15~25 件案件
        num_cases = random.randint(15, 25)
        
        for i in range(num_cases):
            case_num = f"MNT-{year[2:]}-Q{quarter}-{i+1:03d}"
            
            # 報修日期（季內隨機）
            days_offset = random.randint(0, (end_date - start_date).days)
            report_date = start_date + timedelta(days=days_offset)
            
            # 70% 完成率
            is_completed = random.random() < 0.7
            
            if is_completed:
                # 維修天數 1~30 天
                repair_days = random.randint(1, 30)
                completion_date = report_date + timedelta(days=repair_days)
                # 有些案件跨季，確保 completion_date 不超過 end_date
                if completion_date > end_date:
                    completion_date = end_date
            else:
                completion_date = None
            
            # 隨機選擇系統
            system = random.choice(SYSTEMS)
            
            # 描述
            descriptions = {
                "廣播系統": ["喇叭無聲", "廣播主機異常", "背景音樂播放異常"],
                "網路設備": ["網段連線中斷", "交換器故障", "頻寬不足"],
                "攝影機": ["影像模糊", "無訊號", "球機控制失效", "夜視功能異常"],
                "伺服器": ["儲存空間不足", "服務無回應", "備份失敗"],
                "其他": ["電源供應不穩", "線路老化", "設備過熱"]
            }
            description = random.choice(descriptions.get(system, ["一般維修"]))
            
            # 寫入資料庫
            insert_maintenance_record(
                case_number=case_num,
                report_date=report_date.strftime("%Y-%m-%d"),
                completion_date=completion_date.strftime("%Y-%m-%d") if completion_date else None,
                system_category=system,
                status="completed" if completion_date else "pending",
                description=f"{description} (測試資料)"
            )
            
            status = "✅" if completion_date else "⏳"
            print(f"  {status} {case_num} | {system} | {report_date.strftime('%m/%d')}", end="")
            if completion_date:
                print(f" ~ {completion_date.strftime('%m/%d')} ({repair_days}天)")
            else:
                print(" (未結案)")
            
            total_created += 1
    
    print(f"\n✅ 完成！共產生 {total_created} 筆測試資料")

if __name__ == "__main__":
    generate_dummy_data()
