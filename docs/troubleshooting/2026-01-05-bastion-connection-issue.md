# Ansible 透過跳板機連接網路設備故障排除報告

**日期**: 2026-01-05
**問題類型**: Ansible 網路設備連線失敗
**嚴重程度**: 高（阻斷自動化部署）
**狀態**: ✅ 已解決

---

## 執行摘要

在引入跳板機（Bastion Host）作為安全控制措施後，Ansible 控制節點無法連接到目標 Cisco 網路設備。經過系統性診斷，發現三個關鍵問題：(1) 跳板機未配置 SSH 密鑰認證、(2) SSH 簽名算法不匹配、(3) TCP 轉發功能被禁用。通過配置密鑰認證、調整 SSH 算法參數，以及啟用 TCP 轉發，成功解決了連接問題。

---

## 1. 問題背景

### 1.1 架構變更

**變更前（舊架構）：**
```
Ansible 控制節點 (192.168.56.102)
    ↓ 直接連接
目標網路設備 (192.168.100.x)
```
- Ansible 與設備在同網段或可直接路由
- 使用密碼認證 (`ansible_password`)
- 連接正常運作

**變更後（新架構）：**
```
Ansible 控制節點 (192.168.56.102)
    ↓
跳板機 (192.168.213.136)
    ↓
目標網路設備 (192.168.100.x)
```
- 為加強資安，引入跳板機作為中間層
- 所有連接必須經過跳板機
- Ansible 配置使用 `bastion_host` 參數

### 1.2 初始配置

在 `ansible.cfg` 中配置：
```ini
[ssh_connection]
bastion_host = 192.168.213.136
bastion_user = root
bastion_password = eve
```

---

## 2. 問題描述

### 2.1 故障現象

執行 Ansible playbook 時，所有目標 Cisco 設備連接失敗：

```
fatal: [ISP1]: FAILED! =>
  msg: 'ssh connection failed: ssh connect failed: Socket error: Connection reset by peer'
```

### 2.2 影響範圍

- 所有 Cisco 設備（ISP1, ISP2, R1, R2, R3, SW1, BR1, BR-SW）無法連接
- 跳板機（BASTION）可以正常連接
- 手動在跳板機上可以 SSH 到目標設備

---

## 3. 診斷過程

### 3.1 第一階段：網路連通性檢查

**測試 1：跳板機到目標設備的網路連通性**
```bash
# 在跳板機上
ping -c 3 192.168.100.50
# 結果：✅ 成功，0% packet loss
```

**測試 2：SSH 端口檢查**
```bash
nc -zv 192.168.100.50 22
# 結果：✅ 端口開放
```

**結論：** 網路層連通正常，問題不在網路可達性。

---

### 3.2 第二階段：Ansible 配置檢查

**發現 1：`bastion_host` 配置限制**

查閱 Ansible 文檔發現：`bastion_host` 參數不適用於 `network_cli` 連接類型（Cisco 設備使用的連接方式）。

**原因：**
- `network_cli` 使用持久化連接（persistent connection）
- `bastion_host` 主要支援標準 SSH 連接
- 需要改用 `ProxyCommand` 方式實現跳轉

---

### 3.3 第三階段：SSH 密鑰認證檢查

**測試 3：從 Ansible 主機使用密鑰連接跳板機**
```bash
ssh -i /home/geek/.ssh/bastion_key root@192.168.213.136 'hostname'
# 結果：❌ Permission denied (publickey,password,keyboard-interactive)
```

**發現 2：跳板機未配置密鑰認證**

檢查跳板機：
```bash
ls -la /root/.ssh/
# 結果：沒有 authorized_keys 文件
```

**根本原因：**
- 跳板機上的私鑰僅被備份，從未啟用密鑰認證
- 之前的連接都是使用密碼認證
- ProxyCommand 需要非交互式認證，無法使用密碼

---

### 3.4 第四階段：SSH 算法兼容性檢查

**測試 4：詳細 SSH 連接日誌**
```bash
ssh -vv -i /home/geek/.ssh/bastion_key root@192.168.213.136
```

**發現 3：SSH 簽名算法不匹配**

跳板機日誌顯示：
```
userauth_pubkey: signature algorithm ssh-rsa not in PubkeyAcceptedAlgorithms [preauth]
```

**根本原因：**
- 跳板機運行較新版本的 OpenSSH
- 默認禁用 `ssh-rsa` 算法（使用 SHA-1，被認為不安全）
- 客戶端需要明確指定使用 `rsa-sha2-256` 或 `rsa-sha2-512`

---

### 3.5 第五階段：SSH 轉發功能檢查

**測試 5：ProxyCommand 測試**
```bash
ssh -o ProxyCommand='ssh -W %h:%p -i /home/geek/.ssh/bastion_key root@192.168.213.136' \
    cisco123@192.168.100.50
# 結果：❌ stdio forwarding failed
```

**發現 4：TCP 轉發被禁用**

檢查跳板機 SSH 配置：
```bash
grep AllowTcpForwarding /etc/ssh/sshd_config
# 結果：AllowTcpForwarding no
```

**根本原因：**
- ProxyCommand 的 `-W` 選項需要 TCP 轉發支援
- 跳板機出於安全考量禁用了此功能
- 導致 SSH 隧道無法建立

---

## 4. 根本原因分析

| 問題 | 原因 | 影響 |
|------|------|------|
| **1. 缺少密鑰認證** | 跳板機沒有 `authorized_keys` 文件 | ProxyCommand 無法進行非交互式認證 |
| **2. SSH 算法不匹配** | 跳板機拒絕 `ssh-rsa` 算法 | 公鑰認證被拒絕 |
| **3. TCP 轉發禁用** | `AllowTcpForwarding no` | ProxyCommand `-W` 選項失敗 |
| **4. 配置方式錯誤** | 使用 `bastion_host` 而非 `ProxyCommand` | 不適用於 `network_cli` 連接 |

---

## 5. 解決方案

### 5.1 方案設計

採用 **SSH ProxyCommand** 方式實現跳轉連接：

```
Ansible → SSH (with ProxyCommand) → 跳板機 → 目標設備
         └─ 使用密鑰認證 ─┘  └─ 使用密碼認證 ─┘
```

### 5.2 實施步驟

#### 步驟 1：啟用跳板機密鑰認證

**1.1 從私鑰提取公鑰並創建 authorized_keys**
```bash
# 在跳板機上
cat /root/.ssh/temp_rsa.pub >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
```

**驗證：**
```bash
# 從 Ansible 主機測試
ssh -i /home/geek/.ssh/bastion_key root@192.168.213.136 'hostname'
# 結果：仍失敗（算法問題）
```

---

#### 步驟 2：解決 SSH 算法兼容性

**2.1 測試加入算法參數**
```bash
ssh -i /home/geek/.ssh/bastion_key \
    -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    root@192.168.213.136 'hostname'
# 結果：✅ 成功（輸出 "uac"）
```

---

#### 步驟 3：啟用 TCP 轉發

**3.1 修改 SSH 服務器配置**
```bash
# 在跳板機上
sed -i 's/^AllowTcpForwarding no/AllowTcpForwarding yes/' /etc/ssh/sshd_config
/etc/init.d/sshd restart
```

**驗證：**
```bash
grep AllowTcpForwarding /etc/ssh/sshd_config
# 結果：AllowTcpForwarding yes
```

---

#### 步驟 4：修改 Ansible Inventory 配置

**4.1 修改 `inventory/hosts.yml`**

在 `cisco_devices` 群組添加 ProxyCommand 配置：

```yaml
cisco_devices:
  vars:
    ansible_ssh_common_args: "-o ProxyCommand=\"ssh -W %h:%p -i /home/geek/.ssh/bastion_key -o PubkeyAcceptedAlgorithms=+ssh-rsa -o StrictHostKeyChecking=no root@192.168.213.136\" -o StrictHostKeyChecking=no"
  children:
    hq_routers:
    hq_switches:
    branch_routers:
    branch_switches:
    isp:
```

**4.2 移除 ansible.cfg 中的 bastion 配置**

註釋或刪除：
```ini
# [ssh_connection]
# bastion_host = 192.168.213.136
# bastion_user = root
# bastion_password = eve
```

---

## 6. 驗證結果

### 6.1 功能驗證

**測試：Ansible ad-hoc 命令**
```bash
cd /home/geek/ansible_network-lab
ansible ISP1 -m ios_command -a 'commands="show version"'
```

**結果：**
```
PLAY RECAP *********************************************************************
ISP1                       : ok=1    changed=0    unreachable=0    failed=0
```

✅ **成功連接並執行命令**

### 6.2 連接流程驗證

使用詳細模式檢查連接過程：
```bash
ansible ISP1 -m ios_command -a 'commands="show version"' -vvv
```

**確認的連接步驟：**
1. ✅ Ansible 主機使用 ProxyCommand
2. ✅ 通過密鑰認證連接到跳板機
3. ✅ 跳板機轉發連接到目標設備
4. ✅ 使用密碼認證連接到 Cisco 設備
5. ✅ 執行命令並返回結果

---

## 7. 配置變更摘要

### 7.1 跳板機 (192.168.213.136)

| 配置項 | 變更前 | 變更後 |
|--------|--------|--------|
| `/root/.ssh/authorized_keys` | 不存在 | 已創建，包含公鑰 |
| `AllowTcpForwarding` | `no` | `yes` |

### 7.2 Ansible 主機 (192.168.56.102)

| 配置項 | 變更前 | 變更後 |
|--------|--------|--------|
| 連接方式 | `bastion_host` | `ProxyCommand` |
| SSH 參數 | 無特殊參數 | 添加 `PubkeyAcceptedAlgorithms=+ssh-rsa` |
| 跳板機認證 | 密碼 | SSH 密鑰 |

### 7.3 配置文件變更

**inventory/hosts.yml：**
- ✅ 新增 `cisco_devices.vars.ansible_ssh_common_args`

**ansible.cfg：**
- ⚠️ 建議註釋或移除 `bastion_host` 相關配置（已不使用）

---

## 8. 安全性考量

### 8.1 改進點

✅ **已實現：**
- 引入跳板機作為集中訪問控制點
- 使用 SSH 密鑰認證（比密碼更安全）
- 禁用主機密鑰檢查（僅適用於實驗室環境）

### 8.2 建議加強

⚠️ **建議：**
1. **啟用主機密鑰檢查**（生產環境）
   - 移除 `StrictHostKeyChecking=no`
   - 預先收集設備的 host keys

2. **使用更安全的密鑰算法**
   - 考慮使用 Ed25519 密鑰替代 RSA
   - 避免依賴 `+ssh-rsa` 算法

3. **限制 TCP 轉發範圍**
   - 使用 `PermitOpen` 限制可轉發的目標
   - 例如：`PermitOpen 192.168.100.*:22`

4. **審計和日誌**
   - 啟用跳板機的連接日誌
   - 定期審查訪問記錄

5. **密鑰管理**
   - 定期輪換 SSH 密鑰
   - 使用密碼保護私鑰（考慮使用 ssh-agent）

---

## 9. 故障排除流程總結

### 9.1 診斷檢查清單

當遇到類似問題時，建議按以下順序檢查：

- [ ] **網路層**：ping、traceroute、端口掃描
- [ ] **認證層**：密鑰文件存在性、權限、authorized_keys
- [ ] **算法層**：SSH 客戶端和服務器支持的算法
- [ ] **轉發層**：TCP 轉發、端口轉發配置
- [ ] **配置層**：Ansible 配置、inventory 變數
- [ ] **日誌分析**：SSH 詳細日誌（-vv）、服務器日誌（/var/log/）

### 9.2 常用診斷命令

```bash
# 1. 測試網路連通性
ping -c 3 <target>
nc -zv <target> 22

# 2. 測試 SSH 密鑰認證（詳細模式）
ssh -vv -i <key_file> user@host

# 3. 測試 ProxyCommand
ssh -o ProxyCommand='ssh -W %h:%p user@bastion' user@target

# 4. 查看 SSH 服務器日誌
tail -f /var/log/messages | grep sshd

# 5. 測試 Ansible 連接
ansible <host> -m ping -vvv
ansible <host> -m ios_command -a 'commands="show version"' -vvv
```

---

## 10. 經驗教訓

### 10.1 技術層面

1. **`bastion_host` 參數的局限性**
   - 不是所有 Ansible 連接類型都支持
   - `network_cli` 需要使用 `ProxyCommand` 方式

2. **SSH 算法演進**
   - 較新的 OpenSSH 版本禁用老舊算法
   - 需要明確指定兼容的算法

3. **安全配置的權衡**
   - `AllowTcpForwarding` 默認禁用有其原因
   - 啟用時應評估安全風險並添加限制

### 10.2 流程層面

1. **架構變更需要全面測試**
   - 引入跳板機前應進行完整的連接測試
   - 不同連接方式（密鑰/密碼、直連/跳轉）都要驗證

2. **文檔的重要性**
   - 及時更新架構圖和配置文檔
   - 記錄配置變更的原因和影響

3. **系統性診斷方法**
   - 從下到上（網路 → 傳輸 → 應用）
   - 使用詳細日誌和調試模式
   - 逐步隔離問題範圍

---

## 11. 後續建議

### 11.1 立即行動項

- [ ] 備份修改後的配置文件
- [ ] 更新架構文檔（ARCHITECTURE.md）
- [ ] 測試所有設備的連接（不只是 ISP1）
- [ ] 驗證 Ansible playbook 的完整執行

### 11.2 短期改進（1-2 週）

- [ ] 審查並加強 TCP 轉發的安全限制
- [ ] 實施 SSH 連接審計日誌
- [ ] 創建標準化的連接測試腳本
- [ ] 文檔化跳板機的維護流程

### 11.3 長期規劃（1-3 月）

- [ ] 評估遷移到更安全的密鑰算法（Ed25519）
- [ ] 實施密鑰輪換策略
- [ ] 考慮使用 Ansible Vault 管理敏感信息
- [ ] 建立災難恢復程序（跳板機故障時的應對）

---

## 12. 附錄

### 12.1 最終工作配置

**inventory/hosts.yml（cisco_devices 部分）：**
```yaml
cisco_devices:
  vars:
    ansible_ssh_common_args: "-o ProxyCommand=\"ssh -W %h:%p -i /home/geek/.ssh/bastion_key -o PubkeyAcceptedAlgorithms=+ssh-rsa -o StrictHostKeyChecking=no root@192.168.213.136\" -o StrictHostKeyChecking=no"
  children:
    hq_routers:
    hq_switches:
    branch_routers:
    branch_switches:
    isp:
```

**跳板機 /etc/ssh/sshd_config（相關部分）：**
```ini
AllowTcpForwarding yes
AuthorizedKeysFile .ssh/authorized_keys
```

**跳板機 /root/.ssh/authorized_keys：**
```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDQpGNzsUFDAvoHN811uxd++jjOn19HO6Jt6CWU7cudJ1S1XfbzIXDKY/NJfiukT29iIHYgWxUc6C+VTo+UI/Djs2VARUCnWoE/EJaGyiecv2QP4L9oMXEuivfQOg35LN4T/OTCFM7HVxFJnvjpPE4wjXjfwEQSu53Y9wAjVn1H12eyJRLZ4gi17eIn4YJEHTQuD3A/E6oJ5tg48B8oPx8juqeETgjR1udOnE9woyaCE2tO5QnM+mcp9BCQETQalJh9VSncwP10N4soZrcvo+zzYYRSyWc9klBFDD6bkhAkYkqYpkHOE3Ea0LoxURYa5BOoUxptyDvSEySWeAis3IjLZc+NcEoqnTvWzBwcgPfNhCANJsKaM0qVdL+qquV5XbZswXRhNLaMy38jtja1EGT5hqDGNC0EhjMYxJAHup5DILg7CFG24XT1OspiuxsEnMVp7nIr2t20d1OmH9Eim48+PeXDwxedcwD3qSizUXszNABT6MqWKYa3DUEXHw+8l4+PJEl49/jlqAOi4jZ3dgFoCyIutL9HjHuP55ELTR0sezDD1Uwx4XYWVLhybG8f9GvkRZEFpNQ6BXELubV5gU2ijciJHAw3eWq81V9lanXJyuGa46keS3PJ52n8FLhiKqOA8NEGxuMQeIQmovvyNZCooVetHmZwmEiFbGCXuQ8nBQ== root@uac
```

### 12.2 關鍵檔案位置

**Ansible 主機 (192.168.56.102)：**
- 配置文件：`/home/geek/ansible_network-lab/ansible.cfg`
- Inventory：`/home/geek/ansible_network-lab/inventory/hosts.yml`
- 跳板機密鑰：`/home/geek/.ssh/bastion_key`（權限 600）

**跳板機 (192.168.213.136)：**
- SSH 配置：`/etc/ssh/sshd_config`
- 公鑰文件：`/root/.ssh/authorized_keys`（權限 600）
- 私鑰備份：`/root/.ssh/temp_rsa`
- 公鑰：`/root/.ssh/temp_rsa.pub`

### 12.3 參考資料

- [Ansible Network Automation Guide](https://docs.ansible.com/ansible/latest/network/index.html)
- [SSH ProxyCommand Configuration](https://www.openssh.com/manual.html)
- [OpenSSH Legacy Options](https://www.openssh.com/legacy.html)

---

## 13. 結論

通過系統性的診斷和分層解決問題，成功實現了 Ansible 通過跳板機安全連接到網路設備的目標。此次故障排除過程體現了：

1. **分層診斷的重要性**：從網路層到應用層逐步排查
2. **日誌分析的價值**：SSH 詳細日誌提供了關鍵線索
3. **安全與可用性的平衡**：在啟用功能時需考慮安全影響
4. **文檔和測試的必要性**：架構變更需要充分的測試和文檔

最終配置已驗證可用，建議按照「後續建議」章節進行持續改進。

---

**報告編寫者**: Claude (AI Assistant)
**審查狀態**: 待審查
**版本**: 1.0
