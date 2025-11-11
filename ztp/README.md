# ZTP + DHCP Binding 自動化部署方案

## 📋 概述

這個 ZTP (Zero Touch Provisioning) 方案結合 DHCP 動態綁定，實現了完全自動化的網路設備部署流程。新設備接入網路後，無需人工介入即可：

1. ✅ 自動獲取臨時 IP
2. ✅ 下載並執行 ZTP 配置腳本
3. ✅ 向 Provisioning Server 註冊設備資訊
4. ✅ 自動綁定固定管理 IP
5. ✅ 套用基本配置並就緒

## 🎯 核心理念

**這是一種「變相的 OOB 管理」方案**：
- 使用 DHCP 動態分配 + MAC 綁定 = 固定管理 IP
- 不需要手動配置每台設備的管理 IP
- 實現了「即插即用」的 Out-of-Band 管理網路

## 📁 目錄結構

```
ztp/
├── README.md                          # 本文件
├── dhcp/                              # DHCP Server 配置
│   ├── dhcpd.conf                    # ISC DHCP 配置
│   ├── device_inventory.yml          # 設備清單（MAC → IP 映射）
│   └── setup_dhcp_server.sh          # DHCP Server 安裝腳本
├── scripts/                           # ZTP 腳本
│   └── ztp_bootstrap.py              # 設備初始化腳本
├── templates/                         # 配置模板
│   └── device_config_template.j2     # Jinja2 設備配置模板
├── provisioning_server/               # API 服務
│   ├── app.py                        # Flask API 應用
│   ├── requirements.txt              # Python 依賴
│   ├── start_server.sh               # 啟動腳本
│   └── ztp-provisioning.service      # Systemd service
└── playbooks/                         # Ansible 部署腳本
    ├── setup_ztp_server.yml          # 部署 ZTP Server
    └── verify_ztp_server.yml         # 驗證部署
```

## 🏗️ 架構圖

```
┌────────────────────────────────────────────────────────┐
│                  ZTP Server (192.168.1.100)            │
│                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │ DHCP Server  │  │ TFTP Server  │  │ HTTP Server │ │
│  │   Port 67    │  │   Port 69    │  │  Port 8080  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
│         │                 │                  │         │
│         └─────────────────┼──────────────────┘         │
│                           │                            │
│                  ┌────────┴────────┐                   │
│                  │ Provisioning API│                   │
│                  │    Port 5000    │                   │
│                  └─────────────────┘                   │
└────────────────────────────────────────────────────────┘
                            │
                            │ OOB Management Network
                            │ 192.168.1.0/24
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────┴────┐         ┌────┴────┐        ┌────┴────┐
   │   R1    │         │   R2    │        │   R3    │
   │(新設備) │         │(新設備) │        │(新設備) │
   └─────────┘         └─────────┘        └─────────┘
```

## 🔄 工作流程

### Phase 1: 初始 DHCP (臨時 IP)
```
1. 新設備開機，發送 DHCP Discover
2. DHCP Server 從動態 IP 池分配臨時 IP (192.168.1.200-250)
3. DHCP Response 包含:
   - 臨時 IP 地址
   - TFTP Server 地址 (Option 66)
   - ZTP 腳本文件名 (Option 67)
```

### Phase 2: ZTP 腳本執行
```
4. 設備從 TFTP Server 下載 ztp_bootstrap.py
5. 執行腳本，收集設備資訊:
   - MAC 地址
   - 序列號
   - 型號
   - 當前 IP
```

### Phase 3: 設備註冊
```
6. ZTP 腳本向 Provisioning API 發送註冊請求
   POST http://192.168.1.100:5000/api/register
   {
     "mac_address": "50:00:00:01:00:00",
     "serial_number": "FCW1234ABCD",
     "model": "IOSv",
     "current_ip": "192.168.1.200"
   }

7. Provisioning Server:
   - 查詢 device_inventory.yml
   - 根據 MAC 地址識別設備 (例如: R1)
   - 分配固定 IP (例如: 192.168.1.11)
```

### Phase 4: DHCP 綁定
```
8. Provisioning Server 動態更新 DHCP 配置:
   - 在 dhcpd.conf 中添加靜態綁定
   - 重啟 DHCP 服務

9. 添加的綁定範例:
   host R1 {
       hardware ethernet 50:00:00:01:00:00;
       fixed-address 192.168.1.11;
       option host-name "R1";
   }
```

### Phase 5: 套用配置
```
10. ZTP 腳本套用基本配置:
    - 設定 hostname
    - 配置管理介面使用 DHCP
    - 啟用 SSH
    - 建立管理使用者
    - 配置 Syslog

11. 釋放並更新 DHCP 租約
12. 設備獲得固定 IP: 192.168.1.11
13. ZTP 完成，設備就緒！
```

## 🚀 快速開始

### 前置要求

- **ZTP Server**: Ubuntu 20.04+ (或其他 Debian 系列)
- **網路**: 管理網路 192.168.1.0/24
- **設備**: Cisco IOS 設備（支援 Python）

### 1. 準備 ZTP Server

**選項 A: 使用 Ansible 自動部署（推薦）**

```bash
# 在 Ansible 控制節點執行
cd ansible_network-lab/ztp

# 部署 ZTP Server（在 192.168.1.100 上）
ansible-playbook playbooks/setup_ztp_server.yml

# 驗證部署
ansible-playbook playbooks/verify_ztp_server.yml
```

**選項 B: 手動部署**

```bash
# 1. 安裝 DHCP Server
cd ztp/dhcp
sudo ./setup_dhcp_server.sh

# 2. 安裝 TFTP Server
sudo apt-get install tftpd-hpa
sudo cp ../scripts/ztp_bootstrap.py /var/lib/tftpboot/

# 3. 啟動 Provisioning Server
cd ../provisioning_server
./start_server.sh
```

### 2. 配置設備清單

編輯 `ztp/dhcp/device_inventory.yml`，添加您的設備：

```yaml
devices:
  R1:
    mac_address: "50:00:00:01:00:00"  # 修改為實際 MAC
    mgmt_ip: "192.168.1.11"
    device_type: "cisco_ios"
    role: "edge_hsrp_primary"
```

**如何獲取設備 MAC 地址？**
```
# 在設備 console 執行
show version | include Base ethernet MAC
```

### 3. 啟動新設備

```
1. 將新設備連接到管理網路
2. 確保設備配置為預設（出廠狀態或清空配置）
3. 開機
4. 等待 ZTP 自動完成（約 2-5 分鐘）
```

### 4. 監控部署過程

**查看 DHCP 租約：**
```bash
tail -f /var/lib/dhcp/dhcpd.leases
```

**查看設備註冊：**
```bash
# 實時查看註冊
watch -n 2 'curl -s http://192.168.1.100:5000/api/registrations | jq'

# 或查看日誌文件
tail -f /var/log/ztp_registrations.json
```

**查看 Provisioning Server 日誌：**
```bash
journalctl -u ztp-provisioning -f
```

## 📊 驗證 ZTP 成功

### 1. 檢查設備 IP

在設備上：
```
show ip interface brief
```

應該看到管理介面獲得了固定 IP（例如 192.168.1.11）

### 2. 檢查 hostname

```
show running-config | include hostname
```

應該顯示正確的 hostname（例如：R1）

### 3. 測試 SSH 連接

從 Ansible 控制節點：
```bash
ssh admin@192.168.1.11
# 密碼: admin123 (預設)
```

### 4. 使用 Ansible 測試

```bash
cd ansible_network-lab
ansible R1 -m ping
ansible R1 -m cisco.ios.ios_command -a "commands='show version'"
```

## 🔧 API 端點

Provisioning Server 提供以下 API：

### 健康檢查
```bash
curl http://192.168.1.100:5000/api/health
```

### 獲取設備清單
```bash
curl http://192.168.1.100:5000/api/devices | jq
```

### 獲取註冊記錄
```bash
curl http://192.168.1.100:5000/api/registrations | jq
```

### 手動註冊設備
```bash
curl -X POST http://192.168.1.100:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "50:00:00:01:00:00",
    "serial_number": "FCW1234ABCD",
    "model": "IOSv"
  }'
```

## 🎯 與現有 Ansible 整合

ZTP 完成後，設備已具備：
- ✅ 固定管理 IP
- ✅ SSH 啟用
- ✅ 管理使用者
- ✅ 基本配置

接下來使用現有的 Ansible playbooks 進行詳細配置：

```bash
cd ansible_network-lab

# 執行完整部署
ansible-playbook playbooks/deploy_all.yml

# 或分階段部署
ansible-playbook playbooks/s1_hq_vlan_hsrp.yml
ansible-playbook playbooks/s2_dmz_r3.yml
# ... 等等
```

## 🔄 ZTP vs 傳統配置對比

| 項目 | 傳統方式 | ZTP 方式 |
|------|----------|----------|
| **IP 配置** | 手動逐台配置 | 自動分配並綁定 |
| **Hostname** | 手動設定 | 自動識別設定 |
| **部署時間** | 15-30分鐘/台 | 2-5分鐘/台 |
| **人為錯誤** | 容易發生 | 幾乎為零 |
| **10台設備** | 3-5小時 | 20-50分鐘 |
| **可擴展性** | 困難 | 優秀 |
| **一致性** | 難以保證 | 完全一致 |

## 📋 設備清單範例

`device_inventory.yml` 完整範例：

```yaml
devices:
  # HQ Routers
  R1:
    mac_address: "50:00:00:01:00:00"
    mgmt_ip: "192.168.1.11"
    device_type: "cisco_ios"
    role: "edge_hsrp_primary"
    location: "HQ"
    group: "hq_routers"

  R2:
    mac_address: "50:00:00:02:00:00"
    mgmt_ip: "192.168.1.12"
    device_type: "cisco_ios"
    role: "edge_hsrp_standby"
    location: "HQ"
    group: "hq_routers"

  # ... 更多設備

ztp_server:
  ip: "192.168.1.100"
  tftp_root: "/var/lib/tftpboot"
  http_port: 8080
  api_port: 5000
```

## 🛠️ 故障排除

### 問題 1: 設備無法獲取 DHCP

**檢查項目：**
```bash
# DHCP Server 狀態
systemctl status isc-dhcp-server

# 查看 DHCP 日誌
journalctl -u isc-dhcp-server -n 50

# 檢查網路連接
ip addr show
ping 192.168.1.100
```

### 問題 2: TFTP 下載失敗

**檢查項目：**
```bash
# TFTP Server 狀態
systemctl status tftpd-hpa

# 測試 TFTP
tftp 192.168.1.100
> get ztp_bootstrap.py
> quit

# 檢查文件權限
ls -l /var/lib/tftpboot/ztp_bootstrap.py
```

### 問題 3: 設備註冊失敗

**檢查項目：**
```bash
# Provisioning Server 狀態
systemctl status ztp-provisioning

# API 健康檢查
curl http://192.168.1.100:5000/api/health

# 查看詳細日誌
journalctl -u ztp-provisioning -f
```

### 問題 4: MAC 地址不匹配

**症狀：** 設備無法識別，未分配固定 IP

**解決方案：**
1. 在設備上查看實際 MAC
2. 更新 `device_inventory.yml`
3. 重啟 Provisioning Server

## 🔒 安全考量

### 1. 管理網路隔離
- ZTP 應在獨立的管理網路運行
- 使用 VLAN 或物理隔離

### 2. 認證與授權
- 修改預設密碼
- 使用強密碼策略
- 考慮使用 TACACS+/RADIUS

### 3. TFTP 安全
- TFTP 無加密，僅用於初始部署
- 考慮使用 HTTPS 替代（需要設備支援）

### 4. API 安全
- 在生產環境添加 API 認證
- 使用 HTTPS
- 限制訪問來源 IP

## 📚 進階功能

### 1. 基於角色的配置模板

```python
# 在 Provisioning Server 中
if device_role == "edge_router":
    config_template = "edge_router_template.j2"
elif device_role == "access_switch":
    config_template = "access_switch_template.j2"
```

### 2. 自動軟體升級

在 ZTP 腳本中添加：
```python
# 檢查 IOS 版本
# 如需要，從 TFTP 下載新版本
# 執行升級
```

### 3. 合規性檢查

```python
# 檢查設備配置是否符合企業標準
# 自動修正偏差
# 生成合規性報告
```

## 📖 相關資源

- [Cisco ZTP 官方文檔](https://www.cisco.com/c/en/us/td/docs/ios-xml/ios/prog/configuration/169/b_169_programmability_cg/zero_touch_provisioning.html)
- [ISC DHCP 文檔](https://kb.isc.org/docs/isc-dhcp-44-manual-pages-dhcpdconf)
- [Flask 官方文檔](https://flask.palletsprojects.com/)
- [Ansible 網路自動化](https://docs.ansible.com/ansible/latest/network/index.html)

## 🤝 貢獻

歡迎提交 Issues 和 Pull Requests！

## 📝 許可證

MIT License

---

**注意事項：**
- 本方案適用於實驗室環境
- 生產環境部署前請進行充分測試
- 建議在隔離網路中進行 ZTP
- 定期備份 DHCP 和 Provisioning Server 配置

---

**作者**: Riven-dev1030
**版本**: 1.0
**最後更新**: 2025-11-11
