# Binance Testnet Setup Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Create Testnet Account](#create-testnet-account)
3. [Generate API Keys](#generate-api-keys)
4. [Get Test Funds](#get-test-funds)
5. [Configure Environment](#configure-environment)
6. [Verify Setup](#verify-setup)
7. [Run Integration Tests](#run-integration-tests)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

Before starting, ensure you have:
- Python 3.10 or higher installed
- Git installed and repository cloned
- Active GitHub account (for Binance testnet OAuth)
- Internet connection for API access

## Create Testnet Account

### Step 1: Access Binance Testnet

1. Open your browser and navigate to [https://testnet.binance.vision/](https://testnet.binance.vision/)
2. You'll see the Binance Testnet homepage

### Step 2: Login with GitHub

1. Click the **"Log In with GitHub"** button
2. You'll be redirected to GitHub for authentication
3. Authorize the Binance Testnet application
4. You'll be redirected back to the testnet with your account created

> **Note**: Binance testnet uses GitHub OAuth for authentication. Your testnet account is linked to your GitHub account.

## Generate API Keys

### Step 1: Access API Management

1. After logging in, look for **"API Management"** in the menu
2. Click on it to open the API key management page

### Step 2: Create New API Key

1. Click **"Create API"** button
2. Give your API key a label (e.g., "Trading Bot Testnet")
3. Complete any 2FA verification if prompted

### Step 3: Save Your Credentials

⚠️ **CRITICAL**: Save your credentials immediately!

1. **API Key**: A 64-character string (copy this)
2. **Secret Key**: Shown only once (copy and save securely)

Example format:
```
API Key: 7f3a2b5c8d9e1f4a6b8c3d5e7f9a1b3c5d7e9f1a3b5c7d9e1f3a5b7c9d1e3f5a
Secret: YourSecretKeyHereShownOnlyOnce
```

### Step 4: Configure API Restrictions (Optional)

For additional security:
1. Enable **"Restrict access to trusted IPs only"** if you have a static IP
2. Set appropriate permissions (Enable Spot & Margin Trading)
3. Disable withdrawal permissions (not needed for testing)

## Get Test Funds

### Step 1: Access Faucet

1. In the testnet interface, find the **"Faucet"** option
2. Click to open the test funds distribution page

### Step 2: Request Test Funds

1. **USDT**: Click "Get 10,000 USDT" button
2. **BTC**: Click "Get 1 BTC" button (optional, for testing)
3. **ETH**: Click "Get 100 ETH" button (optional)

### Step 3: Verify Balances

1. Go to **"Wallet"** → **"Spot Wallet"**
2. Verify you received the test funds:
   - USDT: 10,000
   - BTC: 1 (if requested)
   - ETH: 100 (if requested)

## Configure Environment

### Step 1: Copy Configuration Template

```bash
# From the repository root
cp .env.testnet.example .env.testnet
```

### Step 2: Edit Configuration File

Open `.env.testnet` in your favorite editor:

```bash
# Using nano
nano .env.testnet

# Or using VS Code
code .env.testnet
```

### Step 3: Add Your API Credentials

Replace the placeholder values with your actual credentials:

```bash
# Binance Testnet Configuration
BINANCE_API_KEY=your_actual_64_character_api_key_here
BINANCE_API_SECRET=your_actual_secret_key_here
BINANCE_TESTNET=true
```

### Step 4: Save and Secure

1. Save the file
2. Ensure it's not tracked by git:
```bash
# Verify .env.testnet is in .gitignore
grep ".env.testnet" .gitignore

# If not, add it
echo ".env.testnet" >> .gitignore
```

## Verify Setup

### Step 1: Load Environment Variables

```bash
# Export environment variables
export $(cat .env.testnet | grep -v '^#' | xargs)

# Or use source
source .env.testnet
```

### Step 2: Run Verification Script

```python
# Create a quick verification script
cat > verify_testnet.py << 'EOF'
import os
import asyncio
from workspace.features.testnet_integration import TestnetConfig, TestnetExchangeAdapter, ExchangeType

async def verify():
    try:
        # Load configuration
        config = TestnetConfig.from_env(ExchangeType.BINANCE)
        print(f"✅ Configuration loaded")
        print(f"   Exchange: {config.exchange.value}")
        print(f"   Mode: {config.mode.value}")

        # Validate configuration
        config.validate()
        print(f"✅ Configuration validated")

        # Initialize adapter
        adapter = TestnetExchangeAdapter(config)
        await adapter.initialize()
        print(f"✅ Connected to {config.exchange.value} testnet")

        # Get balance
        balance = await adapter.get_balance()
        print(f"✅ Balance fetched successfully")

        # Show USDT balance
        if 'USDT' in balance['total']:
            print(f"   USDT Balance: {balance['total']['USDT']}")

        await adapter.close()
        print(f"✅ Setup verification complete!")

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(verify())
    exit(0 if success else 1)
EOF

# Run verification
python verify_testnet.py
```

Expected output:
```
✅ Configuration loaded
   Exchange: binance
   Mode: testnet
✅ Configuration validated
✅ Connected to binance testnet
✅ Balance fetched successfully
   USDT Balance: 10000.0
✅ Setup verification complete!
```

## Run Integration Tests

### Step 1: Run All Tests

```bash
# Run all testnet integration tests
pytest workspace/tests/integration/testnet/ -v

# With coverage report
pytest workspace/tests/integration/testnet/ \
    --cov=workspace.features.testnet_integration \
    --cov-report=html \
    --cov-report=term
```

### Step 2: Run Specific Test Categories

```bash
# Connection tests only
pytest workspace/tests/integration/testnet/test_connection.py -v

# Order execution tests
pytest workspace/tests/integration/testnet/test_orders.py -v

# WebSocket tests
pytest workspace/tests/integration/testnet/test_websocket.py -v
```

### Step 3: Run with Real Testnet (Slow Tests)

```bash
# Run tests that actually connect to testnet (slower)
pytest workspace/tests/integration/testnet/ -v -m "not mock"

# Run only mock tests (faster, no network)
pytest workspace/tests/integration/testnet/ -v -m "mock"
```

## Troubleshooting

### Issue: "Invalid API Key" Error

**Symptoms**:
```
ccxt.base.errors.AuthenticationError: binance {"code":-2014,"msg":"API-key format invalid."}
```

**Solutions**:
1. Verify API key is exactly 64 characters
2. Check for extra spaces or newlines in .env.testnet
3. Ensure you're using testnet keys, not production
4. Verify BINANCE_TESTNET=true is set

### Issue: "Insufficient Balance" Error

**Symptoms**:
```
ccxt.base.errors.InsufficientFunds: binance {"code":-2010,"msg":"Account has insufficient balance for requested action."}
```

**Solutions**:
1. Use the testnet faucet to get more test funds
2. Check your balance: Go to testnet.binance.vision → Wallet
3. Reduce order amounts in tests (use 0.001 BTC minimum)
4. Wait for previous orders to complete

### Issue: Connection Timeout

**Symptoms**:
```
asyncio.exceptions.TimeoutError
```

**Solutions**:
1. Check your internet connection
2. Testnet may be experiencing high load - try again later
3. Increase timeout in configuration:
   ```bash
   BINANCE_TIMEOUT_MS=60000  # Increase to 60 seconds
   ```

### Issue: "Test" Attribute Error

**Symptoms**:
```
AttributeError: 'binance' object has no attribute 'set_sandbox_mode'
```

**Solutions**:
1. Update ccxt to latest version:
   ```bash
   pip install --upgrade ccxt
   ```
2. Verify ccxt version:
   ```python
   import ccxt
   print(ccxt.__version__)  # Should be 4.0.0 or higher
   ```

### Issue: Rate Limiting

**Symptoms**:
```
ccxt.base.errors.RateLimitExceeded: binance {"code":-1003,"msg":"Way too many requests"}
```

**Solutions**:
1. Add delays between requests
2. Increase rate limit buffer:
   ```bash
   BINANCE_RATE_LIMIT_MS=500  # Increase buffer
   ```
3. Reduce parallel test execution

### Issue: WebSocket Connection Failed

**Symptoms**:
```
websockets.exceptions.ConnectionClosed: no close frame received or sent
```

**Solutions**:
1. Check WebSocket URL is correct for testnet
2. Verify firewall allows WebSocket connections
3. Try with a different network
4. Check if testnet WebSocket service is operational

## Best Practices

### Security
- Never commit .env.testnet with real keys
- Use separate API keys for different environments
- Regularly rotate API keys
- Monitor API key usage on testnet dashboard

### Testing
- Start with small order amounts (0.001 BTC)
- Use limit orders with prices far from market to avoid fills
- Cancel orders after tests to clean up
- Monitor your testnet balance

### Development
- Use mock adapters for unit tests
- Only use real testnet for integration tests
- Implement proper retry logic for network issues
- Log all testnet interactions for debugging

## Additional Resources

- [Binance Testnet Documentation](https://testnet.binance.vision/)
- [ccxt Documentation](https://docs.ccxt.com/)
- [Binance API Documentation](https://binance-docs.github.io/apidocs/)
- [Project README](../../README.md)

## Support

If you encounter issues not covered here:
1. Check the [FAQ](./FAQ.md)
2. Review [test logs](../../logs/)
3. Open an issue on GitHub
4. Contact the development team

---

**Last Updated**: 2025-10-31
**Author**: Documentation Curator
