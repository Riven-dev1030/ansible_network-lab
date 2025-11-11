#!/bin/bash
# ZTP Provisioning Server 啟動腳本

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "=========================================="
echo "ZTP Provisioning Server 啟動腳本"
echo "=========================================="

# 檢查 Python 3
if ! command -v python3 &> /dev/null; then
    echo "錯誤: 未安裝 Python 3"
    exit 1
fi

# 檢查並創建虛擬環境
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "創建 Python 虛擬環境..."
    python3 -m venv "$SCRIPT_DIR/venv"
fi

# 啟動虛擬環境
echo "啟動虛擬環境..."
source "$SCRIPT_DIR/venv/bin/activate"

# 安裝依賴
echo "安裝 Python 依賴..."
pip install -q --upgrade pip
pip install -q -r "$SCRIPT_DIR/requirements.txt"

# 創建日誌目錄
sudo mkdir -p /var/log
sudo chmod 755 /var/log

# 啟動服務
echo ""
echo "啟動 ZTP Provisioning Server..."
echo "API 端點: http://0.0.0.0:5000"
echo "按 Ctrl+C 停止服務"
echo ""

cd "$SCRIPT_DIR"
python3 app.py
