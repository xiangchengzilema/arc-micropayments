"""单元测试 - 支付记录模型"""

import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import PaymentRecord


@pytest.fixture
def db(tmp_path):
    """创建临时数据库"""
    db_path = str(tmp_path / "test_payments.db")
    return PaymentRecord(db_path)


class TestPaymentRecord:
    """PaymentRecord 测试类"""

    def test_init_database(self, db):
        """测试数据库初始化"""
        assert db is not None
        assert db.db_path is not None

    def test_create_payment(self, db):
        """测试创建支付记录"""
        payment_id = db.create_payment(
            transaction_hash="0xabc123",
            sender_address="0x1111111111111111111111111111111111111111",
            receiver_address="0x2222222222222222222222222222222222222222",
            amount_usdc=0.05,
            description="Test payment"
        )
        assert payment_id is not None
        assert payment_id > 0

    def test_get_payment(self, db):
        """测试获取支付记录"""
        payment_id = db.create_payment(
            transaction_hash="0xdef456",
            sender_address="0x1111111111111111111111111111111111111111",
            receiver_address="0x2222222222222222222222222222222222222222",
            amount_usdc=0.10,
            description="Get test"
        )

        payment = db.get_payment(payment_id)
        assert payment is not None
        assert payment['transaction_hash'] == "0xdef456"
        assert payment['amount_usdc'] == 0.10
        assert payment['status'] == 'pending'
        assert payment['description'] == "Get test"

    def test_get_payment_not_found(self, db):
        """测试获取不存在的支付记录"""
        payment = db.get_payment(99999)
        assert payment is None

    def test_update_status(self, db):
        """测试更新支付状态"""
        db.create_payment(
            transaction_hash="0xghi789",
            sender_address="0x1111111111111111111111111111111111111111",
            receiver_address="0x2222222222222222222222222222222222222222",
            amount_usdc=0.01
        )

        result = db.update_status("0xghi789", "confirmed")
        assert result is True

        # 验证状态已更新
        payments = db.get_all_payments()
        target = [p for p in payments if p['transaction_hash'] == "0xghi789"][0]
        assert target['status'] == 'confirmed'
        assert target['confirmed_at'] is not None

    def test_get_all_payments(self, db):
        """测试获取所有支付记录"""
        for i in range(5):
            db.create_payment(
                transaction_hash=f"0x{i:064x}",
                sender_address="0x1111111111111111111111111111111111111111",
                receiver_address="0x2222222222222222222222222222222222222222",
                amount_usdc=0.01 * (i + 1)
            )

        payments = db.get_all_payments()
        assert len(payments) == 5

        # 应该按时间倒序
        assert payments[0]['amount_usdc'] == 0.05

    def test_get_all_payments_with_limit(self, db):
        """测试带limit的获取"""
        for i in range(10):
            db.create_payment(
                transaction_hash=f"0xlimit{i:060x}",
                sender_address="0x1111111111111111111111111111111111111111",
                receiver_address="0x2222222222222222222222222222222222222222",
                amount_usdc=0.01
            )

        payments = db.get_all_payments(limit=3)
        assert len(payments) == 3

    def test_get_payments_by_address(self, db):
        """测试按地址查询"""
        sender = "0xAAAA000000000000000000000000000000000000"
        receiver = "0xBBBB000000000000000000000000000000000000"

        db.create_payment(
            transaction_hash="0xaddr001",
            sender_address=sender,
            receiver_address=receiver,
            amount_usdc=0.05
        )
        db.create_payment(
            transaction_hash="0xaddr002",
            sender_address=receiver,
            receiver_address=sender,
            amount_usdc=0.03
        )
        db.create_payment(
            transaction_hash="0xaddr003",
            sender_address="0xCCCC000000000000000000000000000000000000",
            receiver_address="0xDDDD000000000000000000000000000000000000",
            amount_usdc=0.01
        )

        # 查询sender的记录（作为sender出现1次，作为receiver出现1次）
        results = db.get_payments_by_address(sender)
        assert len(results) == 2

    def test_get_stats(self, db):
        """测试统计功能"""
        db.create_payment(
            transaction_hash="0xstat001",
            sender_address="0x1111111111111111111111111111111111111111",
            receiver_address="0x2222222222222222222222222222222222222222",
            amount_usdc=0.10
        )
        db.create_payment(
            transaction_hash="0xstat002",
            sender_address="0x1111111111111111111111111111111111111111",
            receiver_address="0x2222222222222222222222222222222222222222",
            amount_usdc=0.20
        )
        db.update_status("0xstat001", "confirmed")

        stats = db.get_stats()
        assert stats['total_count'] == 2
        assert stats['total_amount'] == 0.30
        assert stats['confirmed_count'] == 1
        assert stats['avg_amount'] == 0.15

    def test_get_stats_empty(self, db):
        """测试空数据库的统计"""
        stats = db.get_stats()
        assert stats['total_count'] == 0
        assert stats['total_amount'] == 0
        assert stats['confirmed_count'] == 0
        assert stats['today_count'] == 0
        assert stats['avg_amount'] == 0
