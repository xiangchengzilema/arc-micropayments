"""
Webhook事件处理器 - 处理Circle的支付状态回调
支持签名验证、事件分发、自动状态更新
"""

import hmac
import hashlib
import json
import sqlite3
from typing import Dict, Optional, Callable
from datetime import datetime


# Circle Webhook事件类型
EVENT_PAYMENT_CREATED = "payment.created"
EVENT_PAYMENT_CONFIRMED = "payment.confirmed"
EVENT_PAYMENT_FAILED = "payment.failed"
EVENT_TRANSFER_CREATED = "transfer.created"
EVENT_TRANSFER_COMPLETED = "transfer.completed"
EVENT_TRANSFER_FAILED = "transfer.failed"
EVENT_WALLET_CREATED = "wallet.created"
EVENT_WALLET_ADDRESS_CREATED = "wallet.address.created"


class WebhookEvent:
    """Webhook事件对象"""

    def __init__(self, event_type: str, data: dict, timestamp: str = None):
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.processed = False
        self.error = None

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "processed": self.processed,
            "error": self.error
        }


class WebhookHandler:
    """Circle Webhook处理器"""

    def __init__(self, db_path: str = "payments.db", webhook_secret: str = ""):
        self.db_path = db_path
        self.webhook_secret = webhook_secret
        self._handlers: Dict[str, Callable] = {}
        self._init_events_table()

    def _init_events_table(self):
        """初始化事件日志表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_id TEXT UNIQUE,
                data TEXT NOT NULL,
                processed INTEGER DEFAULT 0,
                error TEXT,
                received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """验证Webhook签名（防止伪造请求）"""
        if not self.webhook_secret:
            return True  # 无密钥时跳过验证

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def register_handler(self, event_type: str, handler: Callable):
        """注册事件处理器"""
        self._handlers[event_type] = handler

    def handle(self, payload: bytes, signature: str = "") -> WebhookEvent:
        """处理Webhook请求"""
        # 解析payload
        try:
            body = json.loads(payload.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            event = WebhookEvent("parse_error", {})
            event.error = str(e)
            return event

        event_type = body.get("type", body.get("event", "unknown"))
        event_data = body.get("data", body)
        event_id = body.get("id", "")

        # 验证签名
        if not self.verify_signature(payload, signature):
            event = WebhookEvent(event_type, event_data)
            event.error = "Invalid signature"
            self._log_event(event_type, event_id, event_data, error="Invalid signature")
            return event

        # 创建事件
        event = WebhookEvent(event_type, event_data)

        # 记录事件
        self._log_event(event_type, event_id, event_data)

        # 分发到处理器
        handler = self._handlers.get(event_type)
        if handler:
            try:
                handler(event)
                event.processed = True
                self._mark_processed(event_id)
            except Exception as e:
                event.error = str(e)
                self._mark_error(event_id, str(e))
        else:
            # 默认处理：更新支付状态
            self._default_handler(event)

        return event

    def _default_handler(self, event: WebhookEvent):
        """默认事件处理器 - 自动更新支付状态"""
        state_map = {
            EVENT_TRANSFER_COMPLETED: "confirmed",
            EVENT_TRANSFER_FAILED: "failed",
            EVENT_PAYMENT_CONFIRMED: "confirmed",
            EVENT_PAYMENT_FAILED: "failed",
        }

        new_status = state_map.get(event.event_type)
        if not new_status:
            event.processed = True
            return

        tx_hash = event.data.get("txHash") or event.data.get("transactionHash")
        if tx_hash:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE payments SET status = ?, confirmed_at = CURRENT_TIMESTAMP WHERE transaction_hash = ?",
                (new_status, tx_hash)
            )
            conn.commit()
            conn.close()
            event.processed = True

    def _log_event(self, event_type: str, event_id: str, data: dict, error: str = None):
        """记录事件到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO webhook_events (event_type, event_id, data, error)
                VALUES (?, ?, ?, ?)
            ''', (event_type, event_id or "no_id", json.dumps(data), error))
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # 重复事件，忽略
        finally:
            conn.close()

    def _mark_processed(self, event_id: str):
        """标记事件已处理"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE webhook_events SET processed = 1, processed_at = CURRENT_TIMESTAMP WHERE event_id = ?",
            (event_id,)
        )
        conn.commit()
        conn.close()

    def _mark_error(self, event_id: str, error: str):
        """标记事件处理失败"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE webhook_events SET error = ? WHERE event_id = ?",
            (error, event_id)
        )
        conn.commit()
        conn.close()

    def get_event_log(self, limit: int = 50) -> list:
        """获取事件日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM webhook_events ORDER BY received_at DESC LIMIT ?",
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [{
            "id": r[0],
            "event_type": r[1],
            "event_id": r[2],
            "data": r[3],
            "processed": bool(r[4]),
            "error": r[5],
            "received_at": r[6],
            "processed_at": r[7]
        } for r in rows]
