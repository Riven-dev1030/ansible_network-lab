# Ansible Network Lab

這是一個用於網絡自動化學習和測試的 Ansible 實驗室項目。

## 📋 項目簡介

本項目提供了一個網絡設備自動化配置和管理的實驗環境，使用 Ansible 來實現網絡設備的批量配置、監控和維護。

## 🚀 快速開始

### 前置要求

- Python 3.8+
- Ansible 2.9+
- 網絡設備訪問權限

### 安裝

```bash
# 克隆倉庫
git clone https://github.com/yourusername/ansible_network-lab.git
cd ansible_network-lab

# 安裝依賴
pip install ansible
```

## 📂 項目結構

```
ansible_network-lab/
├── README.md           # 項目說明文檔
├── inventory/          # 設備清單
├── playbooks/          # Ansible playbooks
├── roles/              # Ansible roles
└── group_vars/         # 組變量配置
```

## 📖 使用方法

```bash
# 運行 playbook
ansible-playbook -i inventory/hosts playbooks/your-playbook.yml
```

## 🤝 貢獻

歡迎提交 Issues 和 Pull Requests！

## 📄 許可證

MIT License

## 👤 作者

[Your Name]

## 📞 聯繫方式

如有問題，請通過 Issues 聯繫。
