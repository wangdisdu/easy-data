# Easy Data 应用镜像（使用国内镜像加速）
FROM docker.1ms.run/library/python:3.12-slim-bookworm

LABEL maintainer="Easy Data"
LABEL description="Easy Data - 数据探索与智能分析"

# 避免 Python 写字节码、缓冲 stdout
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 依赖声明与应用代码（pip install -e . 需在 app 存在时执行）
COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
RUN pip install --no-cache-dir -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# 前端静态资源（不参与依赖层缓存）
COPY backend/www ./www

# 不将 .env 打入镜像，运行时通过 --env-file 注入
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
