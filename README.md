# Arc Micropayment Receipt System

A high-frequency micropayment solution for the AI Agent era, built on [Arc](https://arc.network) — Circle's stablecoin-native L1 blockchain.

## Problem

AI agents need to make thousands of micro-transactions ($0.001–$1.00), but existing blockchains make this impractical:

| Issue | Ethereum | Arc |
|-------|----------|-----|
| Transaction fee | ~$2-50 | ~$0.01 |
| Confirmation time | 12+ seconds | <1 second |
| Gas token | ETH (volatile) | USDC (stable) |

**Arc changes the economics**: sub-second finality + ~$0.01 fees paid in USDC make micro-payments viable for the first time.

## Use Cases

- **AI Agent billing** — $0.01 per query, $0.05 per task
- **Content tipping** — micro-rewards for articles, code, videos
- **Pay-per-API-call** — no subscriptions, pay what you use
- **In-game purchases** — $0.01 skins, items, upgrades

## Architecture

```
arc-micropayments/
├── app.py                      # Flask application with REST API
├── circle_wallet_service.py    # Circle SDK integration layer
├── nanopayments.py             # High-frequency batched micro-fills (Circle Nanopayments)
├── payment_links.py            # Shareable USDC payment links
├── webhook_handler.py          # Inbound webhook signature verification + event dispatch
├── models.py                   # SQLite database models
├── init_db.py                  # Database initialization
├── config.example.py           # Configuration template
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker support
├── docker-compose.yml          # Docker Compose setup
├── static/
│   └── style.css               # Responsive CSS styles
├── templates/
│   ├── index.html              # Dashboard with stats
│   ├── payment.html            # Payment form
│   ├── receipt.html            # Transaction receipt
│   └── wallets.html            # Wallet management
├── tests/
│   ├── __init__.py
│   ├── test_models.py          # Database model tests
│   ├── test_circle_service.py  # Wallet service tests
│   └── test_api.py             # API endpoint tests
└── .github/workflows/
    └── test.yml                # CI/CD with GitHub Actions
```

## Quick Start

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure (optional — runs in simulation mode without API keys)
cp .env.example .env
# Edit .env with your Circle API credentials

# 3. Initialize database
python init_db.py

# 4. Run
python app.py
```

Visit http://localhost:5000

### Docker

```bash
docker compose up -d
```

### Testing

```bash
pip install pytest
pytest tests/ -v
```

## API Reference

### Payments

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/payment` | Create a new payment |
| `GET` | `/api/payment/:id` | Get payment details |
| `GET` | `/api/payments/recent?limit=20` | List recent payments |
| `GET` | `/api/address/:address` | Get payments by address |
| `GET` | `/api/stats` | Payment statistics |

### Wallets

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/wallet/create` | Create Arc wallet |
| `GET` | `/api/wallet/:id/balance` | Check wallet balance |
| `GET` | `/api/wallet/list` | List all wallets |

### Example: Create Payment

```bash
curl -X POST http://localhost:5000/api/payment \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "0x1111111111111111111111111111111111111111",
    "receiver": "0x2222222222222222222222222222222222222222",
    "amount": 0.05,
    "description": "AI Agent query fee"
  }'
```

Response:
```json
{
  "success": true,
  "payment_id": 1,
  "transaction_hash": "0xabc123...",
  "status": "confirmed"
}
```

## Circle SDK Integration

This project integrates [Circle Developer Controlled Wallets](https://developers.circle.com/wallets/dev-controlled) on Arc:

- **Wallet Sets** — Group wallets by application or user
- **Wallets** — EOA accounts on ARC-TESTNET
- **Transfers** — USDC transfers with ~$0.01 fees
- **Simulation Mode** — Works without API keys for development

### Getting Circle API Keys

1. Register at [console.circle.com](https://console.circle.com)
2. Create an API Key (Standard Key)
3. Generate an Entity Secret
4. Add to `.env` file

## Tech Stack

- **Backend**: Python 3.10+ / Flask
- **Database**: SQLite
- **Blockchain**: Arc Testnet (Circle L1)
- **Payments**: USDC via Circle SDK
- **Frontend**: Vanilla HTML/CSS/JS
- **Testing**: pytest
- **CI/CD**: GitHub Actions
- **Deployment**: Docker

## Roadmap

- [x] Project initialization
- [x] Flask application framework
- [x] SQLite payment records
- [x] Circle SDK integration
- [x] Wallet management API
- [x] USDC transfer (simulation mode)
- [x] Unit tests
- [x] Dashboard with statistics
- [x] Docker support
- [x] GitHub Actions CI/CD
- [ ] Mainnet deployment
- [ ] Nanopayments integration
- [ ] Webhook event handling
- [ ] Multi-currency (USDC + EURC)

## License

MIT License

## Author

Sicheng Zhang — Web3 Developer

## Acknowledgments

- [Circle](https://circle.com) / [Arc](https://arc.network) — Infrastructure
- [arc-commerce](https://github.com/circlefin/arc-commerce) — Reference implementation
- [arc-nanopayments](https://github.com/circlefin/arc-nanopayments) — Nanopayment patterns
