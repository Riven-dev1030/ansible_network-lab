# Ethernet 接口向下兼容说明

## 概述

本分支 (`claude/ethernet-compatibility-011CV1vQMSoPLhgPqeaHMEdu`) 是为了适配使用旧版 **Ethernet** 接口的测试环境而创建的向下兼容版本。

## 变更内容

### 接口类型更改

所有原本使用 `GigabitEthernet` 的接口已全部替换为 `Ethernet`，以适配不支持千兆接口命名的旧设备。

### 修改的文件

1. **配置变量文件**
   - `group_vars/hq_routers.yml` - 更新所有接口定义

2. **Playbook 文件**
   - `playbooks/s1_hq_vlan_hsrp.yml` - HQ VLAN & HSRP 配置
   - `playbooks/s2_dmz_r3.yml` - DMZ 与 R3 接入配置
   - `playbooks/s4_gre_tunnel.yml` - GRE Tunnel 配置
   - `playbooks/s5_branch_lan.yml` - 分公司 LAN 配置
   - `playbooks/s6_ebgp.yml` - eBGP 对上游配置
   - `playbooks/s7_nat_acl.yml` - NAT 与 ACL 配置

### 接口映射对照表

| 原始接口 (GigabitEthernet) | 兼容接口 (Ethernet) | 用途 |
|---------------------------|-------------------|------|
| GigabitEthernet0/0 | Ethernet0/0 | 主干/Trunk 接口 |
| GigabitEthernet0/1 | Ethernet0/1 | WAN/上行接口 |
| GigabitEthernet0/2 | Ethernet0/2 | 交换机互联 |
| GigabitEthernet0/3 | Ethernet0/3 | 其他连接 |
| GigabitEthernet0/4 | Ethernet0/4 | Access 端口 |
| GigabitEthernet0/0.xx | Ethernet0/0.xx | 子接口 (VLAN) |

## 使用场景

### 适用环境
- 使用旧版 Cisco 路由器/交换机 (如 2600, 2800 系列)
- 使用 IOL/IOU 旧版镜像
- 使用不支持 GigabitEthernet 命名的模拟器
- 物理实验环境只有 FastEthernet/Ethernet 接口

### 不适用环境
- 新版 Cisco 设备 (ISR 4000, Catalyst 9000 系列等)
- 已明确支持 GigabitEthernet 的 EVE-NG/GNS3 环境
- 生产环境 (建议使用千兆接口)

## 技术影响

### 保持不变
- ✅ 所有网络拓扑逻辑保持一致
- ✅ VLAN 配置、HSRP、OSPF、BGP 等协议配置不变
- ✅ IP 地址规划完全相同
- ✅ GRE Tunnel、NAT、ACL 功能不受影响

### 需要注意
- ⚠️ 接口速度可能受限于物理接口类型 (10/100Mbps vs 1000Mbps)
- ⚠️ 确保你的设备支持 `Ethernet0/x` 命名格式
- ⚠️ 某些旧设备可能使用 `FastEthernet0/x` 而非 `Ethernet0/x`

## 验证步骤

执行以下命令确认接口配置正确：

```bash
# 在路由器/交换机上
show ip interface brief
show interfaces status
show running-config | include interface

# 使用 Ansible 验证
ansible-playbook playbooks/verify_deployment.yml
```

## 迁移指南

### 从 GigabitEthernet 迁移到 Ethernet

如果你需要在现有环境中应用这些更改：

1. **备份当前配置**
   ```bash
   ansible-playbook -i inventory/hosts.yml playbooks/backup_configs.yml
   ```

2. **切换到此分支**
   ```bash
   git checkout claude/ethernet-compatibility-011CV1vQMSoPLhgPqeaHMEdu
   ```

3. **检查设备接口**
   ```bash
   ansible cisco_devices -m cisco.ios.ios_command -a "commands='show ip interface brief'"
   ```

4. **部署配置**
   ```bash
   ansible-playbook playbooks/deploy_all.yml
   ```

### 从 Ethernet 迁移回 GigabitEthernet

切换回主分支或原始分支：
```bash
git checkout main  # 或原始分支名
```

## 故障排除

### 问题：接口名称不匹配
```
错误: Interface Ethernet0/0 not found
```
**解决方案**: 检查设备实际接口命名，可能需要使用 `FastEthernet` 替代 `Ethernet`

### 问题：子接口无法创建
```
错误: Invalid interface Ethernet0/0.10
```
**解决方案**: 确保主接口 `Ethernet0/0` 处于 up 状态且配置为 trunk 模式

### 问题：VLAN Trunk 不通
```
错误: VLAN 10 not forwarding
```
**解决方案**:
1. 检查 `switchport mode trunk`
2. 验证 `switchport trunk allowed vlan`
3. 确认两端接口都是 up/up 状态

## 技术支持

如遇问题，请检查：
1. 设备型号和 IOS 版本
2. 接口实际命名规则 (`show interfaces`)
3. Ansible 执行日志
4. 设备配置日志 (`show running-config`)

## 变更历史

- **2025-12-05**: 初始创建，将所有 GigabitEthernet 替换为 Ethernet
- 分支基于: `claude/capabilities-overview-011CV1vQMSoPLhgPqeaHMEdu`

---

**注意**: 此分支专为向下兼容而设计。如果你的环境支持 GigabitEthernet，建议使用主分支以获得更好的性能。
