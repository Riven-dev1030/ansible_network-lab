#!/bin/bash
# 快速開始腳本 - 企業網路實驗室 Ansible 部署

set -e

echo "════════════════════════════════════════════════════════"
echo "  企業網路模擬 Lab - Ansible 自動化部署"
echo "  適合 8GB RAM IOL 環境 | 總計 10 台設備"
echo "════════════════════════════════════════════════════════"
echo ""

# 檢查 Ansible 是否安裝
if ! command -v ansible &> /dev/null; then
    echo "❌ Ansible 未安裝"
    echo "請執行: pip install -r requirements.txt"
    exit 1
fi

echo "✅ Ansible 已安裝: $(ansible --version | head -1)"
echo ""

# 選單
echo "請選擇執行模式:"
echo ""
echo "  1) 完整部署 (S0-S8 全部階段)"
echo "  2) 分階段部署 (逐步執行)"
echo "  3) 僅驗證 (不部署)"
echo "  4) 檢查連接"
echo "  0) 退出"
echo ""
read -p "請輸入選項 [0-4]: " choice

case $choice in
    1)
        echo ""
        echo "🚀 開始完整部署..."
        echo ""
        ansible-playbook playbooks/deploy_all.yml
        ;;
    2)
        echo ""
        echo "📋 分階段部署"
        echo ""
        PS3="請選擇階段: "
        stages=("S0: 準備與基線"
                "S1: HQ L2/L3 與 HSRP"
                "S2: DMZ 與 R3 接入"
                "S3: OSPF 聚合預設"
                "S4: GRE Underlay 與 Tunnel"
                "S5: 分公司 LAN"
                "S6: eBGP 對上游"
                "S7: NAT 與 ACL (選配)"
                "S8: 可觀測性與日誌"
                "返回")
        select stage in "${stages[@]}"; do
            case $REPLY in
                1) ansible-playbook playbooks/s0_preparation.yml; break;;
                2) ansible-playbook playbooks/s1_hq_vlan_hsrp.yml; break;;
                3) ansible-playbook playbooks/s2_dmz_r3.yml; break;;
                4) ansible-playbook playbooks/s3_ospf_summary.yml; break;;
                5) ansible-playbook playbooks/s4_gre_tunnel.yml; break;;
                6) ansible-playbook playbooks/s5_branch_lan.yml; break;;
                7) ansible-playbook playbooks/s6_ebgp.yml; break;;
                8) ansible-playbook playbooks/s7_nat_acl.yml; break;;
                9) ansible-playbook playbooks/s8_observability.yml; break;;
                10) break;;
                *) echo "無效選項"; break;;
            esac
        done
        ;;
    3)
        echo ""
        echo "🔍 執行驗證..."
        echo ""
        ansible-playbook playbooks/verify_deployment.yml
        ;;
    4)
        echo ""
        echo "🔌 檢查設備連接..."
        echo ""
        ansible all -m cisco.ios.ios_command -a "commands='show version'" --one-line
        ;;
    0)
        echo "再見！"
        exit 0
        ;;
    *)
        echo "❌ 無效選項"
        exit 1
        ;;
esac

echo ""
echo "════════════════════════════════════════════════════════"
echo "  執行完成！"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📖 更多資訊請參考 README.md"
echo "📊 查看日誌: tail -f ansible.log"
echo ""
