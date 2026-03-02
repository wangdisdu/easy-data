.PHONY: docker-build docker-run docker-stop

# Docker 镜像名
IMAGE_NAME := easy-data
IMAGE_TAG ?= latest

docker-build:
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-run:
	docker run -d --name easy-data -p 8000:8000 $(IMAGE_NAME):$(IMAGE_TAG)

docker-stop:
	docker stop easy-data 2>/dev/null || true
	docker rm easy-data 2>/dev/null || true
