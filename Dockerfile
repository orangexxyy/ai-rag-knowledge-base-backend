FROM python:3.11-slim

# 设置容器内工作目录
WORKDIR /app

# 先复制依赖文件，安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制整个项目
# 这里会把 app/ 和 data/ 一起复制进去
COPY . .

# 暴露 FastAPI 服务端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]