# SSH PermitOpen 配置指南

## 文檔資訊

**版本**: 1.0
**日期**: 2026-01-05
**目的**: 在跳板機上配置 TCP 轉發限制，提升安全性
**適用環境**: OpenSSH Server (跳板機)

---

## 目錄

1. [概述](#概述)
2. [為什麼需要 PermitOpen](#為什麼需要-permitopen)
3. [前置需求](#前置需求)
4. [配置流程](#配置流程)
5. [驗證測試](#驗證測試)
6. [故障排除](#故障排除)
7. [維護管理](#維護管理)
8. [參考資料](#參考資料)

---

## 概述

### 什麼是 PermitOpen

`PermitOpen` 是 OpenSSH 服務器的配置選項，用於**限制 TCP 轉發的目標地址和端口**。

### 使用場景

```
情境：Ansible 透過跳板機連接網路設備

┌─────────────┐     ProxyCommand      ┌──────────┐     SSH/Telnet      ┌────────────┐
│   Ansible   │ ──────────────────────> │  跳板機  │ ──────────────────> │ 網路設備   │
│ 192.168.56  │                         │  .213    │                     │ 192.168.100│
└─────────────┘                         └──────────┘                     └────────────┘
                                            ↑
                                      PermitOpen 控制
                                     只允許轉發到特定目標
```

### 配置目標

- ✅ 啟用 TCP 轉發功能（支持 ProxyCommand）
- ✅ 限制轉發目標到特定網段和端口
- ✅ 防止跳板機被濫用訪問其他系統
- ✅ 符合安全最佳實踐

---

## 為什麼需要 PermitOpen

### 安全風險

**沒有 PermitOpen 限制時：**

```bash
# 攻擊者可以通過跳板機訪問任意內網系統
ssh -L 3306:internal-db:3306 user@bastion
# → 可以訪問內部數據庫

ssh -L 8080:internal-web:80 user@bastion
# → 可以訪問內部網站

ssh -L 445:file-server:445 user@bastion
# → 可以訪問文件服務器
```

**有 PermitOpen 限制後：**

```bash
# 只能訪問授權的目標
ssh -L 2222:192.168.100.50:22 user@bastion
# → ✅ 允許（在 PermitOpen 列表中）

ssh -L 3306:internal-db:3306 user@bastion
# → ❌ 拒絕（不在 PermitOpen 列表中）
```

### 合規要求

許多安全標準要求限制跳板機的轉發功能：
- CIS Benchmarks
- NIST 800-53
- PCI DSS
- ISO 27001

---

## 前置需求

### 系統需求

- OpenSSH Server 6.0 或更高版本
- Root 或 sudo 權限
- 基本的 SSH 和 Linux 知識

### 網路環境

```
Ansible 主機:     192.168.56.102
跳板機:           192.168.213.136
目標設備網段:     192.168.100.0/24
```

### 已知配置

確保以下配置已完成：
- [ ] 跳板機已啟用 `AllowTcpForwarding yes`
- [ ] 跳板機已配置 SSH 密鑰認證
- [ ] Ansible 已配置 ProxyCommand

---

## 配置流程

### 第 1 步：連接到跳板機

#### 1.1 使用 SSH 密鑰連接

```bash
# 語法
ssh -i <私鑰文件> <用戶>@<跳板機IP>

# 範例
ssh -i temp_rsa_backup(.136).txt root@192.168.213.136
```

**參數說明：**
- `-i`：指定私鑰文件
- `root`：登入用戶名
- `192.168.213.136`：跳板機 IP

#### 1.2 驗證連接

```bash
# 測試連接
ssh -i temp_rsa_backup(.136).txt root@192.168.213.136 "hostname"

# 預期輸出
uac
```

---

### 第 2 步：備份配置文件

⚠️ **重要：修改前必須備份！**

#### 2.1 創建備份

```bash
# 在跳板機上執行
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)
```

**命令解析：**
- `cp`：複製文件
- `/etc/ssh/sshd_config`：SSH 服務器配置文件
- `$(date +%Y%m%d_%H%M%S)`：添加時間戳到備份文件名

#### 2.2 從遠端執行備份

```bash
# 從本地 Windows 執行
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)"
```

#### 2.3 驗證備份

```bash
# 列出備份文件
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "ls -lh /etc/ssh/sshd_config*"

# 輸出範例
-rw-r--r--    1 root     root        3.1K Jan  5 04:39 /etc/ssh/sshd_config
-rw-r--r--    1 root     root        3.1K Jan  5 13:06 /etc/ssh/sshd_config.backup.20260105_130633
```

---

### 第 3 步：添加 PermitOpen 配置

#### 3.1 配置語法

**基本語法：**
```ini
PermitOpen host:port
```

**支持的格式：**
```ini
# 1. 精確指定
PermitOpen 192.168.100.50:22

# 2. 使用通配符
PermitOpen 192.168.100.*:22

# 3. 多個端口
PermitOpen 192.168.100.*:22
PermitOpen 192.168.100.*:23

# 4. 使用主機名
PermitOpen server.example.com:22

# 5. 禁用所有轉發（配合 AllowTcpForwarding）
PermitOpen none
```

#### 3.2 添加配置（方法 1 - Heredoc）

```bash
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 "cat >> /etc/ssh/sshd_config << 'EOF'

# ============================================
# Ansible ProxyCommand 安全配置
# 日期: $(date +%Y-%m-%d)
# 目的: 限制 TCP 轉發只能到網路設備管理網段
# ============================================

# 限制轉發目標 - 僅允許到 192.168.100.x 的 SSH
PermitOpen 192.168.100.*:22

# 如果未來需要支援 Telnet，取消註解以下行：
# PermitOpen 192.168.100.*:23

# 安全建議：
# 1. 定期審查 /var/log/messages 中的轉發日誌
# 2. 監控異常連接嘗試
# 3. 定期更新授權的目標列表
EOF
"
```

**Heredoc 語法說明：**
- `cat >> file << 'EOF'`：追加內容到文件
- `'EOF'`：單引號防止變數展開
- 內容會被添加到配置文件末尾

#### 3.3 添加配置（方法 2 - Echo）

```bash
# 單行添加
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "echo 'PermitOpen 192.168.100.*:22' >> /etc/ssh/sshd_config"
```

#### 3.4 添加配置（方法 3 - 使用 sed）

```bash
# 在特定位置插入
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "sed -i '/^AllowTcpForwarding/a PermitOpen 192.168.100.*:22' /etc/ssh/sshd_config"
```

**sed 參數說明：**
- `-i`：直接修改文件
- `/^AllowTcpForwarding/`：找到以 AllowTcpForwarding 開頭的行
- `a`：在該行後面添加（append）
- `PermitOpen ...`：要添加的內容

---

### 第 4 步：驗證配置語法

⚠️ **關鍵步驟：確保配置正確，避免 SSH 服務無法啟動**

#### 4.1 語法檢查

```bash
# 在跳板機上執行
sshd -t

# 或從遠端執行
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 "sshd -t"
```

**輸出說明：**
- **無輸出**：✅ 配置正確
- **有錯誤訊息**：❌ 配置有誤，需要修正

#### 4.2 常見錯誤

**錯誤 1：語法錯誤**
```
/etc/ssh/sshd_config line 123: Bad configuration option: PermitOpne
```
**原因**：拼寫錯誤（PermitOpne → PermitOpen）

**錯誤 2：格式錯誤**
```
/etc/ssh/sshd_config line 124: Bad syntax in PermitOpen directive
```
**原因**：格式不正確，應為 `PermitOpen host:port`

#### 4.3 帶輸出的驗證

```bash
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "sshd -t && echo '✅ 配置語法正確' || echo '❌ 配置有錯誤'"

# 輸出
✅ 配置語法正確
```

---

### 第 5 步：查看配置（可選）

#### 5.1 查看完整配置

```bash
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "cat /etc/ssh/sshd_config"
```

#### 5.2 查看 PermitOpen 相關配置

```bash
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "grep -A 5 PermitOpen /etc/ssh/sshd_config"

# 輸出範例
PermitOpen 192.168.100.*:22
# PermitOpen 192.168.100.*:23
```

#### 5.3 查看配置文件末尾

```bash
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "tail -20 /etc/ssh/sshd_config"
```

---

### 第 6 步：重啟 SSH 服務

⚠️ **注意：確保有其他方式連接，以防 SSH 服務啟動失敗**

#### 6.1 重啟服務

```bash
# 方法 1：使用 init.d 腳本
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "/etc/init.d/sshd restart"

# 方法 2：使用 systemctl（如果支援）
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "systemctl restart sshd"

# 方法 3：使用 service 命令
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "service sshd restart"
```

#### 6.2 預期輸出

```
* Stopping sshd ... [ ok ]
* Starting sshd ... [ ok ]
```

#### 6.3 驗證服務狀態

```bash
# 檢查 SSH 服務是否運行
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "/etc/init.d/sshd status"

# 或
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "ps aux | grep sshd"
```

#### 6.4 測試連接

```bash
# 重啟後立即測試連接
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 "echo 'SSH 服務正常'"

# 輸出
SSH 服務正常
```

---

## 驗證測試

### 測試矩陣

| 測試 | 目標 | 預期結果 | 驗證內容 |
|------|------|---------|---------|
| 1 | 允許的 IP + 端口 | ✅ 成功 | 功能正常 |
| 2 | 不允許的 IP | ❌ 失敗 | IP 限制生效 |
| 3 | 允許的 IP + 不允許的端口 | ❌ 失敗 | 端口限制生效 |

---

### 測試 1：允許的目標（應該成功）

#### 使用 Ansible 測試

```bash
# 從 Ansible 主機執行
ssh -i "temp_rsa_backup(.56).txt" geek@192.168.56.102 \
  "cd /home/geek/ansible_network-lab && ansible ISP1 -m ping"
```

**預期輸出：**
```yaml
PLAY RECAP *********************************************************************
ISP1                       : ok=1    changed=0    unreachable=0    failed=0
```

**結論：** ✅ 到 192.168.100.50:22 的轉發成功

---

#### 使用 ProxyCommand 測試

```bash
ssh -i "temp_rsa_backup(.56).txt" geek@192.168.56.102 \
  "ssh -o ProxyCommand='ssh -W %h:%p -i /home/geek/.ssh/bastion_key -o PubkeyAcceptedAlgorithms=+ssh-rsa -o StrictHostKeyChecking=no root@192.168.213.136' -o StrictHostKeyChecking=no cisco123@192.168.100.50 'show version' | head -5"
```

**預期輸出：**
```
Cisco IOS Software, Linux Software (I86BI_LINUX-ADVENTERPRISEK9-M)...
```

**結論：** ✅ ProxyCommand 轉發正常工作

---

### 測試 2：不允許的 IP（應該失敗）

#### 測試外部 IP

```bash
ssh -i "temp_rsa_backup(.56).txt" geek@192.168.56.102 \
  "timeout 10 ssh -o ProxyCommand='ssh -W %h:%p -i /home/geek/.ssh/bastion_key -o PubkeyAcceptedAlgorithms=+ssh-rsa -o StrictHostKeyChecking=no root@192.168.213.136' -o StrictHostKeyChecking=no -o ConnectTimeout=5 user@8.8.8.8 2>&1"
```

**預期輸出：**
```
stdio forwarding failed
kex_exchange_identification: Connection closed by remote host
Connection closed by UNKNOWN port 65535
```

**關鍵信息：** `stdio forwarding failed` - 轉發被拒絕

**結論：** ✅ 到不允許 IP (8.8.8.8) 的轉發被正確阻止

---

### 測試 3：允許的 IP，不允許的端口（應該失敗）

#### 測試 HTTP 端口

```bash
ssh -i "temp_rsa_backup(.56).txt" geek@192.168.56.102 \
  "timeout 10 ssh -o ProxyCommand='ssh -W 192.168.100.50:80 -i /home/geek/.ssh/bastion_key -o PubkeyAcceptedAlgorithms=+ssh-rsa -o StrictHostKeyChecking=no root@192.168.213.136' -o StrictHostKeyChecking=no -o ConnectTimeout=5 user@192.168.100.50 2>&1"
```

**預期輸出：**
```
stdio forwarding failed
kex_exchange_identification: Connection closed by remote host
Connection closed by UNKNOWN port 65535
```

**結論：** ✅ 到不允許端口 (80) 的轉發被正確阻止

---

### 測試 4：查看服務器端日誌

#### 查看轉發日誌

```bash
ssh -i "temp_rsa_backup(.136).txt" root@192.168.213.136 \
  "tail -20 /var/log/messages | grep -E 'stdio fwd|Permitted open|refused'"
```

**成功的轉發日誌：**
```
Jan  5 13:10:25 uac sshd[12345]: Accepted publickey for root from 192.168.56.102
Jan  5 13:10:25 uac sshd[12345]: request stdio fwd to 192.168.100.50:22
Jan  5 13:10:25 uac sshd[12345]: Permitted open to 192.168.100.50:22
```

**被拒絕的轉發日誌：**
```
Jan  5 13:11:30 uac sshd[12346]: Accepted publickey for root from 192.168.56.102
Jan  5 13:11:30 uac sshd[12346]: request stdio fwd to 8.8.8.8:22
Jan  5 13:11:30 uac sshd[12346]: refused streamlocal port forward: originator 192.168.56.102 port 0, target 8.8.8.8 port 22
```

---

## 故障排除

### 問題 1：配置後無法連接

**症狀：**
```bash
ssh: connect to host 192.168.213.136 port 22: Connection refused
```

**可能原因：**
1. SSH 服務未啟動
2. 配置語法錯誤導致服務啟動失敗

**診斷步驟：**

```bash
# 1. 檢查服務狀態（需要其他方式連接跳板機，如控制台）
/etc/init.d/sshd status

# 2. 檢查配置語法
sshd -t

# 3. 查看詳細錯誤
sshd -T

# 4. 查看系統日誌
tail -50 /var/log/messages | grep sshd
```

**解決方法：**

```bash
# 1. 恢復備份
cp /etc/ssh/sshd_config.backup.YYYYMMDD_HHMMSS /etc/ssh/sshd_config

# 2. 重啟服務
/etc/init.d/sshd restart
```

---

### 問題 2：允許的目標也被拒絕

**症狀：**
```
stdio forwarding failed
```

**可能原因：**
1. PermitOpen 語法錯誤
2. 通配符使用不正確
3. 目標 IP 不在允許範圍

**診斷步驟：**

```bash
# 1. 檢查 PermitOpen 配置
grep PermitOpen /etc/ssh/sshd_config

# 2. 測試配置解析
sshd -T | grep permitopen

# 3. 查看日誌中的拒絕原因
tail -50 /var/log/messages | grep "refused"
```

**常見錯誤：**

```ini
# ❌ 錯誤：缺少端口
PermitOpen 192.168.100.*

# ✅ 正確
PermitOpen 192.168.100.*:22

# ❌ 錯誤：使用了錯誤的通配符
PermitOpen 192.168.100.%:22

# ✅ 正確
PermitOpen 192.168.100.*:22
```

---

### 問題 3：所有轉發都被拒絕

**症狀：**
即使是應該允許的目標也無法轉發

**可能原因：**
1. `AllowTcpForwarding` 被設置為 `no`
2. `PermitOpen` 設置為 `none`
3. 用戶特定限制（Match 配置）

**診斷步驟：**

```bash
# 1. 檢查 AllowTcpForwarding
grep AllowTcpForwarding /etc/ssh/sshd_config

# 2. 檢查完整配置
sshd -T | grep -E 'allowtcpforwarding|permitopen'

# 3. 檢查是否有 Match 限制
grep -A 10 "^Match" /etc/ssh/sshd_config
```

**解決方法：**

```bash
# 確保 AllowTcpForwarding 啟用
sed -i 's/^AllowTcpForwarding no/AllowTcpForwarding yes/' /etc/ssh/sshd_config

# 確保沒有 PermitOpen none
sed -i '/^PermitOpen none/d' /etc/ssh/sshd_config

# 重啟服務
/etc/init.d/sshd restart
```

---

### 問題 4：配置後 Ansible 無法連接

**症狀：**
```
fatal: [ISP1]: FAILED! =>
  msg: 'ssh connection failed: Socket error: Connection reset by peer'
```

**診斷步驟：**

```bash
# 1. 測試從 Ansible 主機到跳板機
ssh -i /home/geek/.ssh/bastion_key root@192.168.213.136 'hostname'

# 2. 測試 ProxyCommand 手動連接
ssh -o ProxyCommand='ssh -W %h:%p -i /home/geek/.ssh/bastion_key root@192.168.213.136' cisco123@192.168.100.50

# 3. 查看 Ansible 詳細錯誤
ansible ISP1 -m ping -vvv
```

**可能的配置問題：**

```yaml
# 檢查 inventory 配置
cat /home/geek/ansible_network-lab/inventory/hosts.yml

# 確認 ansible_ssh_common_args 配置正確
cisco_devices:
  vars:
    ansible_ssh_common_args: "-o ProxyCommand=\"ssh -W %h:%p -i /home/geek/.ssh/bastion_key -o PubkeyAcceptedAlgorithms=+ssh-rsa -o StrictHostKeyChecking=no root@192.168.213.136\" -o StrictHostKeyChecking=no"
```

---

## 維護管理

### 添加新的允許目標

#### 方法 1：編輯配置文件

```bash
# 1. 編輯配置
ssh root@192.168.213.136 "vi /etc/ssh/sshd_config"

# 2. 添加新的 PermitOpen 行
PermitOpen 192.168.200.*:22

# 3. 驗證語法
sshd -t

# 4. 重啟服務
/etc/init.d/sshd restart
```

#### 方法 2：使用腳本添加

```bash
# 創建添加腳本
cat > add_permitopen.sh << 'EOF'
#!/bin/bash
TARGET=$1
if [ -z "$TARGET" ]; then
    echo "用法: $0 <host:port>"
    echo "範例: $0 192.168.200.*:22"
    exit 1
fi

# 備份配置
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)

# 添加配置
echo "PermitOpen $TARGET" >> /etc/ssh/sshd_config

# 驗證語法
if sshd -t; then
    echo "✅ 配置添加成功"
    /etc/init.d/sshd restart
else
    echo "❌ 配置語法錯誤，恢復備份"
    cp /etc/ssh/sshd_config.backup.* /etc/ssh/sshd_config
    exit 1
fi
EOF

chmod +x add_permitopen.sh

# 使用腳本
./add_permitopen.sh "192.168.200.*:22"
```

---

### 移除允許目標

```bash
# 1. 備份
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d_%H%M%S)

# 2. 移除特定的 PermitOpen 行
sed -i '/PermitOpen 192.168.200/d' /etc/ssh/sshd_config

# 3. 驗證
sshd -t

# 4. 重啟
/etc/init.d/sshd restart
```

---

### 查看當前生效的配置

```bash
# 查看運行時配置
sshd -T | grep permitopen

# 輸出範例
permitopen 192.168.100.*:22
permitopen 192.168.100.*:23
```

---

### 審計轉發日誌

#### 實時監控

```bash
# 實時查看轉發請求
tail -f /var/log/messages | grep -E 'stdio fwd|Permitted open|refused'
```

#### 統計分析

```bash
# 統計允許的轉發
grep "Permitted open" /var/log/messages | \
    awk '{print $(NF-2), $(NF)}' | sort | uniq -c | sort -rn

# 輸出範例
   45 192.168.100.50 22
   23 192.168.100.51 22
   12 192.168.100.52 22

# 統計被拒絕的轉發
grep "refused" /var/log/messages | \
    awk '{print $(NF-2), $(NF)}' | sort | uniq -c | sort -rn

# 輸出範例
    3 8.8.8.8 22
    2 192.168.100.50 80
    1 10.0.0.1 3306
```

---

### 定期維護任務

#### 每週任務

```bash
# 1. 審查轉發日誌
grep -E 'stdio fwd|Permitted open|refused' /var/log/messages | tail -100

# 2. 檢查異常連接
grep "refused" /var/log/messages | tail -50

# 3. 備份配置
cp /etc/ssh/sshd_config /backup/sshd_config.$(date +%Y%m%d)
```

#### 每月任務

```bash
# 1. 審查 PermitOpen 列表
grep PermitOpen /etc/ssh/sshd_config

# 2. 移除不再需要的目標

# 3. 生成轉發報告
cat > forwarding_report.sh << 'EOF'
#!/bin/bash
echo "=== SSH 轉發統計報告 ==="
echo "報告時間: $(date)"
echo ""
echo "允許的轉發次數:"
grep "Permitted open" /var/log/messages | wc -l
echo ""
echo "被拒絕的轉發次數:"
grep "refused" /var/log/messages | wc -l
echo ""
echo "最常訪問的目標:"
grep "Permitted open" /var/log/messages | \
    awk '{print $(NF-2), $(NF)}' | sort | uniq -c | sort -rn | head -10
EOF
chmod +x forwarding_report.sh
./forwarding_report.sh
```

---

## 參考資料

### OpenSSH 文檔

```bash
# 查看 sshd_config 手冊
man sshd_config

# 查看 PermitOpen 說明
man sshd_config | grep -A 10 PermitOpen
```

### PermitOpen 詳細說明

```
PermitOpen
    Specifies the destinations to which TCP port forwarding is permitted.
    The forwarding specification must be one of the following forms:

        PermitOpen host:port
        PermitOpen IPv4_addr:port
        PermitOpen [IPv6_addr]:port

    Multiple forwards may be specified by separating them with whitespace.
    An argument of "any" can be used to remove all restrictions and permit
    any forwarding requests. An argument of "none" can be used to prohibit
    all forwarding requests. The wildcard "*" can be used for host or port
    to allow all hosts or ports respectively. Otherwise, no pattern matching
    or address lookups are performed on supplied names. By default all port
    forwarding requests are permitted.
```

### 相關配置選項

```ini
# TCP 轉發總開關
AllowTcpForwarding yes|no|local|remote

# 轉發目標限制
PermitOpen host:port

# 其他轉發相關
GatewayPorts no
PermitTunnel no
AllowAgentForwarding no
X11Forwarding no
```

### 安全最佳實踐文檔

- [CIS OpenSSH Benchmark](https://www.cisecurity.org/)
- [NIST SP 800-53](https://csrc.nist.gov/)
- [OpenSSH Security Best Practices](https://www.openssh.com/security.html)

---

## 快速參考

### 常用命令速查

```bash
# 備份配置
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d)

# 檢查語法
sshd -t

# 查看生效配置
sshd -T | grep permitopen

# 重啟服務
/etc/init.d/sshd restart

# 查看日誌
tail -f /var/log/messages | grep -E 'stdio fwd|Permitted'

# 測試轉發
ssh -W target:22 user@bastion
```

### 配置模板

```ini
# /etc/ssh/sshd_config

# === TCP 轉發配置 ===
AllowTcpForwarding yes

# 限制轉發目標
PermitOpen 192.168.100.*:22    # SSH
PermitOpen 192.168.100.*:23    # Telnet
PermitOpen 192.168.100.*:443   # HTTPS

# 其他安全設置
GatewayPorts no
PermitTunnel no
AllowAgentForwarding no
X11Forwarding no
```

---

## 附錄

### A. 完整配置示例

**生產環境推薦配置：**

```ini
# /etc/ssh/sshd_config

# === 基本設置 ===
Protocol 2
Port 22

# === 認證設置 ===
PermitRootLogin prohibit-password
PubkeyAuthentication yes
PasswordAuthentication no
ChallengeResponseAuthentication no
UsePAM yes

# === 轉發控制 ===
AllowTcpForwarding yes
PermitOpen 192.168.100.*:22
PermitOpen 192.168.100.*:23
X11Forwarding no
AllowAgentForwarding no
PermitTunnel no
GatewayPorts no

# === 日誌 ===
SyslogFacility AUTH
LogLevel VERBOSE

# === 連接限制 ===
MaxAuthTries 3
MaxSessions 5
ClientAliveInterval 300
ClientAliveCountMax 2
LoginGraceTime 60

# === 用戶限制 ===
AllowUsers ansible_user admin_user
```

### B. 故障排除檢查清單

- [ ] 配置文件已備份
- [ ] 使用 `sshd -t` 驗證語法
- [ ] SSH 服務成功重啟
- [ ] 可以連接到跳板機
- [ ] 允許的目標可以轉發
- [ ] 不允許的目標被阻止
- [ ] 日誌中有轉發記錄
- [ ] Ansible 可以連接設備

### C. 自動化腳本

**完整的配置腳本：**

```bash
#!/bin/bash
# configure_permitopen.sh

set -e  # 遇到錯誤立即退出

BASTION_HOST="192.168.213.136"
BASTION_USER="root"
SSH_KEY="temp_rsa_backup(.136).txt"
TARGET_NETWORK="192.168.100.*"
ALLOWED_PORTS="22 23"

echo "=== PermitOpen 配置腳本 ==="
echo "跳板機: $BASTION_HOST"
echo "目標網段: $TARGET_NETWORK"
echo "允許端口: $ALLOWED_PORTS"
echo ""

# 1. 備份配置
echo "步驟 1: 備份配置..."
ssh -i "$SSH_KEY" "$BASTION_USER@$BASTION_HOST" \
    "cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.\$(date +%Y%m%d_%H%M%S)"
echo "✅ 備份完成"

# 2. 添加配置
echo "步驟 2: 添加 PermitOpen 配置..."
for PORT in $ALLOWED_PORTS; do
    echo "  添加: PermitOpen $TARGET_NETWORK:$PORT"
    ssh -i "$SSH_KEY" "$BASTION_USER@$BASTION_HOST" \
        "echo 'PermitOpen $TARGET_NETWORK:$PORT' >> /etc/ssh/sshd_config"
done
echo "✅ 配置添加完成"

# 3. 驗證語法
echo "步驟 3: 驗證配置語法..."
if ssh -i "$SSH_KEY" "$BASTION_USER@$BASTION_HOST" "sshd -t"; then
    echo "✅ 配置語法正確"
else
    echo "❌ 配置語法錯誤"
    exit 1
fi

# 4. 重啟服務
echo "步驟 4: 重啟 SSH 服務..."
ssh -i "$SSH_KEY" "$BASTION_USER@$BASTION_HOST" \
    "/etc/init.d/sshd restart"
echo "✅ 服務重啟完成"

# 5. 測試連接
echo "步驟 5: 測試連接..."
if ssh -i "$SSH_KEY" "$BASTION_USER@$BASTION_HOST" "echo 'SSH 連接正常'"; then
    echo "✅ 連接測試成功"
else
    echo "❌ 連接測試失敗"
    exit 1
fi

echo ""
echo "=== 配置完成 ==="
echo "下一步: 使用 Ansible 測試連接到目標設備"
```

**使用方法：**
```bash
chmod +x configure_permitopen.sh
./configure_permitopen.sh
```

---

**文檔結束**

**版本歷史：**
- v1.0 (2026-01-05): 初始版本

**作者**: Claude (AI Assistant)
**審查狀態**: 待審查
