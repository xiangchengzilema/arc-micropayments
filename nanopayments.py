"""
Nanopayments - Arc链上的批量纳米支付
利用Arc的~$0.01手续费实现高频小额支付
支持批量处理、队列管理、成本优化
"""

import sqlite3
import hashlib
import time
from typing import List, Dict, Optional
from datetime import datetime
from collections import defaultdict


class NanopaymentBatch:
    """纳米支付批处理"""

    def __init__(self, db_path: str = "payments.db"):
        self.db_path = db_path
        self._init_tables()

    def _init_tables(self):
        """初始化纳米支付表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nanopayments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                sender_address TEXT NOT NULL,
                receiver_address TEXT NOT NULL,
                amount_usdc REAL NOT NULL,
                status TEXT DEFAULT 'queued',
                reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                tx_hash TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nanopayment_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT UNIQUE NOT NULL,
                total_count INTEGER DEFAULT 0,
                total_amount REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                executed_at TIMESTAMP,
                estimated_fee REAL DEFAULT 0
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_batch_id ON nanopayments(batch_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_np_status ON nanopayments(status)')

        conn.commit()
        conn.close()

    def create_batch(self, payments: List[Dict], reference: str = "") -> str:
        """
        创建纳米支付批次

        Args:
            payments: [{"receiver": "0x...", "amount": 0.01, "reference": "AI query #1"}]
            reference: 批次备注

        Returns:
            batch_id
        """
        batch_id = "np_" + hashlib.sha256(
            f"{time.time()}{len(payments)}".encode()
        ).hexdigest()[:16]

        total_amount = sum(float(p.get("amount", 0)) for p in payments)
        estimated_fee = len(payments) * 0.01  # ~$0.01 per tx

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建批次记录
        cursor.execute('''
            INSERT INTO nanopayment_batches
            (batch_id, total_count, total_amount, estimated_fee)
            VALUES (?, ?, ?, ?)
        ''', (batch_id, len(payments), total_amount, estimated_fee))

        # 创建单条记录
        for p in payments:
            cursor.execute('''
                INSERT INTO nanopayments
                (batch_id, sender_address, receiver_address, amount_usdc, reference)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                batch_id,
                p.get("sender", "0x0000000000000000000000000000000000000000"),
                p.get("receiver", ""),
                float(p.get("amount", 0)),
                p.get("reference", "")
            ))

        conn.commit()
        conn.close()

        return batch_id

    def execute_batch(self, batch_id: str, wallet_service=None) -> Dict:
        """执行纳米支付批次"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取批次信息
        cursor.execute("SELECT * FROM nanopayment_batches WHERE batch_id = ?", (batch_id,))
        batch = cursor.fetchone()

        if not batch:
            conn.close()
            return {"success": False, "error": "Batch not found"}

        if batch[4] == "completed":
            conn.close()
            return {"success": False, "error": "Batch already completed"}

        # 获取批次内的支付
        cursor.execute("SELECT * FROM nanopayments WHERE batch_id = ? AND status = 'queued'",
                       (batch_id,))
        payments = cursor.fetchall()

        results = {"success": 0, "failed": 0, "total_fee": 0}

        for payment in payments:
            np_id, _, sender, receiver, amount, _, ref, _, _, _ = payment

            try:
                if wallet_service and wallet_service.is_configured:
                    # 真实执行
                    tx = wallet_service.send_usdc(
                        from_wallet_id=sender,
                        to_address=receiver,
                        amount=str(amount)
                    )
                    tx_hash = tx.get("tx_hash", "")
                    status = "completed" if tx.get("state") == "COMPLETE" else "pending"
                else:
                    # 模拟模式
                    tx_hash = "0xnp_" + hashlib.sha256(
                        f"{batch_id}{np_id}{time.time()}".encode()
                    ).hexdigest()[:62]
                    status = "completed"

                cursor.execute(
                    "UPDATE nanopayments SET status = ?, tx_hash = ?, executed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, tx_hash, np_id)
                )
                results["success"] += 1
                results["total_fee"] += 0.01

            except Exception as e:
                cursor.execute(
                    "UPDATE nanopayments SET status = 'failed' WHERE id = ?",
                    (np_id,)
                )
                results["failed"] += 1

        # 更新批次状态
        cursor.execute(
            "UPDATE nanopayment_batches SET status = 'completed', executed_at = CURRENT_TIMESTAMP WHERE batch_id = ?",
            (batch_id,)
        )

        conn.commit()
        conn.close()

        return {"success": True, "batch_id": batch_id, "results": results}

    def get_batch(self, batch_id: str) -> Optional[Dict]:
        """获取批次详情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM nanopayment_batches WHERE batch_id = ?", (batch_id,))
        batch = cursor.fetchone()

        if not batch:
            conn.close()
            return None

        cursor.execute("SELECT * FROM nanopayments WHERE batch_id = ?", (batch_id,))
        payments = cursor.fetchall()
        conn.close()

        return {
            "batch_id": batch[1],
            "total_count": batch[2],
            "total_amount": batch[3],
            "status": batch[4],
            "created_at": batch[5],
            "executed_at": batch[6],
            "estimated_fee": batch[7],
            "payments": [{
                "id": p[0],
                "receiver": p[3],
                "amount": p[4],
                "status": p[5],
                "reference": p[6],
                "tx_hash": p[9]
            } for p in payments]
        }

    def get_batch_stats(self) -> Dict:
        """获取纳米支付统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*), SUM(total_amount) FROM nanopayment_batches")
        batch_row = cursor.fetchone()

        cursor.execute("SELECT COUNT(*), SUM(amount_usdc) FROM nanopayments WHERE status = 'completed'")
        np_row = cursor.fetchone()

        conn.close()

        return {
            "total_batches": batch_row[0] or 0,
            "total_batch_amount": round(batch_row[1] or 0, 6),
            "completed_payments": np_row[0] or 0,
            "completed_amount": round(np_row[1] or 0, 6),
            "avg_payment": round((np_row[1] or 0) / max(np_row[0] or 1, 1), 6)
        }

    def list_batches(self, limit: int = 20) -> List[Dict]:
        """列出所有批次"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT batch_id, total_count, total_amount, status, created_at, estimated_fee FROM nanopayment_batches ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [{
            "batch_id": r[0],
            "total_count": r[1],
            "total_amount": r[2],
            "status": r[3],
            "created_at": r[4],
            "estimated_fee": r[5]
        } for r in rows]
