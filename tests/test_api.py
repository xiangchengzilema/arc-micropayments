"""单元测试 - Flask API端点"""

import pytest
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db as payment_db


@pytest.fixture
def client():
    """创建测试客户端"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestPageRoutes:
    """页面路由测试"""

    def test_index_page(self, client):
        """测试首页"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Arc' in response.data or b'payment' in response.data.lower()

    def test_new_payment_page(self, client):
        """测试新建支付页面"""
        response = client.get('/payment/new')
        assert response.status_code == 200

    def test_receipt_page_not_found(self, client):
        """测试不存在的收据页面重定向"""
        response = client.get('/payment/99999')
        assert response.status_code == 302  # Redirect


class TestPaymentAPI:
    """支付API测试"""

    def test_create_payment(self, client):
        """测试创建支付"""
        response = client.post('/api/payment', json={
            'sender': '0x1111111111111111111111111111111111111111',
            'receiver': '0x2222222222222222222222222222222222222222',
            'amount': 0.05,
            'description': 'API test payment'
        })
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'payment_id' in data
        assert 'transaction_hash' in data

    def test_create_payment_no_data(self, client):
        """测试无数据创建支付"""
        response = client.post('/api/payment')
        data = json.loads(response.data)
        assert data['success'] is False

    def test_create_payment_invalid_address(self, client):
        """测试无效地址"""
        response = client.post('/api/payment', json={
            'receiver': 'invalid_address',
            'amount': 0.05
        })
        data = json.loads(response.data)
        assert data['success'] is False

    def test_create_payment_zero_amount(self, client):
        """测试零金额"""
        response = client.post('/api/payment', json={
            'receiver': '0x2222222222222222222222222222222222222222',
            'amount': 0
        })
        data = json.loads(response.data)
        assert data['success'] is False

    def test_get_payment(self, client):
        """测试获取支付详情"""
        # 先创建
        create_resp = client.post('/api/payment', json={
            'receiver': '0x2222222222222222222222222222222222222222',
            'amount': 0.01
        })
        create_data = json.loads(create_resp.data)
        payment_id = create_data['payment_id']

        # 再获取
        response = client.get(f'/api/payment/{payment_id}')
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['payment']['id'] == payment_id

    def test_get_payment_not_found(self, client):
        """测试获取不存在的支付"""
        response = client.get('/api/payment/99999')
        assert response.status_code == 404

    def test_recent_payments(self, client):
        """测试获取最近支付"""
        response = client.get('/api/payments/recent')
        data = json.loads(response.data)
        assert data['success'] is True
        assert isinstance(data['payments'], list)

    def test_address_payments(self, client):
        """测试按地址查询"""
        response = client.get('/api/address/0x1111111111111111111111111111111111111111')
        data = json.loads(response.data)
        assert data['success'] is True


class TestWalletAPI:
    """钱包API测试"""

    def test_create_wallet(self, client):
        """测试创建钱包"""
        response = client.post('/api/wallet/create')
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'wallet' in data
        assert data['wallet']['blockchain'] == 'ARC-TESTNET'

    def test_list_wallets(self, client):
        """测试列出钱包"""
        response = client.get('/api/wallet/list')
        data = json.loads(response.data)
        assert data['success'] is True


class TestStatsAPI:
    """统计API测试"""

    def test_get_stats(self, client):
        """测试获取统计"""
        response = client.get('/api/stats')
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'stats' in data
        assert 'total_count' in data['stats']
        assert 'total_amount' in data['stats']
