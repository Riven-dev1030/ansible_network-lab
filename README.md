# Ansible Network Lab - 企業網路模擬實驗室

[![Ansible](https://img.shields.io/badge/Ansible-2.10%2B-red.svg)](https://www.ansible.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

這是一個完整的企業網路自動化部署項目，使用 Ansible 自動配置包含 10 台設備的企業網路實驗環境。

## 📋 項目簡介

本項目基於 **企業網路模擬 Lab 指南**，使用 Ansible 自動化部署完整的企業網路環境，包含：

### 🏢 拓樸架構
- **總部 (HQ)**：R1, R2 (HSRP 高可用), R3 (DMZ/ABR), SW1
- **分公司 (Branch)**：BR1, BR-SW, Host-BR
- **ISP**：ISP1 (AS65001), ISP2 (AS65002)
- **伺服器**：WebSrv (DMZ)
  - **註**: LogSrv 當前未部署，VLAN 60 保留供未來使用

### ✅ 核心功能
- **HSRP** - 高可用閘道 (R1/R2)
- **VLAN 間路由** - 多 VLAN 網段隔離
- **OSPF 多區域** - Area 0/50/10 (含 stub + MD5 認證)
- **BGP eBGP** - 雙 ISP 冗餘連接
- **GRE 隧道** - 總部與分公司 VPN
- **ACL** - DMZ 安全防護
- **本地日誌** - 設備本地緩衝日誌（可擴展為集中式 Syslog）

### 🌐 網路規劃
```
HQ VLAN:
  - VLAN 10 (User):    10.10.10.0/24  → VIP: 10.10.10.254
  - VLAN 20 (IT):      10.10.20.0/24  → VIP: 10.10.20.254
  - VLAN 50 (DMZ):     10.10.50.0/24  → GW:  10.10.50.1
  - VLAN 60 (Log):     10.10.60.0/24  → VIP: 10.10.60.254
  - VLAN 99 (Transit): 10.10.99.0/24

Branch:
  - VLAN 110:          10.110.10.0/24 → GW:  10.110.10.254

Tunnel:
  - GRE Overlay:       172.16.10.0/30
  - Underlay:          100.64.1.0/30
```

## 🚀 快速開始

### 前置要求

- **Python** 3.8+
- **Ansible** 2.10+
- **網路設備** Cisco IOS (IOL/VIRL/EVE-NG)
- **RAM**: 約 2.5-3 GB (L3: 256-384MB, L2: 192MB)

### 安裝步驟

1. **克隆倉庫**
```bash
git clone https://github.com/Riven-dev1030/ansible_network-lab.git
cd ansible_network-lab
```

2. **安裝依賴**
```bash
pip install -r requirements.txt
```

3. **配置設備 IP**
編輯 `inventory/hosts.yml`，更新各設備的管理 IP：
```yaml
R1:
  ansible_host: 192.168.1.11  # 修改為實際 IP
```

4. **配置認證資訊** (可選，使用 Ansible Vault)
```bash
ansible-vault create group_vars/vault.yml
```
內容：
```yaml
vault_ansible_password: "your_device_password"
```

5. **測試連接**
```bash
ansible all -m cisco.ios.ios_command -a "commands='show version'" --one-line
```

## 📖 使用方法

### 方法 1: 使用快速開始腳本 (推薦)
```bash
./quickstart.sh
```
選單選項：
1. 完整部署 (S0-S8 全部階段)
2. 分階段部署 (逐步執行)
3. 僅驗證 (不部署)
4. 檢查連接
5. 重置網路 (清除所有配置)

### 方法 2: 手動執行 Playbooks

#### 完整部署
```bash
ansible-playbook playbooks/deploy_all.yml
```

#### 分階段部署
```bash
# S0: 準備與基線
ansible-playbook playbooks/s0_preparation.yml

# S1: HQ L2/L3 與 HSRP
ansible-playbook playbooks/s1_hq_vlan_hsrp.yml

# S2: DMZ 與 R3 接入
ansible-playbook playbooks/s2_dmz_r3.yml

# S3: OSPF 聚合預設
ansible-playbook playbooks/s3_ospf_summary.yml

# S4: GRE Underlay 與 Tunnel
ansible-playbook playbooks/s4_gre_tunnel.yml

# S5: 分公司 LAN
ansible-playbook playbooks/s5_branch_lan.yml

# S6: eBGP 對上游
ansible-playbook playbooks/s6_ebgp.yml

# S7: NAT 與 ACL (選配)
ansible-playbook playbooks/s7_nat_acl.yml --tags scenario_a

# S8: 可觀測性與日誌
ansible-playbook playbooks/s8_observability.yml
```

#### 驗證部署
```bash
ansible-playbook playbooks/verify_deployment.yml
```

#### 重置網路
```bash
# 清除所有配置，回到初始狀態（保留 SSH/Telnet 管理連接）
ansible-playbook playbooks/reset_network.yml
```

**重置功能說明：**
- ✅ **保留項目**：VTY Lines (SSH/Telnet 管理)、Console 設定、認證資訊
- ❌ **清除項目**：所有路由協定、介面配置、VLAN、ACL、NAT、HSRP、日誌、Hostname 等
- 🔄 **用途**：將網路設備恢復到初始狀態，可重新進行完整部署

## 📂 項目結構

```
ansible_network-lab/
├── README.md                    # 專案說明
├── ansible.cfg                  # Ansible 配置
├── requirements.txt             # Python 依賴
├── quickstart.sh               # 快速開始腳本
├── .gitignore                   # Git 忽略文件
│
├── inventory/
│   └── hosts.yml               # 設備清單
│
├── group_vars/
│   ├── all.yml                 # 全局變量 (網路規劃)
│   └── hq_routers.yml          # HQ 路由器變量
│
├── host_vars/                   # 主機特定變量 (可選)
│
├── playbooks/
│   ├── deploy_all.yml          # 主 Playbook
│   ├── s0_preparation.yml      # S0: 準備
│   ├── s1_hq_vlan_hsrp.yml     # S1: VLAN & HSRP
│   ├── s2_dmz_r3.yml           # S2: DMZ
│   ├── s3_ospf_summary.yml     # S3: OSPF 聚合
│   ├── s4_gre_tunnel.yml       # S4: GRE
│   ├── s5_branch_lan.yml       # S5: 分公司
│   ├── s6_ebgp.yml             # S6: BGP
│   ├── s7_nat_acl.yml          # S7: NAT/ACL
│   ├── s8_observability.yml    # S8: 日誌
│   ├── verify_deployment.yml   # 驗證腳本
│   └── reset_network.yml       # 網路重置
│
└── roles/                       # Ansible Roles (未來擴展)
```

## ✅ 驗證清單

部署完成後，請驗證以下項目：

### A. HSRP 與 VLAN 間路由
- [ ] R1 = Active, R2 = Standby
- [ ] VIP 分別為 .254
- [ ] 跨 VLAN ping 通

### B. OSPF
- [ ] Area 0/50/10 鄰居均為 FULL
- [ ] R1/R2 只見 10.110.0.0/16 聚合路由

### C. GRE 隧道
- [ ] Tunnel0 up/up
- [ ] R3 ↔ BR1 互 ping 通
- [ ] MD5 認證啟用

### D. eBGP
- [ ] R1/R2 與 ISP 為 Established
- [ ] 對外只公告聚合路由

### E. 預設路由
- [ ] HQ 內部有 0.0.0.0/0
- [ ] 分公司能 ping 外部

### F. 高可用測試
- [ ] HSRP 切換測試
- [ ] GRE 隧道故障測試

## 🎯 進階功能

### 標籤 (Tags) 使用
```bash
# 僅執行 HSRP 配置
ansible-playbook playbooks/s1_hq_vlan_hsrp.yml --tags hsrp

# 跳過可選功能
ansible-playbook playbooks/deploy_all.yml --skip-tags optional

# 僅執行 NAT 情境 A
ansible-playbook playbooks/s7_nat_acl.yml --tags scenario_a
```

### Dry Run 模式
```bash
# 檢查變更但不實際執行
ansible-playbook playbooks/deploy_all.yml --check
```

### 詳細輸出
```bash
# 顯示詳細執行過程
ansible-playbook playbooks/deploy_all.yml -v
ansible-playbook playbooks/deploy_all.yml -vv   # 更詳細
ansible-playbook playbooks/deploy_all.yml -vvv  # 最詳細 (含 debug)
```

## 🔧 故障排除

### 連接問題
```bash
# 測試單一設備連接
ansible R1 -m ping

# 檢查認證
ansible R1 -m cisco.ios.ios_command -a "commands='show version'"
```

### 配置問題
```bash
# 檢查設備配置
ansible-playbook playbooks/verify_deployment.yml

# 查看 Ansible 日誌
tail -f ansible.log
```

### 常見錯誤
1. **連接超時**: 檢查 `ansible_host` IP 是否正確
2. **認證失敗**: 確認密碼和 enable 密碼
3. **模組未找到**: 執行 `pip install -r requirements.txt`

## 📚 參考文檔

- [企業網路模擬 Lab 指南 PDF](企業網路模擬%20Lab%20指南（重排版）.pdf)
- [Ansible 網路模組文檔](https://docs.ansible.com/ansible/latest/network/index.html)
- [Cisco IOS 配置指南](https://www.cisco.com/c/en/us/support/ios-nx-os-software/ios-15-4m-t/products-installation-and-configuration-guides-list.html)

## 🤝 貢獻

歡迎提交 Issues 和 Pull Requests！

## 📄 許可證

MIT License

## 👤 作者

Riven-dev1030

## 📞 聯繫方式

如有問題，請通過 GitHub Issues 聯繫。

---

**注意事項：**
- 本項目適用於實驗室環境，不建議直接用於生產環境
- 請確保在隔離的網路環境中測試
- 定期備份設備配置
- IOL 某些功能（如 NAT）可能不穩定，請參考 PDF 附錄 A 使用 Linux 替代方案
