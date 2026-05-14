"""单元测试 - Circle钱包服务"""

import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from circle_wallet_service import CircleWalletService


@pytest.fixture
def service():
    """创建模拟模式的钱包服务"""
    return CircleWalletService(api_key="", entity_secret="")


class TestCircleWalletService:
    """CircleWalletService 模拟模式测试"""

    def test_not_configured_without_keys(self, service):
        """测试未配置API密钥时为模拟模式"""
        assert service.is_configured is False

    def test_configured_with_keys(self):
        """测试配置API密钥后为正常模式"""
        svc = CircleWalletService(api_key="test_key", entity_secret="test_secret")
        assert svc.is_configured is True

    def test_create_wallet_simulation(self, service):
        """测试模拟模式创建钱包"""
        wallet = service.create_wallet("sim_set_001")
        assert wallet is not None
        assert wallet['address'].startswith('0x')
        assert wallet['blockchain'] == 'ARC-TESTNET'
        assert wallet['state'] == 'LIVE'

    def test_get_wallet_balance_simulation(self, service):
        """测试模拟模式查询余额"""
        balance = service.get_wallet_balance("sim_wallet_001")
        assert balance is not None
        assert 'balances' in balance

    def test_send_usdc_simulation(self, service):
        """测试模拟模式发送USDC"""
        result = service.send_usdc(
            from_wallet_id="sim_wallet_001",
            to_address="0x2222222222222222222222222222222222222222",
            amount="0.05"
        )
        assert result is not None
        assert result['state'] == 'COMPLETE'
        assert result['tx_hash'].startswith('0x')
        assert result['amounts'] == ['0.05']

    def test_get_transaction_status_simulation(self, service):
        """测试模拟模式查询交易状态"""
        status = service.get_transaction_status("sim_tx_001")
        assert status is not None
        assert status['state'] == 'COMPLETE'

    def test_list_wallets_simulation(self, service):
        """测试模拟模式列出钱包"""
        wallets = service.list_wallets()
        assert isinstance(wallets, list)

    def test_get_or_create_wallet_set_simulation(self, service):
        """测试模拟模式获取钱包集"""
        ws_id = service.get_or_create_wallet_set()
        assert ws_id == "sim_wallet_set_001"


class TestValidation:
    """输入验证测试"""

    def test_validate_valid_address(self):
        """测试有效地址"""
        assert CircleWalletService.validate_address(
            "0x2222222222222222222222222222222222222222"
        ) is True

    def test_validate_address_no_prefix(self):
        """测试缺少0x前缀"""
        assert CircleWalletService.validate_address(
            "2222222222222222222222222222222222222222"
        ) is False

    def test_validate_address_wrong_length(self):
        """测试长度不正确"""
        assert CircleWalletService.validate_address(
            "0x2222"
        ) is False

    def test_validate_address_invalid_hex(self):
        """测试非十六进制字符"""
        assert CircleWalletService.validate_address(
            "0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG"
        ) is False

    def test_format_usdc_amount(self):
        """测试USDC金额格式化"""
        assert CircleWalletService.format_usdc_amount(0.05) == "0.050000"
        assert CircleWalletService.format_usdc_amount(1.0) == "1.000000"
        assert CircleWalletService.format_usdc_amount(0.000001) == "0.000001"
