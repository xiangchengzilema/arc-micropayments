"""
Circle钱包服务 - 管理Arc链上的Developer Controlled Wallets
集成Circle SDK实现USDC转账、钱包管理、余额查询
"""

import os
import json
import urllib.request
import urllib.error
import base64
from typing import Dict, List, Optional


# Arc Testnet配置
ARC_BLOCKCHAIN = "ARC-TESTNET"
ARC_USDC_TOKEN_ID = "15dc2b5d-0994-58b0-bf8c-3a0501148ee8"
CIRCLE_API_BASE = "https://api.circle.com/v1/w3s"


class CircleWalletService:
    """Circle钱包服务 - 管理Arc链上的钱包和支付"""

    def __init__(self, api_key: str = None, entity_secret: str = None):
        self.api_key = api_key or os.getenv("CIRCLE_API_KEY", "")
        self.entity_secret = entity_secret or os.getenv("CIRCLE_ENTITY_SECRET", "")

        if not self.api_key or not self.entity_secret:
            print("[WARN] Circle API Key或Entity Secret未配置")
            print("       请在.env文件中设置CIRCLE_API_KEY和CIRCLE_ENTITY_SECRET")
            print("       当前运行在模拟模式")

    @property
    def is_configured(self) -> bool:
        """检查是否已配置API密钥"""
        return bool(self.api_key and self.entity_secret)

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """发送API请求到Circle"""
        url = f"{CIRCLE_API_BASE}/{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        body = None
        if data:
            body = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            response = urllib.request.urlopen(req)
            return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise Exception(f"Circle API Error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise Exception(f"Network Error: {e.reason}")

    # ==================== Wallet Set 管理 ====================

    def get_or_create_wallet_set(self, name: str = "Arc Micropayments") -> str:
        """获取或创建钱包集，返回wallet_set_id"""
        if not self.is_configured:
            return "sim_wallet_set_001"

        # 先查询是否已存在
        try:
            response = self._make_request("GET", "walletSets")
            for ws in response.get("data", {}).get("walletSets", []):
                if ws.get("name") == name:
                    return ws["id"]
        except Exception:
            pass

        # 不存在则创建
        response = self._make_request("POST", "walletSets", {
            "name": name
        })
        return response["data"]["walletSet"]["id"]

    # ==================== 钱包管理 ====================

    def create_wallet(self, wallet_set_id: str = None) -> Dict:
        """在Arc Testnet上创建新钱包"""
        if not self.is_configured:
            # 模拟模式
            import hashlib
            import time
            mock_addr = "0x" + hashlib.sha256(str(time.time()).encode()).hexdigest()[:40]
            return {
                "id": f"sim_wallet_{int(time.time())}",
                "address": mock_addr,
                "blockchain": ARC_BLOCKCHAIN,
                "state": "LIVE",
                "balances": []
            }

        if not wallet_set_id:
            wallet_set_id = self.get_or_create_wallet_set()

        response = self._make_request("POST", "wallets", {
            "walletSetId": wallet_set_id,
            "blockchains": [ARC_BLOCKCHAIN],
            "count": 1,
            "accountType": "EOA"
        })

        wallet = response["data"]["wallets"][0]
        return {
            "id": wallet["id"],
            "address": wallet["address"],
            "blockchain": wallet["blockchain"],
            "state": wallet["state"],
            "balances": wallet.get("balances", [])
        }

    def get_wallet_balance(self, wallet_id: str) -> Dict:
        """查询钱包余额"""
        if not self.is_configured:
            return {
                "id": wallet_id,
                "balances": [
                    {"token": "USDC", "amount": "100.00"}
                ]
            }

        response = self._make_request("GET", f"wallets/{wallet_id}")
        wallet = response["data"]["wallet"]
        return {
            "id": wallet["id"],
            "address": wallet["address"],
            "balances": wallet.get("balances", [])
        }

    def list_wallets(self, wallet_set_id: str = None) -> List[Dict]:
        """列出所有钱包"""
        if not self.is_configured:
            return []

        params = {}
        if wallet_set_id:
            params["walletSetId"] = wallet_set_id

        endpoint = "wallets"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items())
            endpoint = f"wallets?{query}"

        response = self._make_request("GET", endpoint)
        wallets = []
        for w in response.get("data", {}).get("wallets", []):
            wallets.append({
                "id": w["id"],
                "address": w["address"],
                "blockchain": w["blockchain"],
                "state": w["state"]
            })
        return wallets

    # ==================== USDC转账 ====================

    def send_usdc(
        self,
        from_wallet_id: str,
        to_address: str,
        amount: str,
        token_id: str = None
    ) -> Dict:
        """发送USDC到指定地址"""
        token_id = token_id or ARC_USDC_TOKEN_ID

        if not self.is_configured:
            # 模拟模式
            import hashlib
            import time
            mock_hash = "0x" + hashlib.sha256(
                f"{from_wallet_id}{to_address}{amount}{time.time()}".encode()
            ).hexdigest()[:64]
            return {
                "id": f"sim_tx_{int(time.time())}",
                "state": "COMPLETE",
                "tx_hash": mock_hash,
                "amounts": [amount],
                "blockchain": ARC_BLOCKCHAIN
            }

        response = self._make_request("POST", "transactions/transfer", {
            "walletId": from_wallet_id,
            "tokenId": token_id,
            "destinationAddress": to_address,
            "amounts": [str(amount)],
            "feeLevel": "MEDIUM",
            "entitySecretCiphertext": self._get_entity_secret_ciphertext()
        })

        tx = response["data"]["transaction"]
        return {
            "id": tx["id"],
            "state": tx["state"],
            "tx_hash": tx.get("txHash", ""),
            "amounts": tx.get("amounts", []),
            "blockchain": tx.get("blockchain", ARC_BLOCKCHAIN)
        }

    def get_transaction_status(self, transaction_id: str) -> Optional[Dict]:
        """查询交易状态"""
        if not self.is_configured:
            return {
                "id": transaction_id,
                "state": "COMPLETE",
                "tx_hash": "0x_simulated"
            }

        try:
            response = self._make_request("GET", f"transactions/{transaction_id}")
            tx = response["data"]["transaction"]
            return {
                "id": tx["id"],
                "state": tx["state"],
                "tx_hash": tx.get("txHash", ""),
                "amounts": tx.get("amounts", []),
                "blockchain": tx.get("blockchain", "")
            }
        except Exception:
            return None

    def _get_entity_secret_ciphertext(self) -> str:
        """
        生成Entity Secret的加密密文
        使用Circle的RSA公钥加密entity secret
        """
        # 这里简化处理 - 实际生产环境需要使用Circle的公钥加密
        # SDK会自动处理这个过程
        return base64.b64encode(self.entity_secret.encode()).decode()

    # ==================== 工具方法 ====================

    @staticmethod
    def validate_address(address: str) -> bool:
        """验证以太坊地址格式"""
        if not address.startswith("0x"):
            return False
        if len(address) != 42:
            return False
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False

    @staticmethod
    def format_usdc_amount(amount: float) -> str:
        """格式化USDC金额（保留6位小数）"""
        return f"{amount:.6f}"
