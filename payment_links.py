"""
Payment Links - 生成可分享的支付链接
支持唯一链接、到期管理、自动确认
"""

import sqlite3
import hashlib
import time
import secrets
from typing import Dict, Optional, List
from datetime import datetime


class PaymentLinkManager:
    """支付链接管理器"""

    def __init__(self, db_path: str = "payments.db", base_url: str = "http://localhost:5000"):
        self.db_path = db_path
        self.base_url = base_url.rstrip("/")
        self._init_table()

    def _init_table(self):
        """初始化支付链接表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_code TEXT UNIQUE NOT NULL,
                receiver_address TEXT NOT NULL,
                amount_usdc REAL,
                description TEXT,
                status TEXT DEFAULT 'active',
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                creator_address TEXT,
                metadata TEXT
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_code ON payment_links(link_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_status ON payment_links(status)')

        conn.commit()
        conn.close()

    def create_link(
        self,
        receiver_address: str,
        amount_usdc: float = None,
        description: str = "",
        max_uses: int = 1,
        expires_hours: int = 72,
        creator_address: str = "",
        metadata: dict = None
    ) -> Dict:
        """
        创建支付链接

        Args:
            receiver_address: 收款地址
            amount_usdc: 固定金额（None表示自定义）
            description: 描述
            max_uses: 最大使用次数（0=无限）
            expires_hours: 过期时间（小时）
            creator_address: 创建者地址
            metadata: 额外数据

        Returns:
            支付链接信息
        """
        # 生成唯一链接码
        link_code = secrets.token_urlsafe(12)

        # 计算过期时间
        expires_at = None
        if expires_hours > 0:
            conn_temp = sqlite3.connect(self.db_path)
            cursor_temp = conn_temp.cursor()
            cursor_temp.execute(
                "SELECT datetime('now', '+{} hours')".format(expires_hours)
            )
            expires_at = cursor_temp.fetchone()[0]
            conn_temp.close()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        import json
        cursor.execute('''
            INSERT INTO payment_links
            (link_code, receiver_address, amount_usdc, description,
             max_uses, expires_at, creator_address, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            link_code,
            receiver_address,
            amount_usdc,
            description,
            max_uses,
            expires_at,
            creator_address,
            json.dumps(metadata) if metadata else None
        ))

        link_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "id": link_id,
            "link_code": link_code,
            "url": f"{self.base_url}/pay/{link_code}",
            "receiver_address": receiver_address,
            "amount_usdc": amount_usdc,
            "description": description,
            "max_uses": max_uses,
            "expires_at": expires_at,
            "status": "active"
        }

    def get_link(self, link_code: str) -> Optional[Dict]:
        """获取支付链接详情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM payment_links WHERE link_code = ?", (link_code,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        link = {
            "id": row[0],
            "link_code": row[1],
            "url": f"{self.base_url}/pay/{row[1]}",
            "receiver_address": row[2],
            "amount_usdc": row[3],
            "description": row[4],
            "status": row[5],
            "max_uses": row[6],
            "used_count": row[7],
            "expires_at": row[8],
            "created_at": row[9],
            "creator_address": row[10],
            "metadata": row[11]
        }

        # 检查是否过期
        if link["expires_at"] and link["status"] == "active":
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT datetime('now')"
            )
            now = cursor.fetchone()[0]
            if now > link["expires_at"]:
                cursor.execute(
                    "UPDATE payment_links SET status = 'expired' WHERE link_code = ?",
                    (link_code,)
                )
                conn.commit()
                link["status"] = "expired"
            conn.close()

        return link

    def use_link(self, link_code: str, sender_address: str, amount: float = None) -> Dict:
        """使用支付链接"""
        link = self.get_link(link_code)

        if not link:
            return {"success": False, "error": "Link not found"}

        if link["status"] != "active":
            return {"success": False, "error": f"Link is {link['status']}"}

        if link["max_uses"] > 0 and link["used_count"] >= link["max_uses"]:
            return {"success": False, "error": "Link has reached max uses"}

        payment_amount = amount or link["amount_usdc"]
        if not payment_amount:
            return {"success": False, "error": "Amount required"}

        # 更新使用次数
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE payment_links SET used_count = used_count + 1 WHERE link_code = ?",
            (link_code,)
        )

        # 检查是否达到最大使用次数
        new_count = link["used_count"] + 1
        if link["max_uses"] > 0 and new_count >= link["max_uses"]:
            cursor.execute(
                "UPDATE payment_links SET status = 'used' WHERE link_code = ?",
                (link_code,)
            )

        conn.commit()
        conn.close()

        return {
            "success": True,
            "receiver_address": link["receiver_address"],
            "amount_usdc": payment_amount,
            "description": link["description"],
            "link_code": link_code
        }

    def deactivate_link(self, link_code: str) -> bool:
        """停用支付链接"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE payment_links SET status = 'deactivated' WHERE link_code = ?",
            (link_code,)
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def list_links(self, status: str = None, limit: int = 20) -> List[Dict]:
        """列出支付链接"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if status:
            cursor.execute(
                "SELECT * FROM payment_links WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM payment_links ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )

        rows = cursor.fetchall()
        conn.close()

        return [{
            "id": r[0],
            "link_code": r[1],
            "url": f"{self.base_url}/pay/{r[1]}",
            "receiver_address": r[2],
            "amount_usdc": r[3],
            "description": r[4],
            "status": r[5],
            "max_uses": r[6],
            "used_count": r[7],
            "expires_at": r[8],
            "created_at": r[9]
        } for r in rows]

    def get_link_stats(self) -> Dict:
        """获取链接统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM payment_links")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM payment_links WHERE status = 'active'")
        active = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(used_count) FROM payment_links")
        total_uses = cursor.fetchone()[0] or 0

        conn.close()

        return {
            "total_links": total,
            "active_links": active,
            "total_uses": total_uses
        }
