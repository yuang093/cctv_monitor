FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴 (Streamlit 需要)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 複製需求檔案
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY . .

# 掛載資料庫磁區 (持久化)
VOLUME [ "/app/data" ]

# 暴露連接埠
EXPOSE 8501

# 啟動命令
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
