.PHONY: help build up down logs shell clean test

# Docker 鏡像和容器名
IMAGE_NAME := ansible-bastion
CONTAINER_NAME := ansible-bastion
TAG := latest

help:
	@echo "Bastion SSH Server Docker 管理工具"
	@echo ""
	@echo "可用命令："
	@echo "  make build          - 構建 Docker 鏡像"
	@echo "  make up             - 啟動容器（使用 docker-compose）"
	@echo "  make down           - 停止容器（使用 docker-compose）"
	@echo "  make logs           - 查看容器日誌"
	@echo "  make shell          - 進入容器 shell"
	@echo "  make test-connect   - 測試 SSH 連接"
	@echo "  make test-config    - 測試 SSH 配置"
	@echo "  make clean          - 清理容器和鏡像"
	@echo "  make push           - 推送鏡像到倉庫"
	@echo ""

build:
	@echo "構建 Docker 鏡像..."
	@docker-compose build
	@echo "✓ 鏡像構建完成: $(IMAGE_NAME):$(TAG)"

up:
	@echo "啟動容器..."
	@docker-compose up -d
	@echo "✓ 容器已啟動"
	@echo ""
	@echo "訪問資訊："
	@echo "  主機: localhost"
	@echo "  通訊埠: 2222"
	@echo "  使用者: root"
	@echo ""
	@echo "測試連接:"
	@echo "  ssh -i ~/.ssh/id_rsa -p 2222 root@localhost"
	@echo ""

down:
	@echo "停止容器..."
	@docker-compose down
	@echo "✓ 容器已停止"

logs:
	@docker-compose logs -f $(CONTAINER_NAME)

shell:
	@echo "進入容器 shell..."
	@docker exec -it $(CONTAINER_NAME) sh

test-connect:
	@echo "測試 SSH 連接..."
	@echo "連接到: localhost:2222"
	@ssh -i ~/.ssh/id_rsa -p 2222 -v root@localhost "echo '✓ SSH 連接成功'"

test-config:
	@echo "測試 SSH 配置..."
	@docker exec $(CONTAINER_NAME) sshd -t
	@echo "✓ SSH 配置語法正確"
	@echo ""
	@echo "目前配置："
	@docker exec $(CONTAINER_NAME) sshd -T | grep -E "permitopen|allowtcpforwarding|pubkeyauthentication|passwordauthentication"

clean:
	@echo "清理 Docker 資源..."
	@docker-compose down --rmi all -v
	@echo "✓ 清理完成"

push:
	@read -p "輸入鏡像倉庫地址 (例如: docker.io/username/ansible-bastion): " REPO; \
	docker tag $(IMAGE_NAME):$(TAG) $$REPO:$(TAG); \
	docker push $$REPO:$(TAG); \
	echo "✓ 鏡像已推送: $$REPO:$(TAG)"

# 便利命令
restart: down up
	@echo "✓ 容器已重啟"

rebuild: clean build up
	@echo "✓ 鏡像已重新構建和啟動"

# 輸出目前配置
show-config:
	@echo "目前配置："
	@echo "  鏡像名稱: $(IMAGE_NAME)"
	@echo "  標籤: $(TAG)"
	@echo "  容器名: $(CONTAINER_NAME)"
	@echo ""
	@echo "Docker Compose 配置："
	@docker-compose config

# 查看容器資源使用
stats:
	@docker stats $(CONTAINER_NAME)

# 驗證所有條件
verify:
	@echo "驗證 Docker 環境..."
	@docker --version
	@docker-compose --version
	@echo "✓ 環境檢查完成"
	@echo ""
	@echo "檢查 authorized_keys..."
	@if [ -f authorized_keys ]; then \
		echo "✓ authorized_keys 檔案存在"; \
	else \
		echo "⚠️  authorized_keys 檔案不存在，請參考 README.md"; \
	fi
