# Ethernet 介面向下相容說明

## 概述

本分支 (`claude/ethernet-compatibility-011CV1vQMSoPLhgPqeaHMEdu`) 是為了適配使用舊版 **Ethernet** 介面的測試環境而創建的向下相容版本。

## 變更內容

### 介面類型更改

所有原本使用 `GigabitEthernet` 的介面已全部替換為 `Ethernet`，以適配不支援千兆介面命名的舊設備。

### 修改的檔案

1. **配置變數檔案**
   - `group_vars/hq_routers.yml` - 更新所有介面定義

2. **Playbook 檔案**
   - `playbooks/s1_hq_vlan_hsrp.yml` - HQ VLAN & HSRP 配置
   - `playbooks/s2_dmz_r3.yml` - DMZ 與 R3 接入配置
   - `playbooks/s4_gre_tunnel.yml` - GRE Tunnel 配置
   - `playbooks/s5_branch_lan.yml` - 分公司 LAN 配置
   - `playbooks/s6_ebgp.yml` - eBGP 對上游配置
   - `playbooks/s7_nat_acl.yml` - NAT 與 ACL 配置

### 介面映射對照表

| 原始介面 (GigabitEthernet) | 相容介面 (Ethernet) | 用途 |
|---------------------------|-------------------|------|
| GigabitEthernet0/0 | Ethernet0/0 | 主幹/Trunk 介面 |
| GigabitEthernet0/1 | Ethernet0/1 | WAN/上行介面 |
| GigabitEthernet0/2 | Ethernet0/2 | 交換機互聯 |
| GigabitEthernet0/3 | Ethernet0/3 | 其他連接 |
| GigabitEthernet0/4 | Ethernet0/4 | Access 埠 |
| GigabitEthernet0/0.xx | Ethernet0/0.xx | 子介面 (VLAN) |

## 使用場景

### 適用環境
- 使用舊版 Cisco 路由器/交換機 (如 2600, 2800 系列)
- 使用 IOL/IOU 舊版映像檔
- 使用不支援 GigabitEthernet 命名的模擬器
- 物理實驗環境只有 FastEthernet/Ethernet 介面

### 不適用環境
- 新版 Cisco 設備 (ISR 4000, Catalyst 9000 系列等)
- 已明確支援 GigabitEthernet 的 EVE-NG/GNS3 環境
- 生產環境 (建議使用千兆介面)

## 技術影響

### 保持不變
- ✅ 所有網路拓撲邏輯保持一致
- ✅ VLAN 配置、HSRP、OSPF、BGP 等協定配置不變
- ✅ IP 位址規劃完全相同
- ✅ GRE Tunnel、NAT、ACL 功能不受影響

### 需要注意
- ⚠️ 介面速度可能受限於物理介面類型 (10/100Mbps vs 1000Mbps)
- ⚠️ 確保你的設備支援 `Ethernet0/x` 命名格式
- ⚠️ 某些舊設備可能使用 `FastEthernet0/x` 而非 `Ethernet0/x`

## 驗證步驟

執行以下命令確認介面配置正確：

```bash
# 在路由器/交換機上
show ip interface brief
show interfaces status
show running-config | include interface

# 使用 Ansible 驗證
ansible-playbook playbooks/verify_deployment.yml
```

## 遷移指南

### 從 GigabitEthernet 遷移到 Ethernet

如果你需要在現有環境中應用這些更改：

1. **備份當前配置**
   ```bash
   ansible-playbook -i inventory/hosts.yml playbooks/backup_configs.yml
   ```

2. **切換到此分支**
   ```bash
   git checkout claude/ethernet-compatibility-011CV1vQMSoPLhgPqeaHMEdu
   ```

3. **檢查設備介面**
   ```bash
   ansible cisco_devices -m cisco.ios.ios_command -a "commands='show ip interface brief'"
   ```

4. **部署配置**
   ```bash
   ansible-playbook playbooks/deploy_all.yml
   ```

### 從 Ethernet 遷移回 GigabitEthernet

切換回主分支或原始分支：
```bash
git checkout main  # 或原始分支名
```

## 故障排除

### 問題：介面名稱不匹配
```
錯誤: Interface Ethernet0/0 not found
```
**解決方案**: 檢查設備實際介面命名，可能需要使用 `FastEthernet` 替代 `Ethernet`

### 問題：子介面無法創建
```
錯誤: Invalid interface Ethernet0/0.10
```
**解決方案**: 確保主介面 `Ethernet0/0` 處於 up 狀態且配置為 trunk 模式

### 問題：VLAN Trunk 不通
```
錯誤: VLAN 10 not forwarding
```
**解決方案**:
1. 檢查 `switchport mode trunk`
2. 驗證 `switchport trunk allowed vlan`
3. 確認兩端介面都是 up/up 狀態

## 技術支援

如遇問題，請檢查：
1. 設備型號和 IOS 版本
2. 介面實際命名規則 (`show interfaces`)
3. Ansible 執行日誌
4. 設備配置日誌 (`show running-config`)

## 變更歷史

- **2025-12-05**: 初始創建，將所有 GigabitEthernet 替換為 Ethernet
- 分支基於: `claude/capabilities-overview-011CV1vQMSoPLhgPqeaHMEdu`

---

**注意**: 此分支專為向下相容而設計。如果你的環境支援 GigabitEthernet，建議使用主分支以獲得更好的效能。
