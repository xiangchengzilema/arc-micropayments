# Arc小额支付收据系统

## 简介
为AI Agent时代设计的高频小额支付解决方案，利用Arc的~$0.01手续费实现亚秒级确认的微支付。

## 解决痛点
- **以太坊gas费太高** - 无法做几分钱的小额支付
- **没有统一的支付记录** - 用户和开发者都难以追踪
- **AI Agent按使用量计费困难** - 缺乏灵活的微支付基础设施

## 为什么选择Arc

| Arc特点 | 项目价值 |
|---------|---------|
| ~$0.01手续费 | 使几分钱的支付成为可能 |
| 亚秒级确认 | 用户体验流畅，无需等待 |
| USDC原生 | 不需要买gas，用户友好 |
| Paymaster | 交易费用也用USDC支付 |

## 落地应用场景
1. **AI Agent按使用量计费** - 每回答一个问题 $0.01
2. **内容微打赏** - 文章/代码/视频按喜好支付几分钱
3. **API按次调用** - 不用包月，用多少付多少
4. **游戏内小额购买** - 道具/皮肤几分钱

## 技术架构
- **后端**: Python Flask
- **数据库**: SQLite (简单可靠)
- **区块链**: Circle Developer Controlled Wallets
- **前端**: 简单HTML + JavaScript

## 项目结构
```
arc-micropayments/
├── app.py              # Flask应用主文件
├── requirements.txt    # Python依赖
├── config.py          # 配置文件
├── models.py          # 数据库模型
├── static/            # 静态文件
│   └── style.css
├── templates/         # HTML模板
│   ├── index.html
│   └── payment.html
└── README.md         # 本文件
```

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
复制 `config.example.py` 为 `config.py` 并填入你的Circle API密钥：
```python
CIRCLE_API_KEY = "your_api_key_here"
CIRCLE_ENTITY_SECRET = "your_entity_secret_here"
```

### 3. 初始化数据库
```bash
python init_db.py
```

### 4. 启动服务
```bash
python app.py
```

访问 http://localhost:5000

## 核心功能

### 支付流程
1. 用户创建钱包 (Circle Developer Controlled Wallets)
2. 用户充值USDC到钱包地址
3. 发起小额支付请求
4. 系统在Arc链上执行交易
5. 记录交易信息到数据库
6. 展示支付收据

### 收据系统
- 交易哈希
- 发送方/接收方地址
- 支付金额 (USDC)
- 时间戳
- 交易状态

## 项目进展
- [x] 项目初始化
- [x] 基础Flask应用框架
- [ ] Circle SDK集成
- [ ] 支付功能实现
- [ ] 收据系统实现
- [ ] Web界面完善

## 参考资源
- [Arc官方文档](https://docs.arc.network)
- [Circle Developer Wallets](https://developers.circle.com/wallets/dev-controlled)
- [arc-commerce sample](https://github.com/circlefin/arc-commerce)

## License
MIT License

## 作者
Sicheng Zhang - Web3 Developer

## 致谢
- Circle/Arc团队提供的优秀基础设施
- arc-commerce sample项目的参考
