.PHONY: docker-build docker-run docker-stop

IMAGE_NAME := easy-data
IMAGE_TAG ?= latest
# SQLite 数据目录挂载到容器 /app/data，防止数据丢失
DATA_DIR ?= $(CURDIR)/data

# 先清理旧镜像再构建，保证产出为当前代码
docker-build:
	docker rmi $(IMAGE_NAME):$(IMAGE_TAG) 2>/dev/null || true
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

# 使用 .env：存在则 --env-file 注入；数据库挂载到宿主机 $(DATA_DIR)
docker-run:
	@mkdir -p $(DATA_DIR)
	docker run -d --name easy-data -p 8000:8000 \
		-v $(DATA_DIR):/app/data \
		-e DATABASE_URL=sqlite:////app/data/easy_data.db \
		$(if $(wildcard .env),--env-file .env,) \
		$(IMAGE_NAME):$(IMAGE_TAG)

docker-stop:
	docker stop easy-data 2>/dev/null || true
	docker rm easy-data 2>/dev/null || true
