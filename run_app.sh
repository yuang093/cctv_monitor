#!/bin/bash
# 啟動 Streamlit 監控網頁
cd ~/.openclaw/workspace/cctv_monitor
streamlit run app.py --server.port 8501 --server.address localhost
