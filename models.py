"""
数据库模型 - 支付记录存储
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional

class PaymentRecord:
    """支付记录模型"""

    def __init__(self, db_path: str = "payments.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_hash TEXT UNIQUE NOT NULL,
                sender_address TEXT NOT NULL,
                receiver_address TEXT NOT NULL,
                amount_usdc REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TIMESTAMP,
                description TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def create_payment(
        self,
        transaction_hash: str,
        sender_address: str,
        receiver_address: str,
        amount_usdc: float,
        description: str = ""
    ) -> int:
        """创建新的支付记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO payments
            (transaction_hash, sender_address, receiver_address, amount_usdc, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (transaction_hash, sender_address, receiver_address, amount_usdc, description))

        payment_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return payment_id

    def update_status(self, transaction_hash: str, status: str) -> bool:
        """更新支付状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE payments
            SET status = ?, confirmed_at = CURRENT_TIMESTAMP
            WHERE transaction_hash = ?
        ''', (status, transaction_hash))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def get_payment(self, payment_id: int) -> Optional[Dict]:
        """获取单条支付记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0],
                'transaction_hash': row[1],
                'sender_address': row[2],
                'receiver_address': row[3],
                'amount_usdc': row[4],
                'status': row[5],
                'created_at': row[6],
                'confirmed_at': row[7],
                'description': row[8]
            }
        return None

    def get_all_payments(self, limit: int = 100) -> List[Dict]:
        """获取所有支付记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM payments ORDER BY created_at DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
        conn.close()

        payments = []
        for row in rows:
            payments.append({
                'id': row[0],
                'transaction_hash': row[1],
                'sender_address': row[2],
                'receiver_address': row[3],
                'amount_usdc': row[4],
                'status': row[5],
                'created_at': row[6],
                'confirmed_at': row[7],
                'description': row[8]
            })

        return payments

    def get_stats(self) -> Dict:
        """获取支付统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 总支付数
        cursor.execute('SELECT COUNT(*) FROM payments')
        total_count = cursor.fetchone()[0]

        # 总金额
        cursor.execute('SELECT COALESCE(SUM(amount_usdc), 0) FROM payments')
        total_amount = cursor.fetchone()[0]

        # 确认数
        cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'confirmed'")
        confirmed_count = cursor.fetchone()[0]

        # 今日支付数
        cursor.execute(
            "SELECT COUNT(*) FROM payments WHERE date(created_at) = date('now')"
        )
        today_count = cursor.fetchone()[0]

        # 今日金额
        cursor.execute(
            "SELECT COALESCE(SUM(amount_usdc), 0) FROM payments WHERE date(created_at) = date('now')"
        )
        today_amount = cursor.fetchone()[0]

        # 平均支付金额
        avg_amount = total_amount / total_count if total_count > 0 else 0

        conn.close()

        return {
            'total_count': total_count,
            'total_amount': round(total_amount, 6),
            'confirmed_count': confirmed_count,
            'today_count': today_count,
            'today_amount': round(today_amount, 6),
            'avg_amount': round(avg_amount, 6)
        }

    def get_payments_by_address(self, address: str, limit: int = 100) -> List[Dict]:
        """获取地址相关的支付记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM payments
            WHERE sender_address = ? OR receiver_address = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (address, address, limit))
        rows = cursor.fetchall()
        conn.close()

        payments = []
        for row in rows:
            payments.append({
                'id': row[0],
                'transaction_hash': row[1],
                'sender_address': row[2],
                'receiver_address': row[3],
                'amount_usdc': row[4],
                'status': row[5],
                'created_at': row[6],
                'confirmed_at': row[7],
                'description': row[8]
            })

        return payments
