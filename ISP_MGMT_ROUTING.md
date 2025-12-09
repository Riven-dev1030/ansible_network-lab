# ISP 管理网络路由配置指南

## 概述

本文档说明如何配置 ISP 路由器，使流量能够通过管理网络 (mg) 进行路由。

## 网络拓扑

```
          Internet (Net)
                │
          ┌─────┴─────┐
          │  mg_sw1   │ (192.168.1.1)
          │  (e0/1)   │
          └─────┬─────┘
                │ (e0/0)
          ┌─────┴────────────────┐
          │                      │
    ┌─────▼──────┐         ┌─────▼──────┐
    │   ISP1     │         │   ISP2     │
    │192.168.1.31│         │192.168.1.32│
    │  (Gi0/2)   │         │  (Gi0/2)   │
    └─────┬──────┘         └─────┬──────┘
          │                      │
    ┌─────▼──────┐         ┌─────▼──────┐
    │     R1     │         │     R2     │
    │  (Gi0/1)   │         │  (Gi0/1)   │
    └────────────┘         └────────────┘
```

## 管理网络配置

### 网络地址规划

- **管理网络**: 192.168.1.0/24
- **管理网关**: 192.168.1.1 (mg_sw1)
- **ISP1 管理 IP**: 192.168.1.31
- **ISP2 管理 IP**: 192.168.1.32
- **其他设备**: 192.168.1.11-42

## 配置目标

实现以下路由需求：

1. **ISP → 内部网络**: ISP 路由器能够通过管理网络访问内部网络 (10.10.0.0/16, 10.110.0.0/16)
2. **内部网络 → ISP**: 内部设备能够通过管理网络访问 ISP 路由器
3. **流量隔离**: 生产流量和管理流量分离

## 配置步骤

### 方法 1: 使用 Ansible Playbook (推荐)

运行以下命令应用配置：

```bash
# 执行 ISP 管理网络路由配置
ansible-playbook playbooks/s9_isp_mgmt_routing.yml

# 或者使用完整部署
ansible-playbook playbooks/deploy_all.yml
```

### 方法 2: 手动配置

#### 在 ISP1 上配置

```cisco
! 1. 配置管理网络接口
interface GigabitEthernet0/2
 description Management Network - mg_sw1
 ip address 192.168.1.31 255.255.255.0
 no shutdown
exit

! 2. 配置到内部网络的静态路由 (较低优先级)
! Administrative Distance = 250 (低于 BGP 的 200/20)
ip route 10.10.0.0 255.255.0.0 192.168.1.1 250
ip route 10.110.0.0 255.255.0.0 192.168.1.1 250

! 3. (可选) 配置访问控制
ip access-list standard MGMT_ACCESS
 permit 192.168.1.0 0.0.0.255
 permit 10.10.0.0 0.0.255.255
 permit 10.110.0.0 0.0.255.255
 deny any log
exit

interface GigabitEthernet0/2
 ip access-group MGMT_ACCESS in
exit

! 4. 保存配置
write memory
```

#### 在 ISP2 上配置

```cisco
! 1. 配置管理网络接口
interface GigabitEthernet0/2
 description Management Network - mg_sw19
 ip address 192.168.1.32 255.255.255.0
 no shutdown
exit

! 2. 配置到内部网络的静态路由
ip route 10.10.0.0 255.255.0.0 192.168.1.1 250
ip route 10.110.0.0 255.255.0.0 192.168.1.1 250

! 3. (可选) 配置访问控制
ip access-list standard MGMT_ACCESS
 permit 192.168.1.0 0.0.0.255
 permit 10.10.0.0 0.0.255.255
 permit 10.110.0.0 0.0.255.255
 deny any log
exit

interface GigabitEthernet0/2
 ip access-group MGMT_ACCESS in
exit

! 4. 保存配置
write memory
```

#### 在管理交换机 (mg_sw1/SW1) 上配置 (如果需要)

```cisco
! 如果 mg_sw1 是 Layer 3 交换机
ip routing

interface Vlan1
 ip address 192.168.1.1 255.255.255.0
 no shutdown
exit

! 配置到 ISP 公网的静态路由
ip route 203.0.113.0 255.255.255.252 192.168.1.31
ip route 198.51.100.0 255.255.255.252 192.168.1.32

! 配置到内部网络的路由 (通过 R1/R2)
ip route 10.10.0.0 255.255.0.0 192.168.1.11
ip route 10.110.0.0 255.255.0.0 192.168.1.11

write memory
```

#### 在 HQ 路由器 (R1/R2) 上配置回程路由

```cisco
! 在 R1 和 R2 上配置
ip route 192.168.1.0 255.255.255.0 10.10.99.1 250

write memory
```

## 验证配置

### 1. 检查 ISP 接口状态

```bash
# 在 ISP1/ISP2 上
show ip interface brief | include GigabitEthernet0/2
```

预期输出：
```
GigabitEthernet0/2     192.168.1.31    YES manual up                    up
```

### 2. 检查路由表

```bash
# 在 ISP1/ISP2 上
show ip route | include 10.10.0.0|10.110.0.0|192.168.1.0
```

预期输出：
```
S    10.10.0.0/16 [250/0] via 192.168.1.1
S    10.110.0.0/16 [250/0] via 192.168.1.1
C    192.168.1.0/24 is directly connected, GigabitEthernet0/2
```

### 3. 测试连通性

```bash
# 从 ISP1 ping 管理网关
ping 192.168.1.1

# 从 ISP1 ping 内部设备 (通过管理网络)
ping 192.168.1.11 source 192.168.1.31

# 从 ISP1 测试到内部网络的路由
traceroute 10.10.10.1 source 192.168.1.31
```

### 4. 使用 Ansible 验证

```bash
ansible-playbook playbooks/s9_isp_mgmt_routing.yml --tags verify
```

## 路由优先级说明

配置使用了不同的 Administrative Distance (AD) 来控制路由选择：

| 路由类型 | Administrative Distance | 用途 |
|---------|------------------------|------|
| 直连路由 | 0 | 最高优先级 |
| 静态路由 (默认) | 1 | 生产流量 |
| eBGP | 20 | 生产流量 (ISP 连接) |
| OSPF | 110 | 内部路由 |
| 静态路由 (备份) | **250** | 管理网络备份路由 |

**关键点**: 通过设置 AD=250，管理网络路由只在生产路由不可用时才会被使用。

## 流量流向

### 场景 1: 正常生产流量 (通过 BGP)

```
Client → R1/R2 → ISP1/ISP2 (via Gi0/1) → Internet
```

### 场景 2: 管理流量 (通过管理网络)

```
ISP1 (Gi0/2) → mg_sw1 → 内部设备 (192.168.1.x)
```

### 场景 3: 生产路由故障时的备份路由

```
ISP1 (Gi0/2) → mg_sw1 → R1/R2 → 内部网络 (10.10.x.x)
```

## 安全考虑

1. **访问控制列表 (ACL)**: 限制管理接口只接受来自授权网络的流量
2. **流量隔离**: 生产流量和管理流量使用不同接口
3. **监控**: 建议配置 syslog 监控异常流量
4. **防火墙规则**: 在生产环境中应添加更严格的防火墙规则

## 故障排除

### 问题 1: ISP 无法访问内部网络

**检查项**:
```bash
# 1. 检查接口状态
show ip interface brief

# 2. 检查路由表
show ip route 10.10.0.0

# 3. 检查 ACL
show ip access-lists

# 4. 测试连通性
ping 192.168.1.1
```

### 问题 2: 路由冲突

**解决方案**:
- 检查 Administrative Distance 设置
- 确保管理网络路由的 AD 值较高 (250)
- 使用 `show ip route 10.10.0.0` 查看当前活动路由

### 问题 3: ACL 阻止流量

**解决方案**:
```bash
# 查看 ACL 日志
show logging | include MGMT_ACCESS

# 临时禁用 ACL 测试
interface GigabitEthernet0/2
 no ip access-group MGMT_ACCESS in
```

## 配置文件位置

- **Playbook**: `playbooks/s9_isp_mgmt_routing.yml`
- **Inventory**: `inventory/hosts.yml`
- **变量**: `group_vars/all.yml`

## 相关文档

- [网络拓扑图](TOPOLOGY_ASCII.txt)
- [架构文档](ARCHITECTURE.md)
- [部署指南](README.md)

## 注意事项

1. **生产环境**: 在生产环境部署前，请在测试环境充分测试
2. **备份配置**: 部署前务必备份现有配置
3. **变更窗口**: 建议在维护窗口期间执行配置变更
4. **回滚计划**: 准备回滚脚本以便快速恢复

## 更新日志

- 2024-12-09: 初始版本 - 添加 ISP 管理网络路由配置
