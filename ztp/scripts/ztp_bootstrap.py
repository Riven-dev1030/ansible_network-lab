#!/usr/bin/env python3
"""
ZTP Bootstrap Script - 設備初始化與自動註冊
此腳本在新設備首次啟動時執行，負責：
1. 收集設備資訊
2. 向 Provisioning Server 註冊
3. 套用基本配置
4. 觸發 DHCP 更新以獲取固定管理 IP
"""

import sys
import json
import time
import re
from cli import cli, configure, execute

# ============================================
# 配置參數
# ============================================
PROVISIONING_SERVER = "192.168.1.100"
API_PORT = 5000
REGISTRATION_ENDPOINT = f"http://{PROVISIONING_SERVER}:{API_PORT}/api/register"

# ============================================
# 函數：收集設備資訊
# ============================================
def get_device_info():
    """收集設備的基本資訊"""
    print("正在收集設備資訊...")

    device_info = {}

    try:
        # 獲取版本資訊
        version_output = cli("show version")

        # 解析 MAC 地址
        mac_match = re.search(r'Base [Ee]thernet MAC [Aa]ddress\s+:\s+([0-9A-Fa-f:\.]+)', version_output)
        if mac_match:
            mac_raw = mac_match.group(1)
            # 標準化 MAC 地址格式 (aa:bb:cc:dd:ee:ff)
            mac_clean = mac_raw.replace('.', '').replace(':', '')
            device_info['mac_address'] = ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)])
        else:
            device_info['mac_address'] = "unknown"

        # 解析序列號
        serial_match = re.search(r'[Pp]rocessor board ID ([A-Z0-9]+)', version_output)
        if serial_match:
            device_info['serial_number'] = serial_match.group(1)
        else:
            device_info['serial_number'] = "unknown"

        # 解析型號
        model_match = re.search(r'[Cc]isco ([\w\-]+)', version_output)
        if model_match:
            device_info['model'] = model_match.group(1)
        else:
            device_info['model'] = "unknown"

        # 獲取當前 IP 地址
        ip_output = cli("show ip interface brief | include GigabitEthernet0/0")
        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', ip_output)
        if ip_match:
            device_info['current_ip'] = ip_match.group(1)
        else:
            device_info['current_ip'] = "dhcp_pending"

        # 獲取當前 hostname（如果已設定）
        hostname_output = cli("show running-config | include hostname")
        hostname_match = re.search(r'hostname\s+(\S+)', hostname_output)
        if hostname_match:
            device_info['current_hostname'] = hostname_match.group(1)
        else:
            device_info['current_hostname'] = "Router"

        print(f"設備資訊收集完成: MAC={device_info['mac_address']}, Serial={device_info['serial_number']}")
        return device_info

    except Exception as e:
        print(f"錯誤: 收集設備資訊失敗 - {str(e)}")
        return None

# ============================================
# 函數：向 Provisioning Server 註冊
# ============================================
def register_device(device_info):
    """向 Provisioning Server 註冊設備"""
    print(f"正在向 Provisioning Server 註冊: {REGISTRATION_ENDPOINT}")

    try:
        # 準備註冊數據
        registration_data = {
            "mac_address": device_info['mac_address'],
            "serial_number": device_info['serial_number'],
            "model": device_info['model'],
            "current_ip": device_info['current_ip'],
            "current_hostname": device_info['current_hostname'],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # 使用 Python 內建的 HTTP 請求（Cisco IOS 可能沒有 requests 庫）
        # 這裡使用 EEM 或 guest-shell 的方式
        # 簡化版本：使用 cli 命令模擬 HTTP POST

        # 方法 1: 使用 Cisco IOS 的 copy 命令（簡化）
        # 方法 2: 使用 guest-shell（如果可用）
        # 方法 3: 寫入文件後由外部讀取

        # 這裡我們使用簡化的方法：直接返回配置資訊供後續使用
        print("註冊數據準備完成:")
        print(json.dumps(registration_data, indent=2))

        # 實際環境中，這裡應該發送 HTTP POST 請求
        # 由於 Cisco IOS Python 限制，我們使用替代方案：
        # 將資訊寫入 syslog，由外部 server 監聽

        syslog_message = f"ZTP_REGISTRATION: {json.dumps(registration_data)}"
        try:
            cli(f'send log {syslog_message}')
        except:
            pass

        return registration_data

    except Exception as e:
        print(f"錯誤: 設備註冊失敗 - {str(e)}")
        return None

# ============================================
# 函數：套用基本配置
# ============================================
def apply_basic_config(device_info, assigned_hostname=None):
    """套用基本設備配置"""
    print("正在套用基本配置...")

    try:
        # 如果有分配的 hostname，使用它；否則使用 MAC 最後 4 位
        if assigned_hostname:
            hostname = assigned_hostname
        else:
            mac_suffix = device_info['mac_address'].replace(':', '')[-4:].upper()
            hostname = f"Device-{mac_suffix}"

        # 配置命令列表
        config_commands = [
            f"hostname {hostname}",
            "no ip domain-lookup",
            "!",
            "! 配置管理介面使用 DHCP",
            "interface GigabitEthernet0/0",
            " description OOB Management Interface",
            " ip address dhcp",
            f" ip dhcp client hostname {hostname}",
            " no shutdown",
            "!",
            "! 啟用 SSH",
            "ip domain-name lab.local",
            "crypto key generate rsa modulus 2048",
            "!",
            "! 配置本地使用者",
            "username admin privilege 15 secret admin123",
            "!",
            "! 配置 VTY",
            "line vty 0 4",
            " login local",
            " transport input ssh",
            "!",
            "! 配置 Console",
            "line con 0",
            " exec-timeout 0 0",
            " logging synchronous",
            "!",
            "! 啟用 Syslog",
            f"logging host {PROVISIONING_SERVER}",
            "logging trap informational",
            "!",
            "end"
        ]

        # 套用配置
        for cmd in config_commands:
            if cmd.strip() and not cmd.startswith('!'):
                try:
                    configure(cmd)
                except Exception as e:
                    print(f"警告: 命令執行失敗 - {cmd}: {str(e)}")

        print(f"基本配置已套用，hostname 設定為: {hostname}")

        # 儲存配置
        cli("write memory")
        print("配置已儲存")

        return True

    except Exception as e:
        print(f"錯誤: 套用配置失敗 - {str(e)}")
        return False

# ============================================
# 函數：更新 DHCP 租約
# ============================================
def renew_dhcp():
    """釋放並更新 DHCP 租約以獲取固定 IP"""
    print("正在更新 DHCP 租約...")

    try:
        # 等待一段時間讓 DHCP Server 完成綁定設定
        print("等待 DHCP Server 完成綁定設定...")
        time.sleep(10)

        # 釋放當前 IP
        cli("interface GigabitEthernet0/0")
        cli(" shutdown")
        time.sleep(2)
        cli(" no shutdown")

        print("DHCP 租約已更新")

        # 等待介面 up
        time.sleep(5)

        # 顯示新的 IP 地址
        new_ip = cli("show ip interface brief | include GigabitEthernet0/0")
        print("新的 IP 地址:")
        print(new_ip)

        return True

    except Exception as e:
        print(f"錯誤: DHCP 更新失敗 - {str(e)}")
        return False

# ============================================
# 主程序
# ============================================
def main():
    """ZTP 主程序"""
    print("=" * 60)
    print("ZTP Bootstrap Script - 開始執行")
    print("=" * 60)
    print("")

    # Step 1: 收集設備資訊
    print("[1/4] 收集設備資訊...")
    device_info = get_device_info()
    if not device_info:
        print("錯誤: 無法收集設備資訊，ZTP 中止")
        sys.exit(1)
    print("")

    # Step 2: 註冊設備
    print("[2/4] 向 Provisioning Server 註冊...")
    registration_result = register_device(device_info)
    if not registration_result:
        print("警告: 設備註冊失敗，繼續使用預設配置")
    print("")

    # Step 3: 套用基本配置
    print("[3/4] 套用基本配置...")
    success = apply_basic_config(device_info)
    if not success:
        print("錯誤: 配置套用失敗")
        sys.exit(1)
    print("")

    # Step 4: 更新 DHCP 租約
    print("[4/4] 更新 DHCP 租約以獲取固定 IP...")
    renew_dhcp()
    print("")

    print("=" * 60)
    print("ZTP Bootstrap 完成！")
    print("設備已就緒，可通過 Ansible 進行進一步配置")
    print("=" * 60)
    print("")
    print("提示:")
    print("1. 請檢查設備是否已獲得固定管理 IP")
    print("2. 使用 'show ip interface brief' 查看 IP 地址")
    print("3. 後續配置請使用 Ansible playbooks")
    print("")

# ============================================
# 程式入口
# ============================================
if __name__ == "__main__":
    main()
