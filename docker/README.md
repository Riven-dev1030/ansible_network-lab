# Bastion SSH Server - Docker 鏡像

這個 Docker 鏡像包含了完整配置的 OpenSSH 伺服器，用作 Ansible ProxyCommand 跳板機。

## 功能特性

✅ **SSH 密鑰認證** - 僅支援密鑰認證，禁用密碼認證
✅ **TCP 轉發限制** - 使用 PermitOpen 限制轉發目標
✅ **ProxyCommand 支援** - 完全支援 SSH -W 參數進行stdio轉發
✅ **輕量級** - 基於 Alpine Linux，鏡像大小僅 ~20MB
✅ **容器化** - 易於部署和擴展
✅ **安全** - 遵循 SSH 安全最佳實踐

## 快速開始

### 1. 準備 SSH 公鑰

```bash
# 複製示例檔案
cp docker/authorized_keys.example docker/authorized_keys

# 編輯檔案，新增你的 SSH 公鑰
# 你可以從以下位置取得：
cat ~/.ssh/id_rsa.pub
# 或
cat ~/.ssh/bastion_key.pub
```

編輯 `docker/authorized_keys`，將公鑰貼上進去：

```
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQD... your-public-key... user@host
```

### 2. 構建鏡像

```bash
cd docker

# 方式 1：使用 docker-compose 自動構建
docker-compose build

# 方式 2：手動構建
docker build -t ansible-bastion:latest -f Dockerfile.bastion .
```

### 3. 啟動容器

```bash
# 使用 docker-compose 啟動
docker-compose up -d

# 或手動啟動
docker run -d \
  --name ansible-bastion \
  -p 2222:22 \
  -v $(pwd)/authorized_keys:/root/.ssh/authorized_keys:ro \
  ansible-bastion:latest
```

### 4. 驗證連接

```bash
# 測試 SSH 連接
ssh -i ~/.ssh/id_rsa -p 2222 root@localhost

# 或
ssh -i ~/.ssh/bastion_key.txt -p 2222 root@localhost

# 查看容器日誌
docker logs -f ansible-bastion
```

## 配置檔案說明

### sshd_config

主要配置項：

| 配置項 | 值 | 說明 |
|--------|-----|------|
| `PubkeyAuthentication` | yes | 啟用密鑰認證 |
| `PasswordAuthentication` | no | 禁用密碼認證 |
| `AllowTcpForwarding` | yes | 啟用 TCP 轉發（ProxyCommand 需要） |
| `PermitOpen` | 192.168.1.*:22 | 只允許轉發到 192.168.1.0/24 網段的 SSH |
| `PermitRootLogin` | prohibit-password | 允許 root 登入但需要密鑰 |
| `MaxAuthTries` | 3 | 最多嘗試 3 次認證 |
| `ClientAliveInterval` | 300 | 每 300 秒傳送一個保活訊號 |

### authorized_keys

儲存允許連接的 SSH 公鑰。一行一個公鑰。

## 與 Ansible 整合

### 方法 1：使用 ProxyCommand

在 `inventory/hosts.yml` 中配置：

```yaml
cisco_devices:
  vars:
    # 透過 localhost:2222 的跳板機連接
    ansible_ssh_common_args: "-o ProxyCommand=\"ssh -W %h:%p -i ~/.ssh/id_rsa -p 2222 root@localhost\" -o StrictHostKeyChecking=no"
```

### 方法 2：修改 sshd_config

如果需要支援其他轉發目標，編輯 `sshd_config` 並修改 `PermitOpen`：

```ini
# 支援多個目標
PermitOpen 192.168.1.*:22      # SSH
PermitOpen 192.168.1.*:23      # Telnet
PermitOpen 192.168.1.*:443     # HTTPS
```

然後重新構建鏡像：

```bash
docker-compose up -d --build
```

## 進階用法

### 使用 Volume 掛載更新配置

```bash
docker run -d \
  --name ansible-bastion \
  -p 2222:22 \
  -v $(pwd)/sshd_config:/etc/ssh/sshd_config:ro \
  -v $(pwd)/authorized_keys:/root/.ssh/authorized_keys:ro \
  ansible-bastion:latest
```

### 除錯模式

查看 SSH 詳細日誌：

```bash
# 查看容器日誌
docker logs -f ansible-bastion

# 進入容器
docker exec -it ansible-bastion sh

# 檢查 SSH 配置
sshd -T

# 檢查公鑰
cat /root/.ssh/authorized_keys
```

### 網路配置

如果需要容器訪問其他網路：

```bash
# 建立自訂網路
docker network create ansible_network

# 使用網路啟動
docker-compose -f docker-compose.yml up -d
```

## 故障排除

### 無法連接到容器

```bash
# 1. 檢查容器是否執行
docker ps | grep bastion

# 2. 檢查日誌
docker logs ansible-bastion

# 3. 驗證通訊埠映射
docker port ansible-bastion

# 4. 測試連接
ssh -vv -i ~/.ssh/id_rsa -p 2222 root@localhost
```

### 權限被拒絕 (Permission denied)

```bash
# 1. 檢查 authorized_keys 權限
docker exec ansible-bastion ls -la /root/.ssh/

# 2. 檢查公鑰是否正確
docker exec ansible-bastion cat /root/.ssh/authorized_keys

# 3. 驗證本地私鑰權限
ls -la ~/.ssh/id_rsa
# 應該是 600
```

### SSH 演算法不匹配

如果遇到演算法錯誤，檢查 sshd_config 中的加密套件：

```ini
Ciphers aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
```

## 生產環境部署

對於生產環境，建議：

1. **使用 Secret 管理密鑰**
   - 不要在 Dockerfile 中包含 authorized_keys
   - 使用 Docker Secrets 或環境變數

2. **啟用日誌持久化**
   ```yaml
   volumes:
     - bastion_logs:/var/log
   ```

3. **配置資源限制**
   ```yaml
   resources:
     limits:
       cpus: '0.5'
       memory: 256M
     reservations:
       cpus: '0.25'
       memory: 128M
   ```

4. **配置重啟策略**
   ```yaml
   restart_policy:
     condition: on-failure
     delay: 5s
     max_attempts: 3
   ```

5. **監控和告警**
   - 使用 Prometheus 導出器
   - 配置健康檢查
   - 設定日誌聚合

## 安全建議

✅ **僅使用密鑰認證** - 禁用密碼認證
✅ **限制轉發目標** - 使用 PermitOpen
✅ **定期更新** - 及時更新 Alpine 基礎鏡像
✅ **監控日誌** - 審計 SSH 連接日誌
✅ **限制權限** - 使用最少權限原則
✅ **備份配置** - 定期備份 authorized_keys

## 清理資源

```bash
# 停止並刪除容器
docker-compose down

# 或手動刪除
docker stop ansible-bastion
docker rm ansible-bastion

# 刪除鏡像
docker rmi ansible-bastion:latest

# 刪除網路
docker network rm ansible_network

# 刪除 volume
docker volume rm bastion_logs
```

## 參考資源

- [OpenSSH 官方文檔](https://man.openbsd.org/sshd_config)
- [Docker 官方文檔](https://docs.docker.com/)
- [Ansible ProxyCommand](https://docs.ansible.com/ansible/latest/network/user_guide/network_best_practices_2.5.html#proxy-command)

## 授權

MIT
