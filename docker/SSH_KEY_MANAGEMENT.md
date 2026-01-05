# Docker 跳板機 SSH 密鑰管理指南

## 快速概念圖

```
Ansible 主機（你的電腦）          Bastion 跳板機（Docker 容器）
═══════════════════════════════════════════════════════════

私鑰文件                          公鑰文件
(bastion_key)      ───SSH───>    (authorized_keys)
  ↓                              ↓
  用於連接                        用於驗証連接

  ✅ 保密                        ✅ 可以公開
  ✅ 只有你有                    ✅ 其他人可以看到
  ✅ 用於簽署和驗証               ✅ 接收來自私鑰的連接
```

---

## 部分 1：理解公鑰和私鑰

### 什麼是私鑰？

- **位置**：保存在你的電腦（Ansible 主機）
- **用途**：證明你的身份
- **安全性**：🔒 **非常機密** - 絕對不能洩露
- **位置示例**：`~/.ssh/bastion_key` 或 `~/.ssh/id_rsa`
- **權限**：必須設置為 `600`（只有你能讀取）

```bash
# 檢查私鑰權限
ls -la ~/.ssh/bastion_key
# 應該看到：-rw------- (600)
```

### 什麼是公鑰？

- **位置**：放在跳板機的 `authorized_keys` 中
- **用途**：驗証連接請求
- **安全性**：✅ 可以公開 - 沒有關係
- **位置示例**：跳板機 `/root/.ssh/authorized_keys`
- **格式**：`ssh-rsa AAAAB3...` 開頭的一長串文字

```bash
# 公鑰內容示例
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDQpGNzsUFDAvoHN811uxd++jjOn19HO6Jt6CWU7cudJ1S1XfbzIXDKY/NJfiukT29iIHYgWxUc6C+VTo+UI/Djs2VARUCnWoE/EJaGyiecv2QP4L9oMXEuivfQOg35LN4T/OTCFM7HVxFJnvjpPE4wjXjfwEQSu53Y9wAjVn1H12eyJRLZ4gi17eIn4YJEHTQuD3A/E6oJ5tg48B8oPx8juqeETgjR1udOnE9woyaCE2tO5QnM+mcp9BCQETQalJh9VSncwP10N4soZrcvo+zzYYRSyWc9klBFDD6bkhAkYkqYpkHOE3Ea0LoxURYa5BOoUxptyDvSEySWeAis3IjLZc+NcEoqnTvWzBwcgPfNhCANJsKaM0qVdL+qquV5XbZswXRhNLaMy38jtja1EGT5hqDGNC0EhjMYxJAHup5DILg7CFG24XT1OspiuxsEnMVp7nIr2t20d1OmH9Eim48+PeXDwxedcwD3qSizUXszNABT6MqWKYa3DUEXHw+8l4+PJEl49/jlqAOi4jZ3dgFoCyIutL9HjHuP55ELTR0sezDD1Uwx4XYWVLhybG8f9GvkRZEFpNQ6BXELubV5gU2ijciJHAw3eWq81V9lanXJyuGa46keS3PJ52n8FLhiKqOA8NEGxuMQeIQmovvyNZCooVetHmZwmEiFbGCXuQ8nBQ== root@ansible
```

---

## 部分 2：生成新的 SSH 密鑰對

### 步驟 1：在 Ansible 主機上生成密鑰

```bash
# 生成新的密鑰對
ssh-keygen -t rsa -b 4096 -f ~/.ssh/bastion_key -N ""

# 參數說明：
# -t rsa          使用 RSA 演算法
# -b 4096         使用 4096 位（更安全）
# -f ~/.ssh/bastion_key   儲存位置和名稱
# -N ""           不設置密碼（直接按 Enter）
```

完成後會顯示：

```
Generating public/private rsa key pair.
Your identification has been saved in /root/.ssh/bastion_key
Your public key has been saved in /root/.ssh/bastion_key.pub
The key fingerprint is:
SHA256:abc123... root@ansible
The key's randomart image is:
+---[RSA 4096]----+
|    .o.          |
|   .E o .        |
|  . . * .        |
+----[SHA256]-----+
```

### 步驟 2：驗證密鑰已生成

```bash
# 列出生成的檔案
ls -la ~/.ssh/bastion_key*

# 應該看到：
# -rw------- bastion_key      (私鑰 - 只有你能讀)
# -rw-r--r-- bastion_key.pub  (公鑰 - 任何人能讀)
```

### 步驟 3：設置正確的權限

```bash
# 設置私鑰只有你能讀
chmod 600 ~/.ssh/bastion_key
chmod 644 ~/.ssh/bastion_key.pub

# 驗證
ls -la ~/.ssh/bastion_key*
```

---

## 部分 3：配置 Docker 跳板機的公鑰

### 方式 1：在構建時包含公鑰（快速方式）

#### 步驟 1：複製示例檔案

```bash
cd docker
cp authorized_keys.example authorized_keys
```

#### 步驟 2：添加你的公鑰

```bash
# 查看你的公鑰
cat ~/.ssh/bastion_key.pub

# 複製輸出內容，然後：
# 1. 編輯 authorized_keys
vim authorized_keys

# 2. 粘貼整個公鑰（一行）到檔案中
# ssh-rsa AAAAB3NzaC1yc2E... your-public-key... user@host
```

#### 步驟 3：構建鏡像

```bash
# 構建時會自動包含 authorized_keys
docker-compose build
docker-compose up -d

# 測試連接
ssh -i ~/.ssh/bastion_key -p 2222 root@localhost
```

### 方式 2：使用 Volume 掛載（推薦用於開發）

**優勢**：修改公鑰不需要重新構建鏡像

#### 步驟 1：編輯 docker-compose.yml

```yaml
services:
  bastion:
    volumes:
      # 掛載 authorized_keys（不需要構建）
      - ./authorized_keys:/root/.ssh/authorized_keys:ro

      # 掛載 sshd_config（不需要構建）
      - ./sshd_config:/etc/ssh/sshd_config:ro
```

#### 步驟 2：準備 authorized_keys

```bash
# 創建 authorized_keys 檔案
cat ~/.ssh/bastion_key.pub > docker/authorized_keys

# 檢查內容
cat docker/authorized_keys
```

#### 步驟 3：啟動容器

```bash
# 不需要重新構建，直接啟動
docker-compose up -d

# 測試
ssh -i ~/.ssh/bastion_key -p 2222 root@localhost
```

### 方式 3：運行時複製公鑰（最靈活）

```bash
# 1. 啟動容器
docker-compose up -d

# 2. 複製公鑰到容器
docker cp ~/.ssh/bastion_key.pub ansible-bastion:/root/
docker-compose exec bastion sh -c 'cat /root/bastion_key.pub >> /root/.ssh/authorized_keys'

# 3. 清理
docker-compose exec bastion rm /root/bastion_key.pub

# 4. 測試
ssh -i ~/.ssh/bastion_key -p 2222 root@localhost
```

---

## 部分 4：在 Ansible 中使用私鑰

### 配置 Ansible Inventory

編輯 `inventory/hosts.yml`：

```yaml
all:
  children:
    cisco_devices:
      vars:
        # 方法 1：指定私鑰位置
        ansible_ssh_private_key_file: /home/geek/.ssh/bastion_key

        # 方法 2：使用 ProxyCommand 和私鑰
        ansible_ssh_common_args: >
          -o ProxyCommand="ssh -W %h:%p
             -i /home/geek/.ssh/bastion_key
             -o StrictHostKeyChecking=no
             root@localhost -p 2222"
```

### 測試 Ansible 連接

```bash
# 1. 測試單個主機
ansible-inventory --host ISP1

# 2. Ping 測試
ansible cisco_devices -m ping

# 3. 詳細診斷
ansible cisco_devices -m ping -vvv
```

---

## 部分 5：多個使用者/多個密鑰

### 場景：允許多個 Ansible 主機連接

```bash
# 1. 生成多個密鑰對
ssh-keygen -t rsa -b 4096 -f ~/.ssh/ansible-host1 -N ""
ssh-keygen -t rsa -b 4096 -f ~/.ssh/ansible-host2 -N ""

# 2. 收集所有公鑰
cat ~/.ssh/ansible-host1.pub > docker/authorized_keys
cat ~/.ssh/ansible-host2.pub >> docker/authorized_keys
cat ~/.ssh/bastion_key.pub >> docker/authorized_keys

# 3. 檢查結果（應該有 3 行）
wc -l docker/authorized_keys
```

### authorized_keys 檔案格式

```
# 檔案內容示例（三個公鑰）
ssh-rsa AAAAB3NzaC1yc2E... ansible-host1
ssh-rsa AAAAB3NzaC1yc2E... ansible-host2
ssh-rsa AAAAB3NzaC1yc2E... bastion_key
```

---

## 部分 6：安全管理密鑰

### 🔒 密鑰安全檢查清單

```bash
# 1. 確認私鑰權限是 600（只有你能讀）
ls -la ~/.ssh/bastion_key
# 應該看到：-rw-------

# 2. 私鑰不要複製到 Docker 容器
# ❌ 不要做：COPY bastion_key /root/.ssh/
# ✅ 正確做：放在 Ansible 主機，使用 ProxyCommand

# 3. 不要在 GitHub 上提交私鑰！
echo "bastion_key" >> docker/.gitignore
echo "*.key" >> docker/.gitignore

# 4. 定期輪換密鑰
# 每半年生成新密鑰，更新 authorized_keys

# 5. 備份重要密鑰
cp ~/.ssh/bastion_key ~/.ssh/bastion_key.backup
```

### 查看公鑰指紋（驗証安全性）

```bash
# 查看本地公鑰指紋
ssh-keygen -l -f ~/.ssh/bastion_key

# 應該看到：
# 4096 SHA256:abc123def456... bastion_key (RSA)

# 查看跳板機上接收到的公鑰指紋
docker-compose exec bastion sh -c 'ssh-keygen -l -f /root/.ssh/authorized_keys'
```

---

## 部分 7：常見問題和故障排除

### 問題 1：Permission Denied (publickey)

**症狀**：
```
Permission denied (publickey).
```

**原因和解決方案**：

```bash
# 原因 1：公鑰不在 authorized_keys 中
# 解決：檢查公鑰是否複製到了 authorized_keys
docker-compose exec bastion cat /root/.ssh/authorized_keys
cat ~/.ssh/bastion_key.pub

# 原因 2：指定了錯誤的私鑰
# 解決：確認使用了正確的私鑰檔案
ssh -i ~/.ssh/bastion_key -p 2222 root@localhost

# 原因 3：authorized_keys 權限不對
# 解決：
docker-compose exec bastion chmod 600 /root/.ssh/authorized_keys
docker-compose exec bastion chmod 700 /root/.ssh
```

### 問題 2：識別檔案不可讀

**症狀**：
```
Permissions 0644 for '/home/user/.ssh/bastion_key' are too open.
```

**解決**：

```bash
# 修改私鑰權限為 600
chmod 600 ~/.ssh/bastion_key

# 驗証
ls -la ~/.ssh/bastion_key
# 應該看到：-rw------- (600)
```

### 問題 3：無法登入 root 使用者

**症狀**：
```
ssh: connect to host localhost port 2222: Permission denied
```

**檢查清單**：

```bash
# 1. 檢查容器是否運行
docker ps | grep bastion

# 2. 檢查 SSH 埠是否正確映射
docker port ansible-bastion
# 應該看到：22/tcp -> 0.0.0.0:2222

# 3. 檢查公鑰是否存在
docker-compose exec bastion ls -la /root/.ssh/authorized_keys

# 4. 檢查 sshd 是否啟動
docker-compose exec bastion ps aux | grep sshd

# 5. 檢查 SSH 配置
docker-compose exec bastion sshd -T
```

### 問題 4：多個密鑰但不確定用哪個

**解決**：

```bash
# 嘗試列出所有密鑰
ssh -i ~/.ssh/bastion_key -p 2222 root@localhost -vvv

# 從詳細日誌查看使用了哪個密鑰
# 尋找 "Offering public key:" 行

# 或使用 SSH config 明確指定
cat >> ~/.ssh/config << 'EOF'
Host bastion-local
    HostName localhost
    Port 2222
    User root
    IdentityFile ~/.ssh/bastion_key
    StrictHostKeyChecking no
EOF

# 然後直接連接
ssh bastion-local
```

---

## 部分 8：快速參考

### 生成密鑰

```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/bastion_key -N ""
```

### 配置公鑰

```bash
# 方式 1：編輯檔案後重新構建
cat ~/.ssh/bastion_key.pub > docker/authorized_keys
docker-compose build
docker-compose up -d

# 方式 2：使用 Volume 掛載
# 編輯 docker-compose.yml，掛載 authorized_keys
docker-compose up -d
```

### 測試連接

```bash
# 直接 SSH
ssh -i ~/.ssh/bastion_key -p 2222 root@localhost

# 或使用 SSH config
ssh bastion-local

# 詳細診斷
ssh -vvv -i ~/.ssh/bastion_key -p 2222 root@localhost
```

### 常見命令

```bash
# 查看本地公鑰
cat ~/.ssh/bastion_key.pub

# 查看跳板機上的公鑰
docker-compose exec bastion cat /root/.ssh/authorized_keys

# 新增一個公鑰
cat ~/.ssh/another_key.pub >> docker/authorized_keys
docker-compose restart bastion

# 移除一個公鑰
docker-compose exec bastion sh -c 'echo > /root/.ssh/authorized_keys'
# 然後重新新增需要的公鑰
```

---

## 工作流程總結

```
1. 生成密鑰對
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/bastion_key -N ""
   ↓
2. 配置跳板機公鑰
   cat ~/.ssh/bastion_key.pub > docker/authorized_keys
   ↓
3. 啟動 Docker 容器
   docker-compose up -d
   ↓
4. 測試 SSH 連接
   ssh -i ~/.ssh/bastion_key -p 2222 root@localhost
   ↓
5. 配置 Ansible
   在 inventory/hosts.yml 中指定 bastion_key
   ↓
6. 測試 Ansible
   ansible cisco_devices -m ping
```

---

還有問題嗎？告訴我你的具體情況，我幫你設置！
