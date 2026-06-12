# Binance Futures Testnet Trading Bot

A clean, structured Python CLI application for placing orders on the Binance USDT-M Futures Testnet.

---

## Features

- **Market orders** — immediate execution at best available price
- **Limit orders** — placed in the order book at a specific price
- **Stop-Market orders** (bonus) — triggers a market order when price hits a stop level
- Full **BUY / SELL** support
- Structured **logging** to rotating file + console
- Thorough **input validation** with clear error messages
- **Cancel orders** and **list open orders**
- **Account balance** view
- Optional `--json` flag to dump raw API responses

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # Binance REST API wrapper (auth, signing, requests)
│   ├── orders.py          # Order placement logic + OrderResult dataclass
│   ├── validators.py      # Input validation (raises ValueError on bad input)
│   └── logging_config.py  # Rotating file + console logging setup
├── logs/
│   ├── market_order_sample.log
│   └── limit_order_sample.log
├── cli.py                 # CLI entry point (argparse)
├── .env.example           # Credential template
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Register for Binance Futures Testnet

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in with your GitHub or Google account
3. Navigate to **API Key Management** → **Create API**
4. Copy your **API Key** and **Secret Key** (shown only once)

> The testnet gives you virtual USDT to trade with — no real funds involved.

### 2. Clone / download the project

```bash
git clone https://github.com/your-username/trading_bot.git
cd trading_bot
```

### 3. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure credentials

```bash
cp .env.example .env
```

Open `.env` and fill in your testnet keys:

```dotenv
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
LOG_LEVEL=INFO
```

---

## Running the Bot

All commands follow this pattern:

```
python cli.py [--log-level LEVEL] [--json] <command> [options]
```

### Place a Market Order

```bash
# Buy 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# Sell 0.01 ETH at market price
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --qty 0.01
```

### Place a Limit Order

```bash
# Sell 0.001 BTC at $110,000 (GTC — rests in book until filled or cancelled)
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 110000

# Buy 0.002 BTC at $95,000 with IOC (fill immediately or cancel)
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --qty 0.002 --price 95000 --tif IOC
```

### Place a Stop-Market Order (bonus)

```bash
# If price drops to $95,000, sell 0.001 BTC at market
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.001 --stop-price 95000
```

### List Open Orders

```bash
# All open orders
python cli.py orders

# Filtered by symbol
python cli.py orders --symbol BTCUSDT
```

### Cancel an Order

```bash
python cli.py cancel --symbol BTCUSDT --order-id 4003251234
```

### Check Account Balance

```bash
python cli.py account
```

### Debug Mode (verbose request/response logging)

```bash
python cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

### Print Raw JSON Response

```bash
python cli.py --json place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

---

## Sample Output

### Market Order (filled immediately)

```
──────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
──────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
──────────────────────────────────────────────────

✓  Order placed successfully
   Order ID      : 4003246890
   Symbol        : BTCUSDT
   Side          : BUY
   Type          : MARKET
   Status        : FILLED
   Quantity      : 0.001
   Executed Qty  : 0.001
   Avg Price     : 104823.50
```

### Limit Order (resting in book)

```
──────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
──────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : SELL
  Type       : LIMIT
  Quantity   : 0.001
  Price      : 110000.0
──────────────────────────────────────────────────

✓  Order placed successfully
   Order ID      : 4003251234
   Symbol        : BTCUSDT
   Side          : SELL
   Type          : LIMIT
   Status        : NEW
   Quantity      : 0.001
   Executed Qty  : 0.000
   Limit Price   : 110000.00
```

---

## Logging

Logs are written to `logs/trading_bot.log` (rotating, up to 5 × 5 MB).

Each entry includes timestamp, log level, module name, and message. The signature is redacted from logs for security.

Sample log files from real testnet sessions are in `logs/`:
- `market_order_sample.log` — MARKET BUY order (FILLED)
- `limit_order_sample.log` — LIMIT SELL order (NEW → CANCELED)

---

## Assumptions

- Uses the **USDT-M Futures Testnet** only (`https://testnet.binancefuture.com`)
- No real money is involved; testnet balances are virtual
- Quantity precision depends on the symbol — if the API rejects an order for precision, reduce decimal places (e.g. use `0.001` not `0.0013`)
- `STOP_MARKET` orders require the stop price to be on the correct side of the current market price (below market for SELL, above for BUY)
- Credentials are loaded from `.env` (never committed to git)

---

## Requirements

```
requests>=2.31.0
python-dotenv>=1.0.0
```

Python 3.9+ recommended.
