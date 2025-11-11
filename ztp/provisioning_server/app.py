#!/usr/bin/env python3
"""
ZTP Provisioning Server API
提供設備註冊、DHCP 綁定管理、配置生成等功能
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import yaml
import json
import os
import logging
from datetime import datetime
import subprocess
import re

# ============================================
# 應用初始化
# ============================================
app = Flask(__name__)
CORS(app)

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ztp_provisioning.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# 配置文件路徑
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEVICE_INVENTORY_PATH = os.path.join(BASE_DIR, '../dhcp/device_inventory.yml')
DHCP_CONFIG_PATH = '/etc/dhcp/dhcpd.conf'
REGISTRATION_LOG = '/var/log/ztp_registrations.json'

# ============================================
# 載入設備清單
# ============================================
def load_device_inventory():
    """載入設備清單"""
    try:
        with open(DEVICE_INVENTORY_PATH, 'r') as f:
            inventory = yaml.safe_load(f)
        return inventory
    except Exception as e:
        logger.error(f"載入設備清單失敗: {e}")
        return None

# ============================================
# 根據 MAC 查找設備
# ============================================
def find_device_by_mac(mac_address):
    """根據 MAC 地址查找設備資訊"""
    inventory = load_device_inventory()
    if not inventory:
        return None

    # 標準化 MAC 地址格式
    mac_normalized = mac_address.lower().replace('-', ':').replace('.', ':')

    devices = inventory.get('devices', {})
    for hostname, device_info in devices.items():
        device_mac = device_info.get('mac_address', '').lower().replace('-', ':').replace('.', ':')
        if device_mac == mac_normalized:
            device_info['hostname'] = hostname
            return device_info

    return None

# ============================================
# 記錄註冊資訊
# ============================================
def log_registration(registration_data):
    """記錄設備註冊資訊到日誌文件"""
    try:
        # 讀取現有記錄
        registrations = []
        if os.path.exists(REGISTRATION_LOG):
            with open(REGISTRATION_LOG, 'r') as f:
                registrations = json.load(f)

        # 添加新記錄
        registrations.append(registration_data)

        # 寫回文件
        with open(REGISTRATION_LOG, 'w') as f:
            json.dump(registrations, f, indent=2)

        logger.info(f"註冊記錄已保存: {registration_data['hostname']}")
        return True
    except Exception as e:
        logger.error(f"保存註冊記錄失敗: {e}")
        return False

# ============================================
# 更新 DHCP 配置（動態綁定）
# ============================================
def update_dhcp_binding(hostname, mac_address, ip_address):
    """動態更新 DHCP 靜態綁定"""
    try:
        logger.info(f"更新 DHCP 綁定: {hostname} ({mac_address}) -> {ip_address}")

        # 讀取當前 DHCP 配置
        if not os.path.exists(DHCP_CONFIG_PATH):
            logger.error(f"DHCP 配置文件不存在: {DHCP_CONFIG_PATH}")
            return False

        with open(DHCP_CONFIG_PATH, 'r') as f:
            dhcp_config = f.read()

        # 檢查是否已存在此設備的綁定
        host_block_pattern = f'host {hostname} {{[^}}]*}}'
        if re.search(host_block_pattern, dhcp_config, re.DOTALL):
            logger.info(f"設備 {hostname} 的 DHCP 綁定已存在，跳過更新")
            return True

        # 生成新的 host 綁定配置
        mac_formatted = mac_address.replace(':', ':')
        new_host_block = f'''
    host {hostname} {{
        hardware ethernet {mac_formatted};
        fixed-address {ip_address};
        option host-name "{hostname}";
        option bootfile-name "configs/{hostname}-config.py";
    }}
'''

        # 在 subnet 區塊中添加新綁定（在最後一個 } 之前）
        # 找到 subnet 192.168.1.0 的結束位置
        subnet_pattern = r'(subnet 192\.168\.1\.0 netmask 255\.255\.255\.0 \{[^}]*)(})'
        match = re.search(subnet_pattern, dhcp_config, re.DOTALL)

        if match:
            # 在 subnet 結束前插入新綁定
            updated_config = dhcp_config[:match.end(1)] + new_host_block + dhcp_config[match.end(1):]

            # 備份原配置
            backup_path = f"{DHCP_CONFIG_PATH}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w') as f:
                f.write(dhcp_config)
            logger.info(f"DHCP 配置已備份: {backup_path}")

            # 寫入新配置
            with open(DHCP_CONFIG_PATH, 'w') as f:
                f.write(updated_config)
            logger.info("DHCP 配置已更新")

            # 重啟 DHCP 服務
            try:
                subprocess.run(['systemctl', 'restart', 'isc-dhcp-server'], check=True)
                logger.info("DHCP 服務已重啟")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"重啟 DHCP 服務失敗: {e}")
                return False
        else:
            logger.error("無法找到 subnet 配置區塊")
            return False

    except Exception as e:
        logger.error(f"更新 DHCP 綁定失敗: {e}")
        return False

# ============================================
# API 路由
# ============================================

@app.route('/')
def index():
    """API 首頁"""
    return jsonify({
        'service': 'ZTP Provisioning Server',
        'version': '1.0',
        'status': 'running',
        'endpoints': {
            'register': '/api/register',
            'devices': '/api/devices',
            'registrations': '/api/registrations',
            'health': '/api/health'
        }
    })

@app.route('/api/health')
def health():
    """健康檢查"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/devices', methods=['GET'])
def get_devices():
    """獲取所有設備清單"""
    inventory = load_device_inventory()
    if inventory:
        return jsonify({'success': True, 'devices': inventory['devices']})
    else:
        return jsonify({'success': False, 'error': '無法載入設備清單'}), 500

@app.route('/api/registrations', methods=['GET'])
def get_registrations():
    """獲取所有註冊記錄"""
    try:
        if os.path.exists(REGISTRATION_LOG):
            with open(REGISTRATION_LOG, 'r') as f:
                registrations = json.load(f)
            return jsonify({'success': True, 'registrations': registrations})
        else:
            return jsonify({'success': True, 'registrations': []})
    except Exception as e:
        logger.error(f"讀取註冊記錄失敗: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register_device():
    """
    設備註冊端點
    接收設備資訊，分配固定 IP，更新 DHCP 綁定
    """
    try:
        # 獲取請求數據
        data = request.get_json()
        logger.info(f"收到註冊請求: {data}")

        # 必需欄位驗證
        required_fields = ['mac_address']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必需欄位: {field}'
                }), 400

        mac_address = data['mac_address']
        serial_number = data.get('serial_number', 'unknown')
        model = data.get('model', 'unknown')
        current_ip = data.get('current_ip', 'unknown')

        # 根據 MAC 地址查找設備
        device_info = find_device_by_mac(mac_address)

        if not device_info:
            logger.warning(f"未找到 MAC 地址對應的設備: {mac_address}")
            return jsonify({
                'success': False,
                'error': f'未找到 MAC 地址 {mac_address} 對應的設備配置',
                'message': '請檢查設備清單文件 device_inventory.yml'
            }), 404

        # 準備註冊資料
        hostname = device_info['hostname']
        assigned_ip = device_info['mgmt_ip']

        registration_data = {
            'hostname': hostname,
            'mac_address': mac_address,
            'assigned_ip': assigned_ip,
            'serial_number': serial_number,
            'model': model,
            'current_ip': current_ip,
            'device_type': device_info.get('device_type', 'cisco_ios'),
            'role': device_info.get('role', 'unknown'),
            'location': device_info.get('location', 'unknown'),
            'timestamp': datetime.now().isoformat(),
            'status': 'registered'
        }

        # 記錄註冊資訊
        log_registration(registration_data)

        # 更新 DHCP 綁定
        dhcp_update_success = update_dhcp_binding(hostname, mac_address, assigned_ip)

        # 返回成功響應
        response = {
            'success': True,
            'message': f'設備 {hostname} 註冊成功',
            'device': {
                'hostname': hostname,
                'assigned_ip': assigned_ip,
                'mac_address': mac_address,
                'role': device_info.get('role'),
                'location': device_info.get('location')
            },
            'dhcp_binding_updated': dhcp_update_success,
            'next_steps': [
                '請重啟設備或執行 DHCP renew',
                f'設備將獲得固定 IP: {assigned_ip}',
                '後續配置請使用 Ansible playbooks'
            ]
        }

        logger.info(f"設備註冊成功: {hostname} -> {assigned_ip}")
        return jsonify(response), 200

    except Exception as e:
        logger.error(f"設備註冊失敗: {e}")
        return jsonify({
            'success': False,
            'error': f'註冊失敗: {str(e)}'
        }), 500

# ============================================
# 主程序
# ============================================
if __name__ == '__main__':
    # 檢查設備清單文件
    if not os.path.exists(DEVICE_INVENTORY_PATH):
        logger.error(f"設備清單文件不存在: {DEVICE_INVENTORY_PATH}")
        print(f"錯誤: 找不到設備清單文件 {DEVICE_INVENTORY_PATH}")
        exit(1)

    # 創建日誌目錄
    os.makedirs('/var/log', exist_ok=True)

    # 啟動服務
    logger.info("ZTP Provisioning Server 啟動中...")
    print("=" * 60)
    print("ZTP Provisioning Server")
    print("=" * 60)
    print(f"設備清單: {DEVICE_INVENTORY_PATH}")
    print(f"DHCP 配置: {DHCP_CONFIG_PATH}")
    print(f"註冊日誌: {REGISTRATION_LOG}")
    print("=" * 60)
    print("")

    # 運行 Flask 應用
    app.run(host='0.0.0.0', port=5000, debug=True)
