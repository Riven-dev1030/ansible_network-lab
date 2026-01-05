#!/bin/sh
# Bastion SSH Server 容器啟動腳本

set -e

echo "=========================================="
echo "Bastion SSH Server - 啟動中..."
echo "=========================================="

# 檢查 SSH 主機密鑰
echo "檢查 SSH 主機密鑰..."
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    echo "產生 SSH 主機密鑰..."
    ssh-keygen -A
    echo "✓ 主機密鑰已產生"
fi

# 檢查 authorized_keys
if [ ! -f /root/.ssh/authorized_keys ]; then
    echo "⚠️  警告: /root/.ssh/authorized_keys 不存在"
    echo "⚠️  請掛載或建立 authorized_keys 檔案"
    mkdir -p /root/.ssh
    touch /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
fi

# 驗證 sshd 配置語法
echo "驗證 sshd 配置..."
if sshd -t; then
    echo "✓ SSH 配置語法正確"
else
    echo "✗ SSH 配置有錯誤，請檢查 sshd_config"
    exit 1
fi

# 顯示配置資訊
echo ""
echo "=========================================="
echo "SSH 伺服器配置資訊"
echo "=========================================="
echo "監聽通訊埠: 22"
echo "認證方式: SSH 密鑰"
echo "TCP 轉發: 啟用 (PermitOpen 限制)"
echo "允許的轉發目標: 192.168.1.*:22"
echo ""

# 顯示目前的 PermitOpen 配置
echo "目前 PermitOpen 配置："
sshd -T | grep permitopen || echo "  (未配置)"
echo ""

echo "=========================================="
echo "SSH 服務啟動..."
echo "=========================================="

# 啟動 sshd（前台執行，以便容器可以捕獲信號）
exec /usr/sbin/sshd -D -e
