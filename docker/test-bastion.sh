#!/bin/bash
# Bastion Docker 鏡像快速測試腳本

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 測試函式
test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

echo "=========================================="
echo "Bastion SSH Server Docker 鏡像測試"
echo "=========================================="
echo ""

# 檢查 Docker
echo "1. 檢查 Docker 環境..."
docker --version > /dev/null
test_result $? "Docker 已安裝"

docker-compose --version > /dev/null
test_result $? "Docker Compose 已安裝"

# 檢查 SSH 密鑰
echo ""
echo "2. 檢查 SSH 密鑰..."
if [ -f ~/.ssh/id_rsa ]; then
    test_result 0 "SSH 私鑰存在: ~/.ssh/id_rsa"
else
    echo -e "${YELLOW}⚠️  未找到 SSH 私鑰，將使用 bastion_key${NC}"
fi

# 檢查配置檔案
echo ""
echo "3. 檢查配置檔案..."
[ -f sshd_config ] && test_result 0 "sshd_config 存在" || echo -e "${YELLOW}⚠️  sshd_config 將使用預設配置${NC}"
[ -f docker-compose.yml ] && test_result 0 "docker-compose.yml 存在" || test_result 1 "docker-compose.yml 不存在"

# 檢查 authorized_keys
echo ""
echo "4. 檢查 authorized_keys..."
if [ ! -f authorized_keys ]; then
    echo -e "${YELLOW}⚠️  authorized_keys 不存在，建立示例檔案...${NC}"
    cp authorized_keys.example authorized_keys
    echo -e "${YELLOW}請編輯 authorized_keys 並新增你的 SSH 公鑰${NC}"
    echo "  命令: cat ~/.ssh/id_rsa.pub >> docker/authorized_keys"
fi

[ -s authorized_keys ] && test_result 0 "authorized_keys 檔案非空" || echo -e "${YELLOW}⚠️  authorized_keys 為空${NC}"

# 構建鏡像
echo ""
echo "5. 構建 Docker 鏡像..."
docker-compose build > /dev/null 2>&1
test_result $? "鏡像構建成功"

# 啟動容器
echo ""
echo "6. 啟動容器..."
docker-compose up -d
test_result $? "容器啟動成功"

# 等待服務就緒
echo ""
echo "7. 等待 SSH 服務就緒..."
sleep 3
docker-compose exec -T bastion sshd -t > /dev/null
test_result $? "SSH 服務健康檢查通過"

# 測試連接
echo ""
echo "8. 測試 SSH 連接..."
if ssh-keyscan -p 2222 localhost > /dev/null 2>&1; then
    test_result 0 "SSH 通訊埠 2222 可訪問"
else
    test_result 1 "SSH 通訊埠 2222 不可訪問"
fi

# 顯示配置資訊
echo ""
echo "=========================================="
echo "SSH 伺服器配置資訊"
echo "=========================================="
docker-compose exec -T bastion sshd -T | grep -E "port|permitopen|allowtcpforwarding|pubkeyauthentication|passwordauthentication" || true

# 顯示日誌
echo ""
echo "=========================================="
echo "容器日誌"
echo "=========================================="
docker-compose logs bastion | tail -20

# 測試總結
echo ""
echo "=========================================="
echo "測試完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 啟動容器:"
echo "   docker-compose up -d"
echo ""
echo "2. 測試 SSH 連接:"
echo "   ssh -i ~/.ssh/id_rsa -p 2222 root@localhost"
echo ""
echo "3. 配置 Ansible 使用跳板機:"
echo "   在 inventory/hosts.yml 中新增 ProxyCommand 配置"
echo ""
echo "4. 查看日誌:"
echo "   docker-compose logs -f"
echo ""
echo "5. 停止容器:"
echo "   docker-compose down"
echo ""
