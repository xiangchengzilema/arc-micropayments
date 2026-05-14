"""
初始化数据库 - 创建表结构
"""

from models import PaymentRecord

def main():
    print("初始化Arc小额支付数据库...")
    db = PaymentRecord("payments.db")
    print("[OK] 数据库初始化完成!")
    print(f"数据库文件: payments.db")
    print()
    print("现在可以运行: python app.py")

if __name__ == "__main__":
    main()
