# SSH 跳板機設置指南

本指南說明如何設置和整合 Docker Bastion SSH Server 與 Ansible Network Lab。

## 前提條件

- Docker 和 Docker Compose 已安裝
- SSH 密鑰已生成（或將生成）
- Git 已安裝

## 步驟 1：獲取跳板機專案

### 方法 1：獨立安裝（推薦）

```bash
# 在合適的位置克隆跳板機專案
cd /path/to/your/projects
git clone https://github.com/Riven-dev1030/docker-bastion-ssh.git
cd docker-bastion-ssh
```

### 方法 2：使用 Git Submodule（進階）

```bash
# 在 Ansible 專案根目錄
git submodule add https://github.com/Riven-dev1030/docker-bastion-ssh.git bastion
git submodule update --init
```

## 步驟 2：配置 SSH 密鑰

### 生成密鑰對（如果還沒有）

```bash
# 生成專用的跳板機密鑰
ssh-keygen -t rsa -b 4096 -f ~/.ssh/bastion_key -N ""

# 或使用現有密鑰
# 例如：~/.ssh/id_rsa
```

### 配置跳板機的 authorized_keys

```bash
# 進入跳板機專案目錄
cd /path/to/docker-bastion-ssh

# 複製公鑰到配置檔案
cat ~/.ssh/bastion_key.pub > config/authorized_keys

# 或如果使用現有密鑰
cat ~/.ssh/id_rsa.pub > config/authorized_keys
```

## 步驟 3：啟動跳板機

```bash
# 在跳板機專案目錄
cd /path/to/docker-bastion-ssh

# 使用 docker-compose 構建和啟動
docker-compose up -d

# 或使用 Makefile
make build
make up

# 檢查容器狀態
docker ps | grep bastion

# 查看日誌
docker logs ansible-bastion
```

## 步驟 4：測試跳板機連接

```bash
# 測試 SSH 連接
ssh -i ~/.ssh/bastion_key -p 2222 root@localhost

# 或使用 Makefile
make test-connect

# 如果成功，應該可以登入跳板機的 shell
```

## 步驟 5：配置 Ansible 整合

### 在 inventory/hosts.yml 中配置

編輯 `inventory/hosts.yml`：

```yaml
all:
  vars:
    # 跳板機 ProxyCommand 配置
    ansible_ssh_common_args: >
      -o ProxyCommand="ssh -W %h:%p -i ~/.ssh/bastion_key -p 2222 root@localhost"
      -o StrictHostKeyChecking=no
```

### 或使用環境變數（推薦）

```yaml
# inventory/hosts.yml
all:
  vars:
    bastion_host: "{{ lookup('env', 'BASTION_HOST') | default('localhost') }}"
    bastion_port: "{{ lookup('env', 'BASTION_PORT') | default('2222') }}"
    bastion_key: "{{ lookup('env', 'BASTION_KEY') | default('~/.ssh/bastion_key') }}"
    ansible_ssh_common_args: >
      -o ProxyCommand="ssh -W %h:%p -i {{ bastion_key }} -p {{ bastion_port }} root@{{ bastion_host }}"
      -o StrictHostKeyChecking=no
```

然後在執行時設置環境變數：

```bash
export BASTION_HOST=localhost
export BASTION_PORT=2222
export BASTION_KEY=~/.ssh/bastion_key
```

## 步驟 6：配置 PermitOpen（可選但建議）

如果需要限制跳板機可以轉發的目標，編輯跳板機的 `config/sshd_config`：

```ini
# 只允許轉發到管理網段的 SSH 和 Telnet
PermitOpen 192.168.1.*:22
PermitOpen 192.168.1.*:23
```

重新構建並啟動：

```bash
cd /path/to/docker-bastion-ssh
docker-compose up -d --build
```

詳細說明請參考：[Docker Bastion SSH - PermitOpen Guide](https://github.com/Riven-dev1030/docker-bastion-ssh/blob/main/docs/PERMITOPEN_GUIDE.md)

## 步驟 7：測試 Ansible 連接

```bash
# 回到 Ansible 專案目錄
cd /path/to/ansible-network-lab

# 測試單個設備
ansible R1 -m ping

# 測試所有設備
ansible all -m ping -vvv
```

### 預期結果

如果配置正確，你應該看到：

```
R1 | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

## 故障排除

### 問題 1：無法連接到跳板機

```bash
# 檢查容器狀態
docker ps | grep bastion

# 檢查日誌
docker logs ansible-bastion

# 檢查通訊埠映射
docker port ansible-bastion

# 測試連接（詳細模式）
ssh -vvv -i ~/.ssh/bastion_key -p 2222 root@localhost
```

**常見原因：**
- 容器未啟動：`docker-compose up -d`
- 通訊埠衝突：檢查 2222 是否被佔用
- authorized_keys 未配置：檢查 `config/authorized_keys`
- 私鑰權限錯誤：`chmod 600 ~/.ssh/bastion_key`

### 問題 2：可以連接跳板機，但無法透過跳板機連接設備

```bash
# 測試 TCP 轉發
ssh -v -o ProxyCommand='ssh -W %h:%p -i ~/.ssh/bastion_key -p 2222 root@localhost' admin@192.168.1.11

# 檢查 PermitOpen 配置
docker exec ansible-bastion grep PermitOpen /etc/ssh/sshd_config
```

**常見原因：**
- PermitOpen 限制：確保目標 IP 和端口在允許範圍內
- 網路不通：確保跳板機容器可以訪問目標網段
- 目標設備不可達：ping 192.168.1.11

### 問題 3：Ansible 連接失敗

```bash
# 使用詳細模式查看錯誤
ansible R1 -m ping -vvvv

# 檢查 inventory 配置
ansible-inventory --list

# 測試 ProxyCommand
ssh -F /dev/null -o ProxyCommand='ssh -W %h:%p -i ~/.ssh/bastion_key -p 2222 root@localhost' admin@192.168.1.11
```

**常見原因：**
- ansible_ssh_common_args 配置錯誤：檢查引號和轉義
- 設備憑證錯誤：檢查 ansible_user 和 ansible_password
- 設備 IP 錯誤：檢查 ansible_host

### 問題 4：Permission denied (publickey)

```bash
# 檢查跳板機的 authorized_keys
docker exec ansible-bastion cat /root/.ssh/authorized_keys

# 檢查本地私鑰權限
ls -la ~/.ssh/bastion_key

# 修正權限
chmod 700 ~/.ssh
chmod 600 ~/.ssh/bastion_key
```

## 進階配置

### 1. 跳板機在遠端主機

如果跳板機運行在遠端主機（例如：192.168.1.100）：

```yaml
# inventory/hosts.yml
all:
  vars:
    ansible_ssh_common_args: >
      -o ProxyCommand="ssh -W %h:%p -i ~/.ssh/bastion_key -p 2222 root@192.168.1.100"
```

### 2. 多跳板機配置

如果不同環境使用不同跳板機：

```yaml
# inventory/hosts.yml
all:
  children:
    hq_devices:
      vars:
        ansible_ssh_common_args: >
          -o ProxyCommand="ssh -W %h:%p -i ~/.ssh/hq_bastion -p 2222 root@hq-bastion.local"
      hosts:
        R1:
          ansible_host: 192.168.1.11

    branch_devices:
      vars:
        ansible_ssh_common_args: >
          -o ProxyCommand="ssh -W %h:%p -i ~/.ssh/branch_bastion -p 2222 root@branch-bastion.local"
      hosts:
        BR1:
          ansible_host: 192.168.2.11
```

### 3. 使用 SSH Config 檔案

在 `~/.ssh/config` 中配置：

```
Host bastion
    HostName localhost
    Port 2222
    User root
    IdentityFile ~/.ssh/bastion_key
    StrictHostKeyChecking no

Host 192.168.1.*
    ProxyCommand ssh -W %h:%p bastion
    User admin
    StrictHostKeyChecking no
```

然後 Ansible 配置可以簡化：

```yaml
# inventory/hosts.yml
all:
  vars:
    # SSH Config 會自動處理 ProxyCommand
    ansible_ssh_common_args: "-F ~/.ssh/config"
```

## 生產環境建議

### 1. 安全性

- ✅ 使用強密鑰（RSA 4096 或 Ed25519）
- ✅ 定期輪換 SSH 密鑰
- ✅ 啟用 PermitOpen 限制
- ✅ 監控跳板機日誌
- ✅ 使用 Ansible Vault 保護密碼

### 2. 高可用性

- 部署多個跳板機實例
- 使用負載均衡器（HAProxy、Nginx）
- 配置健康檢查和自動故障轉移

### 3. 監控和日誌

```yaml
# docker-compose.yml
volumes:
  - bastion_logs:/var/log
  - /path/to/centralized/logs:/var/log/bastion:ro
```

### 4. 備份

定期備份關鍵配置：
- `config/authorized_keys`
- `config/sshd_config`
- `inventory/hosts.yml`

## 相關資源

- [Docker Bastion SSH 專案](https://github.com/Riven-dev1030/docker-bastion-ssh)
- [Docker Bastion - README](https://github.com/Riven-dev1030/docker-bastion-ssh/blob/main/README.md)
- [SSH Key Management](https://github.com/Riven-dev1030/docker-bastion-ssh/blob/main/docs/SSH_KEY_MANAGEMENT.md)
- [Customization Guide](https://github.com/Riven-dev1030/docker-bastion-ssh/blob/main/docs/CUSTOMIZATION_GUIDE.md)
- [PermitOpen Configuration](https://github.com/Riven-dev1030/docker-bastion-ssh/blob/main/docs/PERMITOPEN_GUIDE.md)
- [Ansible Integration Examples](https://github.com/Riven-dev1030/docker-bastion-ssh/tree/main/examples/ansible-integration)

## 快速參考

### 常用命令

```bash
# 跳板機管理
cd /path/to/docker-bastion-ssh
make help              # 查看所有命令
make build             # 構建鏡像
make up                # 啟動容器
make down              # 停止容器
make logs              # 查看日誌
make test-connect      # 測試連接

# Ansible 測試
cd /path/to/ansible-network-lab
ansible all -m ping                    # 測試所有設備
ansible R1 -m ping -vvv               # 詳細模式
ansible-inventory --list               # 查看 inventory
ansible-playbook playbooks/s0_preparation.yml --check  # 乾執行
```

### 環境變數

```bash
# 設置跳板機參數
export BASTION_HOST=localhost
export BASTION_PORT=2222
export BASTION_KEY=~/.ssh/bastion_key

# 設置 Ansible 參數
export ANSIBLE_HOST_KEY_CHECKING=False
export ANSIBLE_TIMEOUT=30
```

---

**注意**：Docker Bastion SSH Server 現在是一個獨立專案。如果你需要更新跳板機配置或查看更多範例，請參考 [docker-bastion-ssh](https://github.com/Riven-dev1030/docker-bastion-ssh) 專案。
