#!/bin/bash
# DHCP Server 安裝與配置腳本
# 用於 Ubuntu/Debian 系統

set -e

echo "=========================================="
echo "ZTP DHCP Server Setup Script"
echo "=========================================="

# 檢查是否為 root
if [[ $EUID -ne 0 ]]; then
   echo "錯誤: 此腳本需要 root 權限執行"
   echo "請使用: sudo $0"
   exit 1
fi

# 1. 安裝 ISC DHCP Server
echo ""
echo "[1/6] 安裝 ISC DHCP Server..."
apt-get update
apt-get install -y isc-dhcp-server

# 2. 備份原始配置
echo ""
echo "[2/6] 備份原始 DHCP 配置..."
if [ -f /etc/dhcp/dhcpd.conf ]; then
    cp /etc/dhcp/dhcpd.conf /etc/dhcp/dhcpd.conf.backup.$(date +%Y%m%d_%H%M%S)
    echo "原始配置已備份"
fi

# 3. 複製 ZTP DHCP 配置
echo ""
echo "[3/6] 部署 ZTP DHCP 配置..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cp "$SCRIPT_DIR/dhcpd.conf" /etc/dhcp/dhcpd.conf
echo "DHCP 配置已部署"

# 4. 設定 DHCP Server 監聽介面
echo ""
echo "[4/6] 配置 DHCP Server 監聽介面..."
read -p "請輸入 DHCP Server 監聽的網路介面 (例如: eth0, ens33): " INTERFACE

if [ -z "$INTERFACE" ]; then
    echo "警告: 未指定介面，使用預設值 eth0"
    INTERFACE="eth0"
fi

# 配置監聽介面
if [ -f /etc/default/isc-dhcp-server ]; then
    sed -i "s/^INTERFACESv4=.*/INTERFACESv4=\"$INTERFACE\"/" /etc/default/isc-dhcp-server
    echo "DHCP Server 將監聽介面: $INTERFACE"
fi

# 5. 驗證配置
echo ""
echo "[5/6] 驗證 DHCP 配置..."
dhcpd -t -cf /etc/dhcp/dhcpd.conf
if [ $? -eq 0 ]; then
    echo "✓ DHCP 配置驗證通過"
else
    echo "✗ DHCP 配置驗證失敗，請檢查配置文件"
    exit 1
fi

# 6. 啟動 DHCP Server
echo ""
echo "[6/6] 啟動 DHCP Server..."
systemctl enable isc-dhcp-server
systemctl restart isc-dhcp-server

# 檢查服務狀態
sleep 2
if systemctl is-active --quiet isc-dhcp-server; then
    echo "✓ DHCP Server 已成功啟動"
else
    echo "✗ DHCP Server 啟動失敗"
    echo "查看日誌: journalctl -u isc-dhcp-server -n 50"
    exit 1
fi

# 顯示服務狀態
echo ""
echo "=========================================="
echo "DHCP Server 設定完成！"
echo "=========================================="
echo ""
echo "服務狀態:"
systemctl status isc-dhcp-server --no-pager -l

echo ""
echo "常用命令:"
echo "  查看 DHCP 租約: cat /var/lib/dhcp/dhcpd.leases"
echo "  查看日誌:      journalctl -u isc-dhcp-server -f"
echo "  重啟服務:      systemctl restart isc-dhcp-server"
echo "  停止服務:      systemctl stop isc-dhcp-server"
echo ""
echo "DHCP 配置文件: /etc/dhcp/dhcpd.conf"
echo "設備清單文件: $SCRIPT_DIR/device_inventory.yml"
echo ""
