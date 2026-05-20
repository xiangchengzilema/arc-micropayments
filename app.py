"""
Arc小额支付收据系统 - 主应用文件
集成Circle SDK实现Arc链上的USDC微支付
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import PaymentRecord
from circle_wallet_service import CircleWalletService
from webhook_handler import WebhookHandler
from nanopayments import NanopaymentBatch
from payment_links import PaymentLinkManager
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# 初始化数据库
db = PaymentRecord(os.getenv('DATABASE_PATH', 'payments.db'))

# 初始化Circle钱包服务
wallet_service = CircleWalletService()

# 初始化Webhook处理器
webhook_handler = WebhookHandler(
    db_path=os.getenv('DATABASE_PATH', 'payments.db'),
    webhook_secret=os.getenv('CIRCLE_WEBHOOK_SECRET', '')
)

# 初始化纳米支付
nanopayments = NanopaymentBatch(os.getenv('DATABASE_PATH', 'payments.db'))

# 初始化支付链接
payment_links = PaymentLinkManager(
    db_path=os.getenv('DATABASE_PATH', 'payments.db'),
    base_url=os.getenv('BASE_URL', 'http://localhost:5000')
)


# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页 - 显示支付列表和仪表板"""
    payments = db.get_all_payments(limit=50)
    stats = db.get_stats()
    return render_template('index.html', payments=payments, stats=stats)


@app.route('/payment/new')
def new_payment():
    """创建新支付页面"""
    wallets = wallet_service.list_wallets()
    return render_template('payment.html', wallets=wallets)


@app.route('/payment/<int:payment_id>')
def payment_receipt(payment_id):
    """支付收据页面"""
    payment = db.get_payment(payment_id)
    if not payment:
        return redirect(url_for('index'))
    return render_template('receipt.html', payment=payment)


@app.route('/wallets')
def wallets_page():
    """钱包管理页面"""
    wallets = wallet_service.list_wallets()
    return render_template('wallets.html', wallets=wallets)


# ==================== 钱包API ====================

@app.route('/api/wallet/create', methods=['POST'])
def api_create_wallet():
    """API: 创建新钱包"""
    try:
        wallet_set_id = wallet_service.get_or_create_wallet_set()
        wallet = wallet_service.create_wallet(wallet_set_id)
        return jsonify({'success': True, 'wallet': wallet})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/wallet/<wallet_id>/balance', methods=['GET'])
def api_wallet_balance(wallet_id):
    """API: 查询钱包余额"""
    try:
        balance = wallet_service.get_wallet_balance(wallet_id)
        return jsonify({'success': True, 'balance': balance})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/wallet/list', methods=['GET'])
def api_list_wallets():
    """API: 列出所有钱包"""
    try:
        wallets = wallet_service.list_wallets()
        return jsonify({'success': True, 'wallets': wallets})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 支付API ====================

@app.route('/api/payment', methods=['POST'])
def create_payment():
    """API: 创建USDC支付"""
    data = request.get_json(silent=True)

    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    sender = data.get('sender', '')
    receiver = data.get('receiver', '')
    amount = data.get('amount', 0)
    description = data.get('description', '')
    wallet_id = data.get('wallet_id', '')

    # 验证输入
    if not receiver:
        return jsonify({'success': False, 'error': 'Receiver address required'}), 400
    if not CircleWalletService.validate_address(receiver):
        return jsonify({'success': False, 'error': 'Invalid receiver address'}), 400
    if float(amount) <= 0:
        return jsonify({'success': False, 'error': 'Amount must be positive'}), 400

    try:
        # 如果有wallet_id，执行真实转账
        if wallet_id and wallet_service.is_configured:
            tx_result = wallet_service.send_usdc(
                from_wallet_id=wallet_id,
                to_address=receiver,
                amount=str(amount)
            )
            transaction_hash = tx_result.get('tx_hash', 'pending')
            status = 'confirmed' if tx_result.get('state') == 'COMPLETE' else 'pending'
        else:
            # 模拟模式
            transaction_hash = 'sim_' + str(hash(f"{sender}{receiver}{amount}"))
            status = 'confirmed'

        # 保存支付记录
        payment_id = db.create_payment(
            transaction_hash=transaction_hash,
            sender_address=sender or '0x0000000000000000000000000000000000000000',
            receiver_address=receiver,
            amount_usdc=float(amount),
            description=description
        )

        # 如果是pending状态，更新状态
        if status == 'confirmed':
            db.update_status(transaction_hash, 'confirmed')

        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'transaction_hash': transaction_hash,
            'status': status
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/payment/<int:payment_id>')
def get_payment(payment_id):
    """API: 获取支付详情"""
    payment = db.get_payment(payment_id)
    if payment:
        return jsonify({'success': True, 'payment': payment})
    return jsonify({'success': False, 'error': 'Payment not found'}), 404


@app.route('/api/payments/recent')
def recent_payments():
    """API: 获取最近的支付记录"""
    limit = request.args.get('limit', 20, type=int)
    payments = db.get_all_payments(limit=limit)
    return jsonify({'success': True, 'payments': payments})


# ==================== 地址查询API ====================

@app.route('/api/address/<address>')
def address_payments(address):
    """API: 获取地址的支付记录"""
    payments = db.get_payments_by_address(address)
    return jsonify({'success': True, 'payments': payments})


# ==================== 统计API ====================

@app.route('/api/stats')
def api_stats():
    """API: 获取支付统计"""
    stats = db.get_stats()
    np_stats = nanopayments.get_batch_stats()
    link_stats = payment_links.get_link_stats()
    return jsonify({
        'success': True,
        'stats': stats,
        'nanopayments': np_stats,
        'payment_links': link_stats
    })


# ==================== Webhook API ====================

@app.route('/api/webhook/circle', methods=['POST'])
def circle_webhook():
    """Circle Webhook回调端点"""
    signature = request.headers.get('Circle-Signature', '')
    payload = request.get_data()

    try:
        event = webhook_handler.handle(payload, signature)
    except Exception as e:
        # Always return JSON to Circle's webhook delivery system, never HTML.
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': event.processed, 'event_type': event.event_type})


@app.route('/api/webhook/events')
def webhook_events():
    """API: 获取Webhook事件日志"""
    limit = request.args.get('limit', 50, type=int)
    events = webhook_handler.get_event_log(limit)
    return jsonify({'success': True, 'events': events})


# ==================== Nanopayments API ====================

@app.route('/api/nanopayment/batch', methods=['POST'])
def create_nanopayment_batch():
    """API: 创建纳米支付批次"""
    data = request.get_json()
    if not data or 'payments' not in data:
        return jsonify({'success': False, 'error': 'payments array required'}), 400

    try:
        batch_id = nanopayments.create_batch(
            payments=data['payments'],
            reference=data.get('reference', '')
        )
        return jsonify({'success': True, 'batch_id': batch_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/nanopayment/batch/<batch_id>/execute', methods=['POST'])
def execute_nanopayment_batch(batch_id):
    """API: 执行纳米支付批次"""
    try:
        result = nanopayments.execute_batch(batch_id, wallet_service)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/nanopayment/batch/<batch_id>')
def get_nanopayment_batch(batch_id):
    """API: 获取批次详情"""
    batch = nanopayments.get_batch(batch_id)
    if batch:
        return jsonify({'success': True, 'batch': batch})
    return jsonify({'success': False, 'error': 'Batch not found'}), 404


@app.route('/api/nanopayment/batches')
def list_nanopayment_batches():
    """API: 列出所有批次"""
    limit = request.args.get('limit', 20, type=int)
    batches = nanopayments.list_batches(limit)
    return jsonify({'success': True, 'batches': batches})


# ==================== Payment Links API ====================

@app.route('/api/link/create', methods=['POST'])
def create_payment_link():
    """API: 创建支付链接"""
    data = request.get_json()
    if not data or 'receiver_address' not in data:
        return jsonify({'success': False, 'error': 'receiver_address required'}), 400

    try:
        link = payment_links.create_link(
            receiver_address=data['receiver_address'],
            amount_usdc=data.get('amount_usdc'),
            description=data.get('description', ''),
            max_uses=data.get('max_uses', 1),
            expires_hours=data.get('expires_hours', 72),
            creator_address=data.get('creator_address', '')
        )
        return jsonify({'success': True, 'link': link})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/pay/<link_code>')
def pay_link(link_code):
    """支付链接页面"""
    link = payment_links.get_link(link_code)
    if not link:
        return redirect(url_for('index'))
    return render_template('pay_link.html', link=link)


@app.route('/api/link/<link_code>/pay', methods=['POST'])
def use_payment_link(link_code):
    """API: 使用支付链接"""
    data = request.get_json()
    result = payment_links.use_link(
        link_code=link_code,
        sender_address=data.get('sender', ''),
        amount=data.get('amount')
    )
    return jsonify(result)


@app.route('/api/link/<link_code>/deactivate', methods=['POST'])
def deactivate_payment_link(link_code):
    """API: 停用支付链接"""
    success = payment_links.deactivate_link(link_code)
    return jsonify({'success': success})


@app.route('/api/links')
def list_payment_links():
    """API: 列出支付链接"""
    status = request.args.get('status')
    limit = request.args.get('limit', 20, type=int)
    links = payment_links.list_links(status, limit)
    return jsonify({'success': True, 'links': links})


# ==================== 启动 ====================

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    print()
    print("=" * 50)
    print("  Arc Micropayment Receipt System")
    print("=" * 50)
    print(f"  Circle SDK: {'Configured' if wallet_service.is_configured else 'Simulation Mode'}")
    print(f"  Arc Network: {os.getenv('ARC_BLOCKCHAIN', 'ARC-TESTNET')}")
    print(f"  USDC Token:  15dc2b5d-0994-58b0-bf8c-3a0501148ee8")
    print(f"  Listening:   http://localhost:{port}")
    print("=" * 50)
    print()

    app.run(host='0.0.0.0', port=port, debug=debug)
