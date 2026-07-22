FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖（PyMuPDF、FAISS编译所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 创建数据目录
RUN mkdir -p backend/data/vector_store backend/data/uploads

# 暴露端口
EXPOSE 8000 8501

# 默认启动 FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
