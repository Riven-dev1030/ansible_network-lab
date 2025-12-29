# Ansible Network Lab 架構圖

## 網路拓撲架構

```mermaid
graph TB
    subgraph Internet["☁️ Internet"]
        ISP1["ISP1<br/>AS 65001<br/>203.0.113.1"]
        ISP2["ISP2<br/>AS 65002<br/>198.51.100.1"]
    end

    subgraph HQ["🏢 總部 (HQ)"]
        subgraph HSRP["HSRP 高可用閘道"]
            R1["R1 (Active)<br/>HSRP Priority: 110<br/>203.0.113.2"]
            R2["R2 (Standby)<br/>HSRP Priority: 100<br/>198.51.100.2"]
        end

        R3["R3 (DMZ/ABR)<br/>100.64.1.1<br/>172.16.10.1"]
        SW1["SW1<br/>Access Switch"]
        BASTION["🔐 BASTION<br/>192.168.1.15<br/>Bastion Router"]

        subgraph VLANs["HQ VLANs"]
            VLAN10["VLAN 10 (User)<br/>10.10.10.0/24<br/>VIP: .254"]
            VLAN20["VLAN 20 (IT)<br/>10.10.20.0/24<br/>VIP: .254"]
            VLAN50["VLAN 50 (DMZ)<br/>10.10.50.0/24<br/>GW: .1"]
            VLAN60["VLAN 60 (Log)<br/>10.10.60.0/24<br/>VIP: .254"]
            VLAN99["VLAN 99 (Transit)<br/>10.10.99.0/24"]
        end

        WebSrv["🖥️ WebSrv<br/>10.10.50.10"]
    end

    subgraph Branch["🏪 分公司 (Branch)"]
        BR1["BR1<br/>100.64.1.2<br/>172.16.10.2"]
        BRSW["BR-SW<br/>Branch Switch"]
        VLAN110["VLAN 110<br/>10.110.10.0/24<br/>GW: .254"]
    end

    subgraph Tunnel["🔒 GRE Tunnel"]
        GRE["Tunnel0<br/>172.16.10.0/30<br/>MD5 認證"]
    end

    %% Internet Connections
    ISP1 -.->|"eBGP<br/>AS 65001"| R1
    ISP2 -.->|"eBGP<br/>AS 65002"| R2

    %% HQ Internal
    R1 <-->|"VLAN 99<br/>Transit"| SW1
    R2 <-->|"VLAN 99<br/>Transit"| SW1
    R3 <-->|"VLAN 99<br/>Transit"| SW1
    BASTION <-->|"VLAN 99<br/>Transit"| SW1

    SW1 --> VLAN10
    SW1 --> VLAN20
    SW1 --> VLAN60
    R3 --> VLAN50

    BASTION -.->|"VLAN 10/20<br/>50/60/99/110<br/>Sub-interfaces"| VLAN10
    BASTION -.->|"MGMT入口<br/>192.168.1.15"| R1

    R1 -.->|"HSRP"| R2

    %% DMZ
    VLAN50 --> WebSrv

    %% GRE Tunnel
    R3 <-->|"Underlay<br/>100.64.1.0/30"| GRE
    GRE <-->|"Overlay<br/>172.16.10.0/30"| BR1

    %% Branch
    BR1 <--> BRSW
    BRSW --> VLAN110

    %% OSPF Areas
    R1 -.->|"OSPF Area 0"| R2
    R1 -.->|"OSPF Area 0"| R3
    R2 -.->|"OSPF Area 0"| R3
    R3 -.->|"OSPF Area 50"| WebSrv
    R3 -.->|"OSPF Area 10<br/>MD5"| BR1

    style ISP1 fill:#ff9999
    style ISP2 fill:#ff9999
    style R1 fill:#99ccff
    style R2 fill:#99ccff
    style R3 fill:#99ccff
    style BR1 fill:#99ccff
    style SW1 fill:#99ff99
    style BRSW fill:#99ff99
    style WebSrv fill:#ffcc99
    style GRE fill:#ffff99
```

## Ansible 主機清單架構

```mermaid
graph LR
    subgraph Ansible["🔧 Ansible 控制節點"]
        Playbooks["Playbooks<br/>(S0-S8)"]
    end

    subgraph Groups["設備群組"]
        subgraph HQGroup["hq"]
            HQRouters["hq_routers<br/>R1, R2, R3"]
            HQSwitches["hq_switches<br/>SW1"]
        end

        subgraph BranchGroup["branch"]
            BranchRouters["branch_routers<br/>BR1"]
            BranchSwitches["branch_switches<br/>BR-SW"]
        end

        ISPGroup["isp<br/>ISP1, ISP2"]
        ServersGroup["servers<br/>WebSrv"]
    end

    subgraph DeviceTypes["設備類型群組"]
        CiscoDevices["cisco_devices<br/>(所有 Cisco 設備)"]
        LinuxDevices["linux_devices<br/>(所有 Linux 設備)"]
    end

    Playbooks -->|管理| HQRouters
    Playbooks -->|管理| HQSwitches
    Playbooks -->|管理| BranchRouters
    Playbooks -->|管理| BranchSwitches
    Playbooks -->|管理| ISPGroup
    Playbooks -->|管理| ServersGroup

    HQRouters --> CiscoDevices
    HQSwitches --> CiscoDevices
    BranchRouters --> CiscoDevices
    BranchSwitches --> CiscoDevices
    ISPGroup --> CiscoDevices
    ServersGroup --> LinuxDevices

    style Playbooks fill:#9999ff
    style HQRouters fill:#99ccff
    style HQSwitches fill:#99ff99
    style BranchRouters fill:#99ccff
    style BranchSwitches fill:#99ff99
    style ISPGroup fill:#ff9999
    style ServersGroup fill:#ffcc99
    style CiscoDevices fill:#ccccff
    style LinuxDevices fill:#ffddcc
```

## 設備詳細資訊

### 總部 (HQ) 設備

| 設備 | 管理 IP | 角色 | 功能 |
|------|---------|------|------|
| **R1** | 192.168.1.11 | HSRP Primary | - HSRP Active (Priority 110)<br/>- eBGP to ISP1<br/>- OSPF Area 0<br/>- VLAN 10/20/60 網關 |
| **R2** | 192.168.1.12 | HSRP Standby | - HSRP Standby (Priority 100)<br/>- eBGP to ISP2<br/>- OSPF Area 0<br/>- VLAN 10/20/60 網關 |
| **R3** | 192.168.1.13 | DMZ/ABR | - OSPF ABR (Area 0/10/50)<br/>- GRE Tunnel Endpoint<br/>- DMZ 網關<br/>- NAT & ACL |
| **SW1** | 192.168.1.21 | Access Switch | - VLAN 10/20/50/60/99<br/>- Trunk to R1/R2/R3 |

### 分公司 (Branch) 設備

| 設備 | 管理 IP | 角色 | 功能 |
|------|---------|------|------|
| **BR1** | 192.168.1.14 | Branch Router | - GRE Tunnel Endpoint<br/>- OSPF Area 10<br/>- VLAN 110 網關 |
| **BR-SW** | 192.168.1.22 | Branch Switch | - VLAN 110 Access<br/>- Trunk to BR1 |

### ISP 設備

| 設備 | 管理 IP | AS 號碼 | 功能 |
|------|---------|---------|------|
| **ISP1** | 192.168.1.31 | AS 65001 | eBGP Peer with R1 |
| **ISP2** | 192.168.1.32 | AS 65002 | eBGP Peer with R2 |

### 跳板機 (Bastion)

| 設備 | 管理 IP | 角色 | 功能 |
|------|---------|------|------|
| **BASTION** | 192.168.1.15 | Bastion Router | - MGMT 網段入口<br/>- 所有 VLAN 連接<br/>- 訪問控制 ACL<br/>- SSH 堡壘 |

### 伺服器

| 設備 | 管理 IP | 內部 IP | 角色 |
|------|---------|---------|------|
| **WebSrv** | 192.168.1.41 | 10.10.50.10 | DMZ Web 伺服器 |

## 網路協定架構

```mermaid
graph TB
    subgraph Protocols["🌐 網路協定層"]
        subgraph L2["Layer 2"]
            VLAN["VLAN<br/>10/20/50/60/99/110"]
            Trunk["802.1Q Trunk"]
        end

        subgraph L3["Layer 3"]
            HSRP_P["HSRP<br/>Groups: 10/20/60"]
            OSPF_P["OSPF<br/>Areas: 0/10/50<br/>MD5 Auth"]
            BGP_P["BGP<br/>AS 65010<br/>eBGP to ISP"]
            GRE_P["GRE<br/>Tunnel0"]
        end

        subgraph Security["Security"]
            ACL_P["ACL<br/>DMZ Protection"]
            NAT_P["NAT<br/>Overload"]
        end

        subgraph Management["Management"]
            Syslog_P["Syslog<br/>10.10.60.10"]
            NTP_P["NTP"]
        end
    end

    VLAN --> HSRP_P
    Trunk --> OSPF_P
    OSPF_P --> BGP_P
    OSPF_P --> GRE_P
    GRE_P --> ACL_P
    BGP_P --> NAT_P

    style VLAN fill:#99ff99
    style HSRP_P fill:#99ccff
    style OSPF_P fill:#99ccff
    style BGP_P fill:#99ccff
    style GRE_P fill:#ffff99
    style ACL_P fill:#ff9999
    style NAT_P fill:#ff9999
    style Syslog_P fill:#ffcc99
```

## OSPF 區域架構

```mermaid
graph TB
    subgraph Area0["OSPF Area 0 (Backbone)"]
        R1_A0["R1"]
        R2_A0["R2"]
        R3_A0["R3"]
        Networks_A0["Networks:<br/>- 10.10.10.0/24 (VLAN 10)<br/>- 10.10.20.0/24 (VLAN 20)<br/>- 10.10.60.0/24 (VLAN 60)<br/>- 10.10.99.0/24 (VLAN 99)"]
    end

    subgraph Area50["OSPF Area 50 (Stub)"]
        R3_A50["R3 (ABR)"]
        Networks_A50["Networks:<br/>- 10.10.50.0/24 (DMZ)<br/>- WebSrv"]
    end

    subgraph Area10["OSPF Area 10 (MD5 Auth)"]
        R3_A10["R3 (ABR)"]
        BR1_A10["BR1"]
        Networks_A10["Networks:<br/>- 172.16.10.0/30 (Tunnel)<br/>- 10.110.10.0/24 (Branch)<br/>Summary: 10.110.0.0/16"]
    end

    R1_A0 <--> R2_A0
    R1_A0 <--> R3_A0
    R2_A0 <--> R3_A0
    R1_A0 --> Networks_A0

    R3_A0 -.->|ABR| R3_A50
    R3_A50 --> Networks_A50

    R3_A0 -.->|ABR| R3_A10
    R3_A10 <-->|"MD5 Auth"| BR1_A10
    BR1_A10 --> Networks_A10

    style Area0 fill:#e6f3ff
    style Area50 fill:#fff4e6
    style Area10 fill:#ffe6f0
```

## IP 地址分配表

### HQ VLANs

| VLAN | 名稱 | 網段 | 網關/VIP | HSRP Group |
|------|------|------|----------|------------|
| 10 | User | 10.10.10.0/24 | 10.10.10.254 | 10 |
| 20 | IT | 10.10.20.0/24 | 10.10.20.254 | 20 |
| 50 | DMZ | 10.10.50.0/24 | 10.10.50.1 (R3) | - |
| 60 | Log | 10.10.60.0/24 | 10.10.60.254 | 60 |
| 99 | Transit | 10.10.99.0/24 | - | - |

### Branch VLANs

| VLAN | 名稱 | 網段 | 網關 |
|------|------|------|------|
| 110 | Branch-LAN | 10.110.10.0/24 | 10.110.10.254 (BR1) |

### Point-to-Point Links

| 連接 | 網段 | R1/R3 IP | R2/BR1/ISP IP |
|------|------|----------|---------------|
| R1 - ISP1 | 203.0.113.0/30 | 203.0.113.2 | 203.0.113.1 |
| R2 - ISP2 | 198.51.100.0/30 | 198.51.100.2 | 198.51.100.1 |
| R3 - BR1 (Underlay) | 100.64.1.0/30 | 100.64.1.1 | 100.64.1.2 |
| R3 - BR1 (Tunnel) | 172.16.10.0/30 | 172.16.10.1 | 172.16.10.2 |

## Ansible 部署流程

```mermaid
graph LR
    S0["S0: 準備與基線<br/>- Hostname<br/>- Logging<br/>- Basic Config"]
    S1["S1: HQ VLAN & HSRP<br/>- VLANs 10/20/60<br/>- HSRP Config"]
    S2["S2: DMZ & R3<br/>- VLAN 50<br/>- R3 Integration"]
    S3["S3: OSPF Summary<br/>- Area 0/50 Config<br/>- Route Summary"]
    S4["S4: GRE Tunnel<br/>- Underlay Config<br/>- Tunnel0 Setup"]
    S5["S5: Branch LAN<br/>- VLAN 110<br/>- BR1 Config"]
    S6["S6: eBGP<br/>- BGP to ISPs<br/>- Route Advertisement"]
    S7["S7: NAT & ACL<br/>- NAT Overload<br/>- DMZ ACL"]
    S8["S8: Observability<br/>- Syslog<br/>- Monitoring"]

    S0 --> S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8

    style S0 fill:#e6f3ff
    style S1 fill:#e6ffe6
    style S2 fill:#ffe6f3
    style S3 fill:#fff4e6
    style S4 fill:#f3e6ff
    style S5 fill:#e6fff4
    style S6 fill:#ffe6e6
    style S7 fill:#f4ffe6
    style S8 fill:#e6f4ff
```

## 高可用性架構

### HSRP 容錯

```mermaid
graph TB
    subgraph Normal["正常運作"]
        R1_N["R1 (Active)<br/>Priority: 110"]
        R2_N["R2 (Standby)<br/>Priority: 100"]
        VIP_N["VIP: x.x.x.254"]

        R1_N -->|"Active"| VIP_N
        R2_N -.->|"Standby"| VIP_N
    end

    subgraph Failover["R1 故障"]
        R1_F["R1 (Down)<br/>❌"]
        R2_F["R2 (Active)<br/>Priority: 100"]
        VIP_F["VIP: x.x.x.254"]

        R1_F -.->|"Down"| VIP_F
        R2_F -->|"Takeover"| VIP_F
    end

    Normal -.->|"R1 Failure"| Failover

    style R1_N fill:#99ff99
    style R2_N fill:#ffff99
    style R1_F fill:#ff9999
    style R2_F fill:#99ff99
```

### BGP 冗餘

```mermaid
graph TB
    subgraph Internal["內部網路"]
        HQ["HQ Network<br/>10.10.0.0/16<br/>10.110.0.0/16"]
    end

    subgraph Edge["邊界路由器"]
        R1_B["R1<br/>Primary Path"]
        R2_B["R2<br/>Backup Path"]
    end

    subgraph External["外部網路"]
        ISP1_B["ISP1<br/>AS 65001"]
        ISP2_B["ISP2<br/>AS 65002"]
        Internet_B["☁️ Internet"]
    end

    HQ <--> R1_B
    HQ <--> R2_B
    R1_B <-->|"eBGP"| ISP1_B
    R2_B <-->|"eBGP"| ISP2_B
    ISP1_B <--> Internet_B
    ISP2_B <--> Internet_B

    style R1_B fill:#99ff99
    style R2_B fill:#99ff99
    style ISP1_B fill:#ffcc99
    style ISP2_B fill:#ffcc99
```

## 安全架構

```mermaid
graph TB
    subgraph Internet_S["☁️ Internet"]
        Threat["外部威脅"]
    end

    subgraph DMZ_Zone["🔒 DMZ Zone (VLAN 50)"]
        WebSrv_S["WebSrv<br/>10.10.50.10"]
        ACL_DMZ["ACL Protection<br/>- Inbound Filtering<br/>- Outbound Control"]
    end

    subgraph Internal_Zone["🏢 Internal Zone"]
        User_VLAN["User VLAN 10<br/>10.10.10.0/24"]
        IT_VLAN["IT VLAN 20<br/>10.10.20.0/24"]
        Log_VLAN["Log VLAN 60<br/>10.10.60.0/24"]
    end

    subgraph Firewall_Layer["🛡️ Firewall Layer"]
        R3_FW["R3<br/>- NAT<br/>- ACL<br/>- OSPF Area 50"]
    end

    Threat -->|"Filtered"| R3_FW
    R3_FW <-->|"ACL"| ACL_DMZ
    ACL_DMZ --> WebSrv_S
    R3_FW <-->|"Protected"| User_VLAN
    R3_FW <-->|"Protected"| IT_VLAN
    R3_FW <-->|"Protected"| Log_VLAN

    style Threat fill:#ff6666
    style ACL_DMZ fill:#ffcc99
    style R3_FW fill:#99ccff
    style User_VLAN fill:#ccffcc
    style IT_VLAN fill:#ccffcc
    style Log_VLAN fill:#ccffcc
```

## 跳板機 (Jump Host)

跳板機的作用是讓 Ansible 能夠從外部網段連接到 MGMT 網段（192.168.1.0/24）。

| 設備 | 管理 IP | 角色 |
|------|---------|------|
| **BASTION** | 192.168.1.100 | Jump Host - MGMT 網段入口 |

### Ansible 配置範例

在 `ansible.cfg` 中設置：

```ini
[defaults]
bastion_host = 192.168.1.100
bastion_user = admin
```

或在 `inventory/hosts.yml` 中設置：

```yaml
all:
  vars:
    ansible_bastion_host: 192.168.1.100
    ansible_bastion_user: admin
```

這樣 Ansible 會自動透過跳板機連接到所有設備。

---

## 總結

這個 Ansible Network Lab 實現了一個完整的企業級網路架構，包含：

### ✅ 核心特性
- **高可用性**: HSRP、雙 ISP 連接
- **安全隔離**: DMZ、ACL、VLAN 隔離、堡壘主機
- **多區域路由**: OSPF (Area 0/10/50) + BGP
- **VPN 連接**: GRE Tunnel with MD5 認證
- **堡壘主機**: BASTION Router 作為 MGMT 網段入口
- **自動化部署**: Ansible 完整自動化配置

### 📊 設備統計
- **路由器**: 5 台 (R1, R2, R3, BR1, ISP1, ISP2) + 1 台跳板機
- **交換機**: 2 台 (SW1, BR-SW)
- **伺服器**: 1 台 (WebSrv)
- **VLANs**: 6 個 + MGMT 網段
- **總計**: 10 台設備 + Jump Host

### 🔧 Ansible 管理
- **Playbooks**: 9 個階段 (S0-S8)
  - S0: 準備與基線
  - S1: HQ VLAN & HSRP
  - S2: DMZ & R3
  - S3: OSPF Summary
  - S4: GRE Tunnel
  - S5: Branch LAN
  - S6: eBGP
  - S7: NAT & ACL
  - S8: Observability
- **群組**: 5 個邏輯群組 (hq, branch, bastion, isp, servers, 設備類型)
- **變數**: 集中管理的網路規劃和配置
- **Jump Host**: BASTION (192.168.1.100) 用於遠端訪問
