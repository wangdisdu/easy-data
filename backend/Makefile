.PHONY: develop code-format code-check

develop:
	@echo "安装开发环境依赖..."
	pip install -e ".[dev]"
	@echo "安装完成！"

code-format:
	@echo "格式化代码..."
	black app/
	isort app/
	@echo "格式化完成！"

code-check:
	@echo "检查代码..."
	black --check app/ || exit 1
	isort --check-only app/ || exit 1
	ruff check app/ || exit 1
	@echo "检查通过！"
