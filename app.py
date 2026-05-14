"""
Arc小额支付收据系统 - 主应用文件
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from models import PaymentRecord
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

# 初始化数据库
db = PaymentRecord(os.getenv('DATABASE_PATH', 'payments.db'))

@app.route('/')
def index():
    """首页 - 显示支付列表"""
    payments = db.get_all_payments(limit=50)
    return render_template('index.html', payments=payments)

@app.route('/payment/new')
def new_payment():
    """创建新支付页面"""
    return render_template('payment.html')

@app.route('/api/payment', methods=['POST'])
def create_payment():
    """API: 创建支付"""
    data = request.get_json()

    # TODO: 这里需要集成Circle SDK进行实际支付
    # 目前是模拟实现

    transaction_hash = data.get('tx_hash', 'pending_' + str(hash(data)))
    sender = data.get('sender', '0x0000000000000000000000000000000000000000')
    receiver = data.get('receiver', '0x3600000000000000000000000000000000000000')
    amount = float(data.get('amount', 0))
    description = data.get('description', '')

    payment_id = db.create_payment(
        transaction_hash=transaction_hash,
        sender_address=sender,
        receiver_address=receiver,
        amount_usdc=amount,
        description=description
    )

    return jsonify({
        'success': True,
        'payment_id': payment_id,
        'transaction_hash': transaction_hash
    })

@app.route('/api/payment/<int:payment_id>')
def get_payment(payment_id):
    """API: 获取支付详情"""
    payment = db.get_payment(payment_id)
    if payment:
        return jsonify({'success': True, 'payment': payment})
    return jsonify({'success': False, 'error': 'Payment not found'}), 404

@app.route('/payment/<int:payment_id>')
def payment_receipt(payment_id):
    """支付收据页面"""
    payment = db.get_payment(payment_id)
    if not payment:
        return redirect(url_for('index'))
    return render_template('receipt.html', payment=payment)

@app.route('/api/address/<address>')
def address_payments(address):
    """API: 获取地址的支付记录"""
    payments = db.get_payments_by_address(address)
    return jsonify({'success': True, 'payments': payments})

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
