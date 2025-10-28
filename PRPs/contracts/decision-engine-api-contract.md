# API Contract: Decision Engine Service

**Version**: 1.0 | **Date**: 2025-10-27 | **Status**: Final

## Overview
Decision Engine integrates with LLM providers (DeepSeek primary, OpenRouter backup) to generate trading signals from market data.

## Service Interface

```python
class DecisionEngine:
    async def get_trading_decisions(
        self,
        market_data: Dict[str, MarketData],
        positions: List[Position]
    ) -> List[TradingSignal]:
        """Generate trading signals from market data"""
```

## Data Models

### TradingSignal

```python
class TradingSignal(BaseModel):
    symbol: str
    action: Literal['buy_to_enter', 'sell_to_enter', 'hold', 'close_position']
    confidence: float = Field(..., ge=0, le=1)
    risk_usd: float = Field(..., gt=0)
    leverage: int = Field(..., ge=5, le=40)
    stop_loss_pct: float = Field(..., ge=0.01, le=0.10)
    take_profit_pct: Optional[float] = Field(None, gt=0)
    reasoning: str
    model_used: str
    tokens_input: int
    tokens_output: int
    cost_usd: float
```

## LLM Integration

### DeepSeek API (Primary)
- **URL**: `https://api.deepseek.com/v1/chat/completions`
- **Model**: `deepseek-chat`
- **Cost**: $0.27/1M input, $1.10/1M output
- **Budget**: $12/month projected

### OpenRouter API (Backup)
- **URL**: `https://openrouter.ai/api/v1/chat/completions`
- **Model**: `qwen/qwen3-max`
- **Cost**: $1.20/1M input, $6.00/1M output
- **Budget**: $60/month maximum

### Request Format

```json
{
  "model": "deepseek-chat",
  "messages": [
    {"role": "system", "content": "SYSTEM_PROMPT"},
    {"role": "user", "content": "USER_PROMPT"}
  ],
  "temperature": 0.3,
  "max_tokens": 500,
  "response_format": {"type": "json_object"}
}
```

### Response Format

```json
{
  "signals": [
    {
      "symbol": "BTC/USDT",
      "action": "buy_to_enter",
      "confidence": 0.75,
      "risk_usd": 100,
      "leverage": 10,
      "stop_loss_pct": 0.02,
      "reasoning": "Bullish MACD crossover, RSI oversold"
    }
  ]
}
```

## Prompt Engineering

### System Prompt
```
You are a crypto trading agent. Analyze technical indicators and return JSON signals.
Output: {"signals": [{"symbol": "...", "action": "...", "confidence": 0-1, "risk_usd": 100, "leverage": 5-40, "stop_loss_pct": 0.01-0.10, "reasoning": "..."}]}
Rules: Confidence >0.6 for entries. Stop-loss 1-10%. Leverage 5-40x.
```

### User Prompt (Token-Optimized)
```
Market Data:
BTC/USDT: $50000 EMA20:49800 RSI:58 MACD:150 Vol:1.2x
ETH/USDT: $3000 EMA20:2980 RSI:45 MACD:-50 Vol:0.9x

Positions:
BTC/USDT long 0.002 @49500 PnL:+2.0%

Decide: buy_to_enter, sell_to_enter, hold, or close_position
```

## Performance Targets
- **Latency**: <1.2s (95th percentile)
- **Token Budget**: <1000 input, <500 output
- **Cost Per Call**: <$0.002
- **Retry Attempts**: 2 (primary), 2 (backup)

---

**Document Location**: `/Users/tobiprivat/Documents/GitProjects/personal/trader/PRPs/contracts/decision-engine-api-contract.md`
