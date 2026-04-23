#!/usr/bin/env python3
"""
cctv_monitor - PDF 報表產生器
產生月報/季報的專業 PDF 文件
"""

import io
from datetime import datetime
from typing import Optional, List, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from database import get_monthly_stats, get_quarterly_stats, get_utilization_status

# 註冊中文字體 (使用專案內建的 STXIHEI 字型)
import os as _os
FONT_DIR = _os.path.dirname(_os.path.abspath(__file__)) + "/fonts"
CHINESE_FONT_PATH = _os.path.join(FONT_DIR, "STXIHEI.ttf")
CHINESE_FONT_NAME = "STHeitiLight"

try:
    pdfmetrics.registerFont(TTFont(CHINESE_FONT_NAME, CHINESE_FONT_PATH))
except Exception as e:
    print(f"⚠️ 中文字體註冊失敗: {e}")
    CHINESE_FONT_NAME = "Helvetica"  # Fallback


def generate_pdf_report(
    year: int,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    output_path: Optional[str] = None
) -> bytes:
    """
    產生 PDF 報表
    
    Args:
        year: 年份
        month: 月份 (若為 None 則產生季報)
        quarter: 季度 (若 month 為 None)
        output_path: 輸出路徑 (若為 None則回傳 bytes)
    
    Returns:
        PDF 檔案的 bytes
    """
    
    # 決定報表類型
    if month:
        title = f"{year} 年 {month} 月 串流使用報告"
        stats = get_monthly_stats(year, month)
    elif quarter:
        title = f"{year} 年 第 {quarter} 季 串流使用報告"
        stats = get_quarterly_stats(year, quarter)
    else:
        raise ValueError("必須指定 month 或 quarter")
    
    # 建立 PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # 取得樣式
    styles = getSampleStyleSheet()
    
    # 自訂樣式 (使用中文字體)
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=CHINESE_FONT_NAME,
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#1a1a2e')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontName=CHINESE_FONT_NAME,
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.grey,
        spaceAfter=30
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=CHINESE_FONT_NAME,
        fontSize=14,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#16213e')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=CHINESE_FONT_NAME,
        fontSize=10,
        alignment=TA_LEFT
    )
    
    # 建立元素
    elements = []
    
    # 標題
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(f"產生時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", subtitle_style))
    elements.append(Spacer(1, 10*mm))
    
    # 系統狀態指標
    elements.append(Paragraph("📊 系統狀態指標", heading_style))
    
    # 使用率計算
    current_streams = stats.get('current_streams', 0) or 0
    util_status = get_utilization_status(current_streams)
    
    # 根據使用率狀態設定顏色與標籤
    if util_status['label'] == "低度負載":
        status_color = colors.HexColor('#4CAF50')
    elif util_status['label'] == "運作順暢":
        status_color = colors.HexColor('#2196F3')
    elif util_status['label'] == "正常負載":
        status_color = colors.HexColor('#00D4AA')
    elif util_status['label'] == "忙碌警示":
        status_color = colors.HexColor('#FF9800')
    else:
        status_color = colors.HexColor('#f44336')
    
    status_data = [
        ["指標項目", "數值", "狀態"],
        ["系統使用率", f"{util_status['utilization']:.2f}%", util_status['label']],
        ["平均串流負載", f"{stats['avg_load']:.1f}", "📊 穩定"],
        ["總串流數", f"{stats['total_streams']:,}", "📹 正常"],
        ["目前串流", f"{current_streams:.0f} / 700", f"{util_status['icon']} {util_status['label']}"],
    ]
    
    status_table = Table(status_data, colWidths=[100, 120, 100])
    status_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT_NAME),
        ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT_NAME),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8f5e9')),  # 使用率列高亮
        ('TEXTCOLOR', (2, 1), (2, 1), status_color),  # 狀態列著色
        ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#f0f2f6')]),
    ]))
    elements.append(status_table)
    elements.append(Spacer(1, 10*mm))
    
    # 高負載排行
    elements.append(Paragraph("🔥 高負載排行 TOP 3", heading_style))
    
    if stats['top_servers']:
        rank_data = [["排名", "伺服器", "平均串流數"]]
        for i, server in enumerate(stats['top_servers'][:3], 1):
            rank_data.append([
                f"第 {i} 名",
                server['server_name'].strip(),
                f"{server['avg_count']:.1f}"
            ])
        
        rank_table = Table(rank_data, colWidths=[80, 120, 100])
        rank_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), CHINESE_FONT_NAME),
            ('FONTNAME', (0, 1), (-1, -1), CHINESE_FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fff3cd'), colors.HexColor('#ffeaa7'), colors.HexColor('#d4a574')]),
        ]))
        elements.append(rank_table)
    else:
        elements.append(Paragraph("⚠️ 暫無排名資料", normal_style))
    
    elements.append(Spacer(1, 15*mm))
    
    # 報表說明
    elements.append(Paragraph("📋 指標說明", heading_style))
    
    notes = [
        "• <b>系統使用率</b>：目前串流數 ÷ 700 容量 (7台×100ch)，反映系統負載狀態",
        "• <b>使用率分級</b>：0-20%低度負載 / 21-40%運作順暢 / 41-60%正常負載 / 61-80%忙碌警示 / 81-100%滿載臨界",
        "• <b>平均串流負載</b>：該期間所有伺服器的平均串流數",
        "• <b>高負載排行</b>：平均串流數最高的前三名伺服器，建議優先關注",
    ]
    
    for note in notes:
        elements.append(Paragraph(note, normal_style))
        elements.append(Spacer(1, 3*mm))
    
    elements.append(Spacer(1, 10*mm))
    
    # 頁尾
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName=CHINESE_FONT_NAME,
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    elements.append(Paragraph("帆宣系統科技 廣播系統串流使用報告", footer_style))
    
    # 建立 PDF
    doc.build(elements)
    
    # 取得 PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    # 如果有指定輸出路徑，寫入檔案
    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
    
    return pdf_bytes


def generate_quarterly_pdf(year: int, quarter: int, output_path: Optional[str] = None) -> bytes:
    """產生季度 PDF 報表"""
    return generate_pdf_report(year=year, quarter=quarter, output_path=output_path)


def generate_monthly_pdf(year: int, month: int, output_path: Optional[str] = None) -> bytes:
    """產生月度 PDF 報表"""
    return generate_pdf_report(year=year, month=month, output_path=output_path)


if __name__ == "__main__":
    # 測試產生 PDF
    import sys
    sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
    
    print("測試產生 2026 Q1 季度報表...")
    pdf = generate_quarterly_pdf(2026, 1)
    print(f"✅ PDF 產生成功，大小: {len(pdf):,} bytes")
