# ZTP 快速開始指南

## 🚀 5 分鐘快速部署

### Step 1: 準備 ZTP Server (1 分鐘)

```bash
# SSH 到 ZTP Server (192.168.1.100)
ssh user@192.168.1.100

# 部署 ZTP 環境
cd /path/to/ansible_network-lab/ztp
ansible-playbook playbooks/setup_ztp_server.yml
```

### Step 2: 配置設備清單 (2 分鐘)

```bash
# 編輯設備清單，添加您的設備 MAC 地址
vim dhcp/device_inventory.yml
```

**重要：** 獲取設備 MAC 地址
```
# 在設備 console 執行
show version | include Base ethernet MAC
```

### Step 3: 驗證 ZTP Server (1 分鐘)

```bash
# 驗證所有服務正常
ansible-playbook playbooks/verify_ztp_server.yml

# 或手動檢查
curl http://192.168.1.100:5000/api/health
curl http://192.168.1.100:5000/api/devices
```

### Step 4: 啟動新設備 (1 分鐘)

```
1. 將新設備連接到管理網路
2. 確保設備為出廠狀態
3. 開機
4. 等待自動配置完成
```

### Step 5: 監控並驗證

```bash
# 實時監控設備註冊
watch -n 2 'curl -s http://192.168.1.100:5000/api/registrations | jq'

# 檢查設備是否獲得固定 IP
# 在設備上執行：
show ip interface brief
show running-config | include hostname

# 從 Ansible 控制節點測試
ansible R1 -m ping
```

## ✅ 成功標誌

- ✅ 設備獲得固定管理 IP (例如: 192.168.1.11)
- ✅ Hostname 已正確設定 (例如: R1)
- ✅ SSH 可以連接
- ✅ Ansible 可以管理設備

## 🎯 下一步

使用 Ansible 進行詳細配置：

```bash
cd /path/to/ansible_network-lab

# 完整部署
ansible-playbook playbooks/deploy_all.yml

# 或分階段部署
ansible-playbook playbooks/s1_hq_vlan_hsrp.yml
ansible-playbook playbooks/s2_dmz_r3.yml
# ... 等等
```

## 🆘 遇到問題？

查看完整文檔：[README.md](README.md)

快速診斷：
```bash
# 檢查所有服務狀態
systemctl status isc-dhcp-server
systemctl status tftpd-hpa
systemctl status nginx
systemctl status ztp-provisioning

# 查看日誌
journalctl -u isc-dhcp-server -f
journalctl -u ztp-provisioning -f
```

---

**提示：** 第一次部署建議逐步執行並監控日誌，熟悉流程後即可批量部署！
