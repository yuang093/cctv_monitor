"""
cctv_monitor - 桃園機場 CCTV 串流監控系統
Streamlit 主程式
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# 加入路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_recent_logs, get_server_summary, get_connection

# 頁面設定
st.set_page_config(
    page_title="桃園機場 CCTV 監控",
    page_icon="📹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 側邊欄
# ============================================================
# Logo 和標題區
st.sidebar.markdown("""
<div style="
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 12px;
    padding: 20px 15px;
    text-align: center;
    margin-bottom: 10px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
">
    <div style="font-size: 48px; margin-bottom: 8px;">📹</div>
    <div style="color: #00D4AA; font-size: 18px; font-weight: bold;">CCTV 監控系統</div>
    <div style="color: #a0a0a0; font-size: 12px;">桃園國際機場</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.divider()

# 深色模式切換
with st.sidebar.expander("⚙️ 顯示設定", expanded=False):
    dark_mode = st.toggle("🌙 深色模式", value=False)

# 應用深色主題
if dark_mode:
    st.markdown("""
    <style>
        body { background-color: #1a1a2e; color: #e0e0e0; }
        .stApp { background-color: #1a1a2e; }
        .stSidebar > div:first-child { background-color: #16213e; }
        div[data-testid="stMetricValue"] { color: #00D4AA; }
        div[data-testid="stMetricLabel"] { color: #a0a0a0; }
        .stTabs [data-baseweb="tab-list"] { background-color: #16213e; }
        .stTabs [data-baseweb="tab"] { color: #a0a0a0; }
        .stTabs [aria-selected="true"] { color: #00D4AA !important; }
        .st-dt { background-color: #16213e; }
        div.st-aggrid { background-color: #1a1a2e; }
    </style>
    """, unsafe_allow_html=True)

# 系統狀態卡片
try:
    import os
    db_path = "/Users/taeyeon093.bot/.openclaw/workspace/cctv_monitor/cctv_monitor.db"
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path) / (1024 * 1024)  # MB
        db_size_str = f"{db_size:.1f} MB"
    else:
        db_size_str = "N/A"
except:
    db_size_str = "N/A"

st.sidebar.markdown(f"""
<div style="
    background: #f8f9fa;
    border-radius: 8px;
    padding: 12px;
    margin: 10px 0;
">
    <div style="color: #666; font-size: 10px; margin-bottom: 5px;">📊 系統狀態</div>
    <div style="display: flex; justify-content: space-between; font-size: 11px;">
        <span>📦 資料庫:</span>
        <span style="color: #00D4AA;">{db_size_str}</span>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 11px;">
        <span>🕐 現在:</span>
        <span style="color: #666;">{datetime.now().strftime('%H:%M:%S')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio(
    "📌 導航",
    ["📊 即時流量", "📋 維修記錄", "📈 串流使用分析報告"],
    captions = ["流量監控與統計", "維修案件管理", "月報/季報分析"]
)

st.sidebar.divider()
st.sidebar.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 版本資訊
st.sidebar.markdown("""
<div style="
    text-align: center;
    color: #999;
    font-size: 10px;
    margin-top: 10px;
">
    v1.0.0 | OpenClaw CCTV Monitor<br>
    <span style="color: #666;">© 2026 姜昱安</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# 頁面 1: 即時流量
# ============================================================
if page == "📊 即時流量":
    st.title("📊 即時流量監控")
    st.caption("桃園國際機場 CCTV 串流系統")
    
    # 時間範圍選擇 - 優化版（快速按鈕 + 下拉選單）
    st.subheader("⏰ 時間範圍")
    
    # 快速按鈕列
    quick_buttons = st.columns(5)
    time_options = ["最近 1 小時", "最近 6 小時", "最近 24 小時", "最近 7 天", "自訂範圍"]
    
    # 根據選擇初始化
    if 'time_range' not in st.session_state:
        st.session_state['time_range'] = "最近 24 小時"
    
    selected_range_idx = time_options.index(st.session_state['time_range']) if st.session_state['time_range'] in time_options else 2
    
    for i, (btn, option) in enumerate(zip(quick_buttons, time_options)):
        with btn:
            if st.button(
                option.replace("最近 ", "").replace(" 小時", "h").replace(" 天", "d"),
                key=f"quick_btn_{i}",
                use_container_width=True
            ):
                st.session_state['time_range'] = option
                st.rerun()
    
    # 下拉選單（用於更細緻的選擇）
    time_range = st.selectbox(
        "或選擇精確範圍",
        time_options,
        index=selected_range_idx,
        label_visibility="collapsed"
    )
    
    # 根據選擇計算時間範圍
    now = datetime.now()
    start_time = now
    end_time = now
    
    if time_range == "最近 1 小時":
        start_time = now - timedelta(hours=1)
        end_time = now
    elif time_range == "最近 6 小時":
        start_time = now - timedelta(hours=6)
        end_time = now
    elif time_range == "最近 24 小時":
        start_time = now - timedelta(days=1)
        end_time = now
    elif time_range == "最近 7 天":
        start_time = now - timedelta(days=7)
        end_time = now
    else:
        # 自訂範圍
        col_custom1, col_custom2 = st.columns(2)
        with col_custom1:
            custom_start = st.date_input("開始日期", now - timedelta(days=1))
            start_time = datetime.combine(custom_start, datetime.min.time())
        with col_custom2:
            custom_end = st.date_input("結束日期", now)
            end_time = datetime.combine(custom_end, datetime.max.time())
    
    # 讀取資料
    @st.cache_data(ttl=60)  # 快取 60 秒
    def load_stream_data(start: datetime, end: datetime):
        conn = get_connection()
        query = """
            SELECT timestamp, server_name, stream_count
            FROM stream_logs
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """
        df = pd.read_sql_query(query, conn, params=(start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")))
        conn.close()
        
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['server_name'] = df['server_name'].str.strip()  # 移除空白字元
            df = df.drop_duplicates(subset=['timestamp', 'server_name'])  # 去重
        return df
    
    if time_range != "自訂範圍":
        df = load_stream_data(start_time, start_time + (now - start_time))
        actual_end = now
    else:
        df = load_stream_data(start_time, end_time)
        actual_end = end_time
    
    # 顯示資料筆數資訊
    if not df.empty:
        total_records = len(df)
        unique_timestamps = df['timestamp'].nunique()
        time_span = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600
        st.markdown(f"""
        <div style="padding: 0.75rem 1rem; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 8px; margin: 1rem 0; color: #ffffff;">
            📊 <strong>資料範圍:</strong> {start_time.strftime('%Y-%m-%d %H:%M')} ~ {actual_end.strftime('%Y-%m-%d %H:%M')}<br>
            📝 <strong>總筆數:</strong> {total_records:,} 筆 (去重後) | ⏱️ <strong>時間戳:</strong> {unique_timestamps} 個 | ⏳ <strong>跨度:</strong> {time_span:.1f} 小時
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding: 0.75rem 1rem; background: linear-gradient(135deg, #533483 0%, #2c2c54 100%); border-radius: 8px; margin: 1rem 0; color: #ffffff;">
            ⚠️ 目前時間範圍內沒有資料
        </div>
        """, unsafe_allow_html=True)
    
    # 顯示統計卡片
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    
    total_servers = 7
    latest_data = df[df['timestamp'] == df['timestamp'].max()] if not df.empty else pd.DataFrame()
    total_streams = latest_data['stream_count'].sum() if not latest_data.empty else 0
    
    # 計算統計數值
    if not df.empty:
        max_stream = int(df.groupby('server_name')['stream_count'].max().sum())
        min_stream = int(df.groupby('server_name')['stream_count'].min().sum())
    else:
        max_stream = "N/A"
        min_stream = "N/A"
    
    # 統一卡片樣式
    def render_kpi_card(icon, title, value, color="#1a1a2e"):
        return f"""
        <div style="
            background: linear-gradient(135deg, {color} 0%, {color}dd 100%);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 5px;
        ">
            <div style="font-size: 28px; margin-bottom: 8px;">{icon}</div>
            <div style="color: #a0a0a0; font-size: 12px; margin-bottom: 4px;">{title}</div>
            <div style="color: #00D4AA; font-size: 28px; font-weight: bold;">{value}</div>
        </div>
        """
    
    # 並排顯示四個 KPI 卡片
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        st.markdown(render_kpi_card("🏢", "伺服器數", total_servers, "#1a1a2e"), unsafe_allow_html=True)
    with kpi2:
        st.markdown(render_kpi_card("📹", "總串流數", total_streams, "#16213e"), unsafe_allow_html=True)
    with kpi3:
        st.markdown(render_kpi_card("📈", "最高串流", max_stream, "#0f3460"), unsafe_allow_html=True)
    with kpi4:
        st.markdown(render_kpi_card("📉", "最低串流", min_stream, "#533483"), unsafe_allow_html=True)
    
    st.divider()
    
    # 繪製圖表
    if not df.empty:
        # 選項：依伺服器分組或總計
        view_mode = st.radio(
            "📊 檢視模式",
            ["所有伺服器", "個別伺服器", "總流量"],
            horizontal=True,
            index=0
        )
        
        if view_mode == "總流量":
            # 總流量趨勢
            total_df = df.groupby('timestamp')['stream_count'].sum().reset_index()
            fig = px.area(
                total_df, 
                x='timestamp', 
                y='stream_count',
                title="📈 總串流量趨勢",
                labels={'timestamp': '時間', 'stream_count': '串流數'},
                color_discrete_sequence=['#00D4AA']
            )
            fig.update_layout(
                template="plotly_white",
                height=400,
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        elif view_mode == "所有伺服器":
            # 所有伺服器趨勢（電纜圖）
            fig = go.Figure()
            servers = sorted(df['server_name'].unique())
            colors = px.colors.qualitative.Set2[:len(servers)]
            
            for i, server in enumerate(servers):
                server_df = df[df['server_name'] == server]
                fig.add_trace(go.Scatter(
                    x=server_df['timestamp'],
                    y=server_df['stream_count'],
                    name=server.strip(),
                    mode='lines',
                    line=dict(color=colors[i % len(colors)], width=2),
                    hovertemplate='%{y} streams'
                ))
            
            fig.update_layout(
                title="📈 各伺服器串流量趨勢",
                xaxis_title="時間",
                yaxis_title="串流數",
                template="plotly_white",
                height=450,
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        
        else:
            # 個別伺服器下拉選擇
            server_list = sorted(df['server_name'].unique())
            selected_server = st.selectbox("🔍 選擇伺服器", [s.strip() for s in server_list])
            
            server_df = df[df['server_name'].str.strip() == selected_server]
            
            fig = px.line(
                server_df,
                x='timestamp',
                y='stream_count',
                title=f"📈 {selected_server} 串流量",
                labels={'timestamp': '時間', 'stream_count': '串流數'},
                color_discrete_sequence=['#00D4AA']
            )
            fig.update_layout(
                template="plotly_white",
                height=400,
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 該伺服器的統計
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("平均串流", f"{server_df['stream_count'].mean():.1f}")
            with col2:
                st.metric("最大串流", server_df['stream_count'].max())
            with col3:
                st.metric("最小串流", server_df['stream_count'].min())
    else:
        st.warning("⚠️ 選定的時間範圍內沒有資料")
    
    st.divider()
    
    # CSV 匯出
    st.subheader("💾 資料匯出")
    
    if not df.empty:
        # 格式化資料用於匯出
        export_df = df.copy()
        export_df['timestamp'] = export_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        export_df['server_name'] = export_df['server_name'].str.strip()
        
        col1, col2 = st.columns([1, 3])
        with col1:
            csv_data = export_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 下載 CSV",
                data=csv_data,
                file_name=f"cctv_stream_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            st.caption(f"共 {len(export_df)} 筆記錄")
    else:
        st.info("目前時間範圍內無資料可匯出")
    
    st.divider()
    
    # 資料庫統計資訊
    st.subheader("📊 資料庫資訊")
    
    from database import get_record_count
    db_stats = get_record_count()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="padding: 15px; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 12px; color: #fff;">
            <div style="font-size: 12px; color: #a0a0a0; margin-bottom: 8px;">📊 資料庫統計</div>
            <div style="font-size: 24px; color: #00D4AA; font-weight: bold;">{db_stats['total']:,}</div>
            <div style="font-size: 11px; color: #a0a0a0; margin-top: 5px;">筆記錄</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="padding: 15px; background: linear-gradient(135deg, #16213e 0%, #0f3460 100%); border-radius: 12px; color: #fff;">
            <div style="font-size: 12px; color: #a0a0a0; margin-bottom: 8px;">📅 資料時間範圍</div>
            <div style="font-size: 14px; color: #fff; margin-top: 5px;">
                {db_stats['earliest'][:10] if db_stats['earliest'] else 'N/A'}<br>
                ~<br>
                {db_stats['latest'][:10] if db_stats['latest'] else 'N/A'}
            </div>
        </div>
        """, unsafe_allow_html=True)

# ============================================================
# 頁面 2: 維修記錄
# ============================================================
elif page == "📋 維修記錄":
    st.title("📋 維修記錄管理")
    st.caption("維修案件登錄與追蹤")
    
    # 顯示現有記錄
    conn = get_connection()
    
    # 讀取所有維修記錄
    df_maintenance = pd.read_sql_query(
        "SELECT * FROM maintenance_records ORDER BY report_date DESC",
        conn
    )
    conn.close()
    
    if not df_maintenance.empty:
        # 狀態篩選
        status_filter = st.selectbox(
            "🔍 狀態篩選",
            ["全部", "pending", "in_progress", "completed"],
            index=0
        )
        
        if status_filter != "全部":
            df_maintenance = df_maintenance[df_maintenance['status'] == status_filter]
        
        st.dataframe(
            df_maintenance,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("尚無維修記錄")
    
    st.divider()
    
    # 新增維修記錄表單
    st.subheader("➕ 新增維修記錄")
    
    with st.form("add_maintenance_form"):
        col1, col2 = st.columns(2)
        with col1:
            case_number = st.text_input("案件編號 *", placeholder="例: MNT-2026-001")
            system_category = st.selectbox(
                "系統類別 *",
                ["廣播系統", "網路設備", "攝影機", "伺服器", "其他"]
            )
        
        with col2:
            report_date = st.date_input("報修日期 *", datetime.now())
            completion_date = st.date_input("完修日期", None)
        
        description = st.text_area("案件描述", placeholder="請輸入維修描述...")
        
        submitted = st.form_submit_button("💾 儲存記錄", use_container_width=True)
        
        if submitted:
            if not case_number:
                st.error("⚠️ 請輸入案件編號")
            else:
                from database import insert_maintenance_record
                insert_maintenance_record(
                    case_number=case_number,
                    report_date=report_date.strftime("%Y-%m-%d"),
                    completion_date=completion_date.strftime("%Y-%m-%d") if completion_date else None,
                    system_category=system_category,
                    status="completed" if completion_date else "pending",
                    description=description if description else None
                )
                st.success("✅ 維修記錄已儲存！")
                st.rerun()

# ============================================================
# 頁面 3: 串流使用分析報告
# ============================================================
elif page == "📈 串流使用分析報告":
    st.title("📈 串流使用分析報告")
    st.caption("CCTV 串流系統月報/季報分析")
    
    from database import get_monthly_stats, get_quarterly_stats, get_available_periods
    
    # 報告類型切換
    report_type = st.radio(
        "📊 報告類型",
        ["季度報告", "月度報告"],
        horizontal=True,
        index=0
    )
    
    # 取得可用期間
    available = get_available_periods()
    
    if not available:
        st.warning("⚠️ 目前沒有足夠的串流資料可供分析。請先確認爬蟲是否正常運行。")
    else:
        # 解析可用期間
        years = sorted(set([int(r['year']) for r in available]), reverse=True)
        
        if report_type == "季度報告":
            # 季度選擇
            col1, col2 = st.columns([1, 3])
            with col1:
                selected_year = st.selectbox("選擇年份", years, index=0)
            
            # 找出該年份有哪些季度有資料
            quarters_with_data = sorted([
                int(r['quarter'][1]) for r in available 
                if int(r['year']) == selected_year
            ], reverse=True)
            
            if not quarters_with_data:
                st.warning(f"⚠️ {selected_year} 年沒有資料")
            else:
                selected_quarter = st.selectbox("選擇季度", quarters_with_data)
                
                # 取得季度統計
                stats = get_quarterly_stats(selected_year, selected_quarter)
                
                # 顯示季度統一卡片
                st.divider()
                st.subheader(f"📅 {selected_year} 年 第 {selected_quarter} 季度")
                
                # 計算可用率顏色
                avail_value = stats['availability']
                if avail_value >= 95:
                    avail_icon, avail_color = "🟢", "#4CAF50"
                elif avail_value >= 85:
                    avail_icon, avail_color = "🟡", "#FFC107"
                else:
                    avail_icon, avail_color = "🔴", "#f44336"
                
                top_server_name = stats['top_servers'][0]['server_name'].strip() if stats['top_servers'] else "N/A"
                top_server_count = stats['top_servers'][0]['avg_count'] if stats['top_servers'] else 0
                
                # 統一報告卡片樣式
                def render_report_card(icon, title, value, subtitle="", bg_color="#1a1a2e"):
                    return f"""
                    <div style="
                        background: linear-gradient(135deg, {bg_color} 0%, {bg_color}cc 100%);
                        border-radius: 12px;
                        padding: 20px;
                        text-align: center;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        margin: 5px;
                        min-height: 100px;
                    ">
                        <div style="font-size: 24px; margin-bottom: 8px;">{icon}</div>
                        <div style="color: #a0a0a0; font-size: 11px; margin-bottom: 4px;">{title}</div>
                        <div style="color: #00D4AA; font-size: 22px; font-weight: bold;">{value}</div>
                        <div style="color: #888; font-size: 10px;">{subtitle}</div>
                    </div>
                    """
                
                rcol1, rcol2, rcol3 = st.columns(3)
                with rcol1:
                    st.markdown(render_report_card(
                        avail_icon, 
                        "系統可用率", 
                        f"{avail_value:.1f}%",
                        f"抓取 {stats['fetch_count']:,} / {stats['total_expected']:,}",
                        avail_color
                    ), unsafe_allow_html=True)
                with rcol2:
                    st.markdown(render_report_card(
                        "📊", 
                        "平均串流負載", 
                        f"{stats['avg_load']:.1f}",
                        f"總串流數: {stats['total_streams']:,}",
                        "#16213e"
                    ), unsafe_allow_html=True)
                with rcol3:
                    st.markdown(render_report_card(
                        "🏆", 
                        "最高負載伺服器", 
                        top_server_name,
                        f"平均 {top_server_count:.1f} 串流",
                        "#0f3460"
                    ), unsafe_allow_html=True)
                
                st.divider()
                
                # TOP 3 高負載排行
                st.subheader("🔥 高負載排行 TOP 3")
                
                if stats['top_servers']:
                    for i, server in enumerate(stats['top_servers'], 1):
                        col = st.columns([1, 3, 1])[1]
                        with col:
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(90deg, #{'ff6b6b' if i==1 else 'ffd93d' if i==2 else '6bcb77'} 0%, transparent 100%);
                                padding: 12px 20px;
                                border-radius: 8px;
                                margin: 8px 0;
                                border-left: 4px solid #{'ff6b6b' if i==1 else 'ffd93d' if i==2 else '6bcb77'};
                            ">
                                <big>第 {i} 名</big> &nbsp; <strong>{server['server_name'].strip()}</strong>
                                &nbsp;&nbsp; 平均 {server['avg_count']:.1f} 串流
                            </div>
                            """, unsafe_allow_html=True)
                
                # 月度趨勢（如果該季度有 3 個月資料）
                st.divider()
                st.subheader("📈 月度趨勢")
                
                monthly_data = []
                for month in stats['months']:
                    m_stats = get_monthly_stats(selected_year, month)
                    monthly_data.append({
                        '月份': f"{month}月",
                        '可用率': m_stats['availability'],
                        '平均負載': m_stats['avg_load']
                    })
                
                if monthly_data:
                    df_monthly = pd.DataFrame(monthly_data)
                    
                    # 並列顯示月度柱狀圖
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=df_monthly['月份'],
                        y=df_monthly['平均負載'],
                        name='平均負載',
                        marker_color='#00D4AA'
                    ))
                    fig.update_layout(
                        title="各月平均串流負載",
                        template="plotly_white",
                        height=300,
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        else:
            # 月度報告
            col1, col2 = st.columns([1, 1])
            with col1:
                selected_year = st.selectbox("選擇年份", years, index=0)
            
            with col2:
                months_with_data = sorted([
                    int(r['quarter'][1]) for r in available 
                    if int(r['year']) == selected_year for _ in range(3)
                ])
                # 取得該年有哪些月份有資料
                all_months = set()
                for r in available:
                    if int(r['year']) == selected_year:
                        q = int(r['quarter'][1])
                        for m in range((q-1)*3+1, q*3+1):
                            all_months.add(m)
                months_sorted = sorted(all_months, reverse=True)
                
                if not months_sorted:
                    st.warning(f"⚠️ {selected_year} 年沒有資料")
                else:
                    selected_month = st.selectbox("選擇月份", months_sorted)
                    
                    # 取得月度統計
                    stats = get_monthly_stats(selected_year, selected_month)
                    
                    # 顯示月度卡片
                    st.divider()
                    st.subheader(f"📅 {selected_year} 年 {selected_month} 月")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        avail_color = "🟢" if stats['availability'] >= 95 else "🟡" if stats['availability'] >= 85 else "🔴"
                        st.metric(
                            f"{avail_color} 系統可用率",
                            f"{stats['availability']:.1f}%",
                            help=f"成功抓取 {stats['fetch_count']} 次 / 預期 {stats['total_expected']} 次"
                        )
                    
                    with col2:
                        st.metric(
                            "📊 平均串流負載",
                            f"{stats['avg_load']:.1f}",
                            help=f"總串流數: {stats['total_streams']:,}"
                        )
                    
                    with col3:
                        if stats['top_servers']:
                            top_name = stats['top_servers'][0]['server_name'].strip()
                            top_count = stats['top_servers'][0]['avg_count']
                            st.metric(
                                "🏆 最高負載伺服器",
                                top_name,
                                help=f"平均 {top_count:.1f} 串流"
                            )
                    
                    st.divider()
                    
                    # TOP 3
                    st.subheader("🔥 高負載排行 TOP 3")
                    
                    if stats['top_servers']:
                        for i, server in enumerate(stats['top_servers'], 1):
                            with st.container():
                                st.markdown(f"""
                                <div style="
                                    background: linear-gradient(90deg, #{'ff6b6b' if i==1 else 'ffd93d' if i==2 else '6bcb77'} 0%, transparent 100%);
                                    padding: 12px 20px;
                                    border-radius: 8px;
                                    margin: 8px 0;
                                    border-left: 4px solid #{'ff6b6b' if i==1 else 'ffd93d' if i==2 else '6bcb77'};
                                ">
                                    <big>第 {i} 名</big> &nbsp; <strong>{server['server_name'].strip()}</strong>
                                    &nbsp;&nbsp; 平均 {server['avg_count']:.1f} 串流
                                </div>
                                """, unsafe_allow_html=True)
    
    # PDF 匯出功能
    st.divider()
    st.subheader("💾 匯出 PDF 報表")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        pdf_report_type = st.radio(
            "選擇報告類型",
            ["季度報告", "月度報告"],
            horizontal=True,
            key="pdf_report_type"
        )
    
    with col2:
        if pdf_report_type == "季度報告":
            # 季度 PDF
            if 'quarters_with_data' in dir() and quarters_with_data:
                pdf_year = selected_year
                pdf_quarter = selected_quarter
                
                if st.button("📥 下載季度 PDF 報表", use_container_width=True):
                    try:
                        from pdf_generator import generate_quarterly_pdf
                        with st.spinner("產生 PDF 中..."):
                            pdf_bytes = generate_quarterly_pdf(pdf_year, pdf_quarter)
                        st.success(f"✅ PDF 產生成功 ({len(pdf_bytes):,} bytes)")
                        st.download_button(
                            label="📥 點擊下載",
                            data=pdf_bytes,
                            file_name=f"CCTV_Report_{pdf_year}_Q{pdf_quarter}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"❌ PDF 產生失敗: {e}")
        else:
            # 月度 PDF
            if 'months_sorted' in dir() and months_sorted:
                pdf_year = selected_year
                pdf_month = selected_month
                
                if st.button("📥 下載月度 PDF 報表", use_container_width=True):
                    try:
                        from pdf_generator import generate_monthly_pdf
                        with st.spinner("產生 PDF 中..."):
                            pdf_bytes = generate_monthly_pdf(pdf_year, pdf_month)
                        st.success(f"✅ PDF 產生成功 ({len(pdf_bytes):,} bytes)")
                        st.download_button(
                            label="📥 點擊下載",
                            data=pdf_bytes,
                            file_name=f"CCTV_Report_{pdf_year}_{pdf_month:02d}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"❌ PDF 產生失敗: {e}")
    
    # 底部說明
    st.divider()
    st.caption("""
    📌 **指標說明：**
    - **系統可用率**：成功抓取次數 ÷ 預期抓取次數 (每 10 分鐘一次)
    - **平均串流負載**：該期間所有伺服器的平均串流數
    - **高負載排行**：平均串流數最高的前三名伺服器
    """)
