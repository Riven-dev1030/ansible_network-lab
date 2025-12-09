# ISP 管理網路路由配置指南

## 概述

本文檔說明如何配置 ISP 路由器，使流量能夠透過管理網路 (mg) 進行路由。

**架構說明**: mg_sw1 和 mg_sw19 為純 Layer 2 交換機（無 IP 位址），透過 R1/R2 作為網關。

## 網路拓撲

```
          Internet (Net)
                │
          ┌─────┴─────────────┐
          │                   │
    mg_sw1 (L2)          mg_sw19 (L2)  ← 純 L2 交換機
       │                      │
       │   管理網路 192.168.1.0/24 (同一個 L2 域)
       │                      │
    ┌──┴────┐              ┌──┴────┐
    │ ISP1  │              │ ISP2  │
    │ .31   │              │ .32   │
    │(Gi0/2)│              │(Gi0/2)│
    └───────┘              └───────┘
                │
         (管理網路 L2)
                │
    ┌───────────┴───────────┐
    │                       │
┌───▼────┐              ┌───▼────┐
│   R1   │◄────生產─────►│   R2   │
│  .11   │   網路連接    │  .12   │
│ (Gi0/3)│  (Gi0/0-1)    │ (Gi0/3)│
└────┬───┘              └────┬───┘
     │                       │
  內部網路              內部網路
10.10.x.x            10.10.x.x
```

## 管理網路配置

### 網路位址規劃

- **管理網路**: 192.168.1.0/24
- **L2 交換機**: mg_sw1, mg_sw19 (無 IP，純 L2 轉發)
- **ISP1 管理 IP**: 192.168.1.31 → 網關: 192.168.1.11 (R1)
- **ISP2 管理 IP**: 192.168.1.32 → 網關: 192.168.1.12 (R2)
- **R1 管理 IP**: 192.168.1.11 (Gi0/3)
- **R2 管理 IP**: 192.168.1.12 (Gi0/3)
- **其他設備**: 192.168.1.13-30

## 配置目標

實現以下路由需求：

1. **配置 R1/R2 管理網路介面**: 在 Gi0/3 上配置管理網路 IP
2. **ISP → 內部網路**: ISP 路由器透過 R1/R2 作為網關存取內部網路 (10.10.0.0/16, 10.110.0.0/16)
3. **內部網路 → ISP**: 內部設備透過 R1/R2 存取 ISP 路由器
4. **流量隔離**: 生產流量（Gi0/0-1）和管理流量（Gi0/3）使用不同介面
5. **L2 架構**: mg_sw1 和 mg_sw19 無需配置，純 L2 轉發

## 配置步驟

### 方法 1: 使用 Ansible Playbook (推薦)

執行以下命令套用配置：

```bash
# 執行 ISP 管理網路路由配置
ansible-playbook playbooks/s9_isp_mgmt_routing.yml

# 或者使用完整部署
ansible-playbook playbooks/deploy_all.yml
```

### 方法 2: 手動配置

#### 步驟 1: 配置 R1 管理網路介面

```cisco
! 在 R1 上配置
interface GigabitEthernet0/3
 description Management Network Interface
 ip address 192.168.1.11 255.255.255.0
 no shutdown
exit

write memory
```

#### 步驟 2: 配置 R2 管理網路介面

```cisco
! 在 R2 上配置
interface GigabitEthernet0/3
 description Management Network Interface
 ip address 192.168.1.12 255.255.255.0
 no shutdown
exit

write memory
```

#### 步驟 3: 配置 ISP1

```cisco
! 1. 配置管理網路介面
interface GigabitEthernet0/2
 description Management Network - via mg_sw1 (L2)
 ip address 192.168.1.31 255.255.255.0
 no shutdown
exit

! 2. 配置到內部網路的靜態路由 (透過 R1)
! Administrative Distance = 250 (低於 BGP 的 200/20)
ip route 10.10.0.0 255.255.0.0 192.168.1.11 250
ip route 10.110.0.0 255.255.0.0 192.168.1.11 250

! 3. (可選) 配置存取控制
ip access-list standard MGMT_ACCESS
 permit 192.168.1.0 0.0.0.255
 permit 10.10.0.0 0.0.255.255
 permit 10.110.0.0 0.0.255.255
 deny any log
exit

interface GigabitEthernet0/2
 ip access-group MGMT_ACCESS in
exit

! 4. 儲存配置
write memory
```

#### 步驟 4: 配置 ISP2

```cisco
! 1. 配置管理網路介面
interface GigabitEthernet0/2
 description Management Network - via mg_sw19 (L2)
 ip address 192.168.1.32 255.255.255.0
 no shutdown
exit

! 2. 配置到內部網路的靜態路由 (透過 R2)
ip route 10.10.0.0 255.255.0.0 192.168.1.12 250
ip route 10.110.0.0 255.255.0.0 192.168.1.12 250

! 3. (可選) 配置存取控制
ip access-list standard MGMT_ACCESS
 permit 192.168.1.0 0.0.0.255
 permit 10.10.0.0 0.0.255.255
 permit 10.110.0.0 0.0.255.255
 deny any log
exit

interface GigabitEthernet0/2
 ip access-group MGMT_ACCESS in
exit

! 4. 儲存配置
write memory
```

**注意**: mg_sw1 和 mg_sw19 為純 L2 交換機，無需任何配置。

## 驗證配置

### 1. 檢查 R1/R2 管理介面狀態

```bash
# 在 R1/R2 上
show ip interface brief | include GigabitEthernet0/3
```

預期輸出：
```
GigabitEthernet0/3     192.168.1.11    YES manual up                    up
```

### 2. 檢查 ISP 介面狀態

```bash
# 在 ISP1 上
show ip interface brief | include GigabitEthernet0/2
```

預期輸出：
```
GigabitEthernet0/2     192.168.1.31    YES manual up                    up
```

### 3. 檢查路由表

```bash
# 在 ISP1 上
show ip route | include 10.10.0.0|10.110.0.0|192.168.1.0
```

預期輸出：
```
S    10.10.0.0/16 [250/0] via 192.168.1.11
S    10.110.0.0/16 [250/0] via 192.168.1.11
C    192.168.1.0/24 is directly connected, GigabitEthernet0/2
```

### 4. 測試連通性

```bash
# 從 ISP1 ping R1 (管理網關)
ping 192.168.1.11

# 從 ISP1 ping R2
ping 192.168.1.12 source 192.168.1.31

# 從 ISP1 測試到內部網路的路由
ping 10.10.10.1 source 192.168.1.31
traceroute 10.10.10.1 source 192.168.1.31
```

### 5. 使用 Ansible 驗證

```bash
ansible-playbook playbooks/s9_isp_mgmt_routing.yml
```

## 路由優先權說明

配置使用了不同的 Administrative Distance (AD) 來控制路由選擇：

| 路由類型 | Administrative Distance | 用途 |
|---------|------------------------|------|
| 直連路由 | 0 | 最高優先權 |
| 靜態路由 (預設) | 1 | 生產流量 |
| eBGP | 20 | 生產流量 (ISP 連接) |
| OSPF | 110 | 內部路由 |
| 靜態路由 (備份) | **250** | 管理網路備份路由 |

**關鍵點**: 透過設定 AD=250，管理網路路由只在生產路由不可用時才會被使用。

## 流量流向

### 場景 1: 正常生產流量 (透過 BGP)

```
Client (10.10.10.x) → R1/R2 (Gi0/0-1) → ISP1/ISP2 (Gi0/1) → Internet
```

### 場景 2: 管理流量 (透過管理網路 L2)

```
ISP1 (Gi0/2, .31) → mg_sw1 (L2) → R1 (Gi0/3, .11) → 內部設備
ISP2 (Gi0/2, .32) → mg_sw19 (L2) → R2 (Gi0/3, .12) → 內部設備
```

### 場景 3: 生產路由故障時的備份路由

```
ISP1 (Gi0/2, .31) → mg_sw1 (L2) → R1 (Gi0/3, .11) → R1 內部介面 → 內部網路 (10.10.x.x)
```

### 關鍵點

1. **L2 轉發**: mg_sw1 和 mg_sw19 只做 L2 轉發，不參與路由決策
2. **多條路徑**: ISP1 可以透過 mg_sw1 → R1，ISP2 透過 mg_sw19 → R2
3. **介面隔離**:
   - Gi0/0-1: 生產 BGP 流量
   - Gi0/2: 管理網路介面 (ISP)
   - Gi0/3: 管理網路介面 (R1/R2)

## 安全考量

1. **存取控制列表 (ACL)**: 限制管理介面只接受來自授權網路的流量
2. **流量隔離**: 生產流量和管理流量使用不同介面
3. **監控**: 建議配置 syslog 監控異常流量
4. **防火牆規則**: 在生產環境中應新增更嚴格的防火牆規則

## 故障排除

### 問題 1: ISP 無法存取內部網路

**檢查項**:
```bash
# 1. 檢查介面狀態
show ip interface brief

# 2. 檢查路由表
show ip route 10.10.0.0

# 3. 檢查 ACL
show ip access-lists

# 4. 測試連通性
ping 192.168.1.1
```

### 問題 2: 路由衝突

**解決方案**:
- 檢查 Administrative Distance 設定
- 確保管理網路路由的 AD 值較高 (250)
- 使用 `show ip route 10.10.0.0` 查看目前活動路由

### 問題 3: ACL 阻止流量

**解決方案**:
```bash
# 查看 ACL 日誌
show logging | include MGMT_ACCESS

# 暫時停用 ACL 測試
interface GigabitEthernet0/2
 no ip access-group MGMT_ACCESS in
```

## 配置檔案位置

- **Playbook**: `playbooks/s9_isp_mgmt_routing.yml`
- **Inventory**: `inventory/hosts.yml`
- **變數**: `group_vars/all.yml`

## 相關文件

- [網路拓撲圖](TOPOLOGY_ASCII.txt)
- [架構文件](ARCHITECTURE.md)
- [部署指南](README.md)

## 注意事項

1. **生產環境**: 在生產環境部署前，請在測試環境充分測試
2. **備份配置**: 部署前務必備份現有配置
3. **變更視窗**: 建議在維護視窗期間執行配置變更
4. **回復計畫**: 準備回復腳本以便快速恢復

## 更新日誌

- 2024-12-09: 初始版本 - 新增 ISP 管理網路路由配置
