# 使用国内镜像加速
FROM docker.1ms.run/library/python:3.12-slim-bookworm
WORKDIR /app

# 安装后端依赖
COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install --no-cache-dir -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 使用已构建好的前端静态文件（backend/www）
COPY backend/www ./www

EXPOSE 8000
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
