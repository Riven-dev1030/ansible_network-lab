# Docker 跳板機自訂配置指南

本指南說明如何調整 Docker 跳板機的各項配置。

## 目錄

1. [修改 SSH 轉發限制](#修改-ssh-轉發限制)
2. [修改 SSH 伺服器配置](#修改-ssh-伺服器配置)
3. [修改 Docker Compose 設定](#修改-docker-compose-設定)
4. [修改 Dockerfile](#修改-dockerfile)
5. [快速配置範例](#快速配置範例)

---

## 修改 SSH 轉發限制

### 場景 1：允許轉發到多個網段

編輯 `docker/sshd_config`，找到 `PermitOpen` 部分：

```ini
# 原始配置（只允許 192.168.1.x:22）
PermitOpen 192.168.1.*:22
```

改為：

```ini
# 允許多個網段和端口
PermitOpen 192.168.1.*:22        # SSH
PermitOpen 192.168.1.*:23        # Telnet
PermitOpen 10.10.10.*:22         # 另一個子網 SSH
PermitOpen 10.10.20.*:22         # 又一個子網 SSH
```

### 場景 2：允許轉發到特定 IP

```ini
# 只允許特定 IP
PermitOpen 192.168.1.11:22       # R1 SSH
PermitOpen 192.168.1.12:22       # R2 SSH
PermitOpen 192.168.1.13:22       # R3 SSH
```

### 場景 3：允許特定 IP 的多個端口

```ini
# 允許多個端口
PermitOpen 192.168.1.11:22
PermitOpen 192.168.1.11:23
PermitOpen 192.168.1.11:443
PermitOpen 192.168.1.12:22
PermitOpen 192.168.1.12:3306     # MySQL
```

### 場景 4：禁用轉發限制（不推薦）

```ini
# 允許所有轉發（安全風險！）
# PermitOpen any
```

### 場景 5：完全禁用轉發

```ini
# 完全禁用 TCP 轉發
AllowTcpForwarding no
```

---

## 修改 SSH 伺服器配置

### 場景 1：允許密碼認證

編輯 `docker/sshd_config`：

```ini
# 原始配置（禁用密碼認證）
PasswordAuthentication no

# 改為允許密碼認證
PasswordAuthentication yes
```

### 場景 2：允許 Root 直接登入

```ini
# 原始配置
PermitRootLogin prohibit-password

# 改為完全允許（不推薦）
PermitRootLogin yes

# 或要求密鑰認證
PermitRootLogin without-password
```

### 場景 3：修改 SSH 監聽埠

```ini
# 原始配置
Port 22

# 改為其他埠
Port 2222
```

### 場景 4：增加認證嘗試次數

```ini
# 原始配置
MaxAuthTries 3

# 增加到 6 次
MaxAuthTries 6
```

### 場景 5：調整連接保活時間

```ini
# 原始配置（300 秒 = 5 分鐘）
ClientAliveInterval 300

# 改為 10 分鐘
ClientAliveInterval 600

# 或禁用保活（完全依賴 TCP keepalive）
ClientAliveInterval 0
```

### 場景 6：啟用 Agent 轉發

```ini
# 原始配置（禁用）
AllowAgentForwarding no

# 改為允許
AllowAgentForwarding yes
```

### 場景 7：啟用 X11 轉發

```ini
# 原始配置
X11Forwarding no

# 改為允許
X11Forwarding yes
```

### 場景 8：調整加密演算法

```ini
# 原始配置（安全演算法）
Ciphers aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com

# 增加對舊演算法的支援
Ciphers aes128-ctr,aes192-ctr,aes256-ctr,aes128-cbc,aes192-cbc,aes256-cbc

# 或只支援最安全的
Ciphers aes256-gcm@openssh.com
```

---

## 修改 Docker Compose 設定

編輯 `docker/docker-compose.yml`：

### 場景 1：改變映射的埠

```yaml
# 原始配置（容器 22 埠 → 主機 2222 埠）
ports:
  - "2222:22"

# 改為其他埠（容器 22 埠 → 主機 22 埠）
ports:
  - "22:22"

# 或多個埠
ports:
  - "2222:22"
  - "2223:22"  # 第二個容器的映射
```

### 場景 2：掛載本地配置檔案

```yaml
volumes:
  # 掛載自訂 sshd_config（覆蓋容器內的）
  - ./sshd_config:/etc/ssh/sshd_config:ro

  # 掛載 authorized_keys
  - ./authorized_keys:/root/.ssh/authorized_keys:ro

  # 掛載日誌目錄用於檢查
  - bastion_logs:/var/log
```

### 場景 3：調整資源限制

```yaml
services:
  bastion:
    # 新增資源限制
    deploy:
      resources:
        limits:
          cpus: '0.5'          # 最多 50% CPU
          memory: 256M         # 最多 256MB 記憶體
        reservations:
          cpus: '0.25'
          memory: 128M
```

### 場景 4：修改環境變數

```yaml
environment:
  TZ: UTC
  # 新增自訂變數
  SSH_BANNER: "Welcome to Bastion"
  LOG_LEVEL: "VERBOSE"
```

### 場景 5：改變重啟策略

```yaml
# 原始配置
restart: unless-stopped

# 改為其他策略
restart: always          # 總是重啟
restart: no             # 不自動重啟
restart: on-failure     # 失敗時重啟
```

### 場景 6：新增環境特定的覆蓋

```yaml
services:
  bastion:
    # 用於開發環境
    environment:
      DEBUG: "true"
    volumes:
      # 掛載本地配置用於快速迭代
      - ./sshd_config:/etc/ssh/sshd_config:ro
      - ./authorized_keys:/root/.ssh/authorized_keys:ro
```

---

## 修改 Dockerfile

編輯 `docker/Dockerfile.bastion`：

### 場景 1：新增額外的套件

```dockerfile
# 在 RUN apk add 那行增加
RUN apk update && \
    apk add --no-cache \
        openssh=9.3_p2-r1 \
        openssh-client=9.3_p2-r1 \
        bash \
        doas \
        curl \              # 新增
        vim \               # 新增
        net-tools \         # 新增
    && rm -rf /var/cache/apk/*
```

### 場景 2：改變基礎鏡像

```dockerfile
# 原始配置（Alpine Linux - 輕量級）
FROM alpine:3.18

# 改為 Ubuntu（功能更完整但更大）
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y \
    openssh-server \
    openssh-client \
    bash \
    && rm -rf /var/lib/apt/lists/*

# 或使用 Debian（中等大小）
FROM debian:12-slim
```

### 場景 3：新增健康檢查

```dockerfile
# 修改或新增健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sshd -t && echo "SSH service is healthy" || exit 1
```

### 場景 4：新增使用者

```dockerfile
# 在 ENTRYPOINT 之前新增
RUN addgroup -g 1000 sshuser && \
    adduser -D -u 1000 -G sshuser sshuser && \
    mkdir -p /home/sshuser/.ssh && \
    chown -R sshuser:sshuser /home/sshuser/.ssh
```

### 場景 5：複製額外的配置檔案

```dockerfile
# 在 COPY sshd_config 之後新增
COPY ssh_banner.txt /etc/ssh/banner.txt
COPY motd.txt /etc/motd
```

---

## 快速配置範例

### 範例 1：開發環境配置

**修改 `docker/sshd_config`：**

```ini
# 允許密碼認證（開發用）
PasswordAuthentication yes
PermitEmptyPasswords no

# 允許 root 直接登入
PermitRootLogin yes

# 允許 TCP 轉發到所有目標（開發用）
AllowTcpForwarding yes
# PermitOpen any

# 啟用 X11 和 Agent 轉發（開發用）
AllowAgentForwarding yes
X11Forwarding yes

# 增加日誌詳細程度
LogLevel DEBUG
```

### 範例 2：生產環境配置

**修改 `docker/sshd_config`：**

```ini
# 嚴格禁用密碼認證
PasswordAuthentication no
PubkeyAuthentication yes

# 禁止 root 直接登入
PermitRootLogin no

# 嚴格限制轉發
AllowTcpForwarding yes
PermitOpen 192.168.1.*:22
PermitOpen 10.10.10.*:22

# 禁用危險功能
AllowAgentForwarding no
X11Forwarding no
PermitTunnel no

# 加強安全設定
MaxAuthTries 2
MaxSessions 3
ClientAliveInterval 600

# 日誌記錄
LogLevel VERBOSE
```

### 範例 3：多網段環境配置

**修改 `docker/sshd_config`：**

```ini
# 允許多個網段的 SSH
PermitOpen 192.168.1.*:22      # HQ 管理網段
PermitOpen 10.10.10.*:22       # HQ VLAN 10
PermitOpen 10.10.20.*:22       # HQ VLAN 20
PermitOpen 10.110.10.*:22      # 分公司 VLAN
PermitOpen 192.168.100.*:22    # 臨時網段

# 允許多個管理端口
PermitOpen 192.168.1.*:23      # Telnet
PermitOpen 192.168.1.*:443     # HTTPS
```

### 範例 4：修改後重新部署

```bash
# 1. 編輯配置檔案
vim docker/sshd_config
vim docker/docker-compose.yml

# 2. 驗證 SSH 配置語法
docker-compose exec bastion sshd -t

# 3. 如果修改了 Dockerfile，重新構建
docker-compose down
docker-compose build
docker-compose up -d

# 4. 如果只修改了 sshd_config，只需重啟
docker-compose restart bastion

# 5. 檢查日誌確認變更生效
docker-compose logs -f bastion
```

---

## 常見問題

### Q: 修改後需要重新構建鏡像嗎？

**A:** 取決於修改的內容：
- **sshd_config**：只需重啟容器（`docker-compose restart bastion`）
- **docker-compose.yml**：只需重啟容器
- **Dockerfile**：需要重新構建（`docker-compose build`）
- **authorized_keys**：只需重啟容器

### Q: 如何測試新配置是否正確？

```bash
# 1. 檢查 SSH 配置語法
docker-compose exec bastion sshd -t

# 2. 測試 SSH 連接
ssh -i ~/.ssh/id_rsa -p 2222 root@localhost

# 3. 查看詳細日誌
docker-compose logs -f bastion
```

### Q: 如何備份原始配置？

```bash
# 備份當前配置
cp docker/sshd_config docker/sshd_config.backup
cp docker/docker-compose.yml docker/docker-compose.yml.backup

# 或使用 git
git diff docker/sshd_config
```

### Q: 修改後容器無法啟動怎麼辦？

```bash
# 1. 檢查日誌
docker-compose logs bastion

# 2. 驗證配置語法
docker run --rm -v $(pwd)/docker/sshd_config:/etc/ssh/sshd_config \
  alpine:3.18 sh -c "apk add openssh && sshd -t"

# 3. 恢復備份
cp docker/sshd_config.backup docker/sshd_config

# 4. 重啟容器
docker-compose restart bastion
```

---

## 修改工作流程

1. **編輯配置檔案**
   ```bash
   vim docker/sshd_config
   ```

2. **測試配置**
   ```bash
   docker-compose exec bastion sshd -t
   ```

3. **應用變更**
   ```bash
   docker-compose restart bastion
   ```

4. **驗證變更**
   ```bash
   ssh -i ~/.ssh/id_rsa -p 2222 root@localhost
   docker-compose logs bastion
   ```

5. **提交到 Git**
   ```bash
   git add docker/sshd_config docker/docker-compose.yml
   git commit -m "調整跳板機配置：允許更多轉發目標"
   git push
   ```

---

## 安全建議

✅ **備份**：修改前始終備份原始配置
✅ **測試**：修改後立即測試連接
✅ **監控**：檢查日誌確認沒有錯誤
✅ **版本控制**：使用 git 追蹤所有變更
✅ **文檔**：記錄為什麼進行修改
✅ **驗證**：使用 `sshd -T` 檢視實際生效的配置

---

需要幫助嗎？ 可以提供具體的配置需求，我會幫你調整！
