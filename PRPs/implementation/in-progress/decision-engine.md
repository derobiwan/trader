# PRP: Decision Engine Implementation

## Metadata
- **PRP Type**: Implementation
- **Feature**: LLM-Powered Decision Engine
- **Priority**: Critical
- **Estimated Effort**: 26 story points
- **Dependencies**: Market Data Service, Database Setup
- **Target Directory**: workspace/features/decision_engine/

## Context

### Business Requirements
Implement an LLM-powered decision engine that analyzes market data every 3 minutes to generate trading signals with <1 second latency, using DeepSeek Chat V3.1 as primary model and Qwen3 Max as fallback, with comprehensive prompt engineering and response validation.

### Technical Context
- **Primary LLM**: DeepSeek Chat V3.1 ($12/month, ultra-fast)
- **Backup LLM**: Qwen3 Max ($60/month, more sophisticated)
- **Decision Latency**: <1000ms target
- **Response Format**: Structured JSON with validation
- **Token Budget**: ~2000 tokens per request
- **Cost Tracking**: Real-time token usage monitoring

### From API Contract
```yaml
# From PRPs/contracts/decision-engine-api-contract.md
POST /decision-engine/analyze
  - Market data input
  - Returns: trading signal with confidence
  - Latency: <1 second
  - Includes reasoning and risk assessment
```

## Implementation Requirements

### 1. LLM Client Abstraction

**File**: `workspace/features/decision_engine/llm_client.py`

```python
import asyncio
import httpx
import json
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime, UTC
from decimal import Decimal
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """Generate response from LLM."""
        pass

    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        pass

class DeepSeekProvider(LLMProvider):
    """
    DeepSeek Chat V3.1 provider implementation.
    Ultra-fast, cost-effective for high-frequency decisions.
    """

    API_URL = "https://api.deepseek.com/v1/chat/completions"
    MODEL = "deepseek-chat-v3.1"
    TIMEOUT = 5.0  # 5 second timeout

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.TIMEOUT),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        self.total_tokens_used = 0
        self.total_requests = 0

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Generate trading decision from DeepSeek.
        """
        start_time = datetime.now(UTC)

        try:
            # Prepare request
            request_data = {
                "model": self.MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert cryptocurrency trader analyzing market data. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"}
            }

            # Make request
            response = await self.client.post(
                self.API_URL,
                json=request_data
            )
            response.raise_for_status()

            # Parse response
            data = response.json()

            # Track usage
            usage = data.get('usage', {})
            tokens_used = usage.get('total_tokens', 0)
            self.total_tokens_used += tokens_used
            self.total_requests += 1

            # Calculate latency
            latency_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            # Extract content
            content = data['choices'][0]['message']['content']

            # Parse JSON response
            try:
                decision = json.loads(content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {content}")
                decision = {"error": "invalid_json", "raw": content}

            return {
                "decision": decision,
                "model": self.MODEL,
                "tokens_used": tokens_used,
                "latency_ms": latency_ms,
                "timestamp": start_time.isoformat()
            }

        except httpx.TimeoutException:
            logger.error("DeepSeek request timeout")
            return {
                "error": "timeout",
                "model": self.MODEL,
                "latency_ms": self.TIMEOUT * 1000
            }
        except Exception as e:
            logger.error(f"DeepSeek request failed: {e}")
            return {
                "error": str(e),
                "model": self.MODEL
            }

    async def count_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation).
        """
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // 4

class Qwen3MaxProvider(LLMProvider):
    """
    Qwen3 Max provider - more sophisticated backup model.
    """

    API_URL = "https://api.qwen.ai/v1/chat/completions"  # Example URL
    MODEL = "qwen3-max"
    TIMEOUT = 8.0  # Slightly longer timeout for more complex model

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.TIMEOUT),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        self.total_tokens_used = 0
        self.total_requests = 0

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1500
    ) -> Dict[str, Any]:
        """
        Generate sophisticated analysis from Qwen3 Max.
        """
        # Similar implementation to DeepSeek
        # but with Qwen3-specific parameters
        pass  # Implementation similar to DeepSeek

class LLMOrchestrator:
    """
    Orchestrates multiple LLM providers with failover.
    """

    def __init__(self, config: Dict[str, Any]):
        self.providers = {
            'deepseek': DeepSeekProvider(config['deepseek_api_key']),
            'qwen3': Qwen3MaxProvider(config['qwen3_api_key'])
        }
        self.primary_provider = 'deepseek'
        self.fallback_provider = 'qwen3'
        self.max_retries = 3

    async def generate_decision(
        self,
        prompt: str,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Generate decision with automatic failover.
        """
        # Try primary provider
        primary = self.providers[self.primary_provider]
        result = await primary.generate(prompt)

        if 'error' not in result:
            return result

        # Failover to backup if enabled
        if use_fallback:
            logger.warning(f"Primary LLM failed, falling back to {self.fallback_provider}")
            backup = self.providers[self.fallback_provider]
            result = await backup.generate(prompt, max_tokens=1500)

        return result

    def get_token_usage_stats(self) -> Dict[str, Any]:
        """
        Get token usage statistics for cost tracking.
        """
        stats = {}
        for name, provider in self.providers.items():
            stats[name] = {
                'total_tokens': provider.total_tokens_used,
                'total_requests': provider.total_requests,
                'avg_tokens_per_request': (
                    provider.total_tokens_used / provider.total_requests
                    if provider.total_requests > 0 else 0
                )
            }
        return stats
```

### 2. Prompt Engineering System

**File**: `workspace/features/decision_engine/prompts.py`

```python
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

class PromptTemplates:
    """
    Manages prompt templates for different market conditions.
    """

    MARKET_ANALYSIS_PROMPT = """
Analyze the following cryptocurrency market data and provide a trading decision.

CURRENT MARKET DATA:
Symbol: {symbol}
Current Price: ${current_price}
24h Change: {price_change_24h}%
24h Volume: ${volume_24h}

TECHNICAL INDICATORS:
- RSI(14): {rsi_14}
- MACD: {macd} (Signal: {macd_signal})
- SMA(20): ${sma_20}
- SMA(50): ${sma_50}
- Bollinger Bands: Upper=${bb_upper}, Lower=${bb_lower}
- ATR(14): ${atr_14}
- Volume Ratio: {volume_ratio}x

CURRENT POSITIONS:
{positions}

RISK PARAMETERS:
- Daily Loss Limit: -7% (CHF {daily_loss_limit})
- Current Daily P&L: CHF {current_pnl}
- Max Position Size: {max_position_size} units
- Available Capital: CHF {available_capital}

Provide your analysis in the following JSON format:
{{
    "signal": "entry_long" | "entry_short" | "exit" | "hold",
    "confidence": 0.0-1.0,
    "recommended_size": position size in units,
    "recommended_leverage": 1-10,
    "stop_loss_price": price level,
    "take_profit_price": price level,
    "reasoning": "detailed explanation",
    "risk_assessment": {{
        "risk_score": 0.0-1.0,
        "max_drawdown_expected": percentage,
        "key_risks": ["risk1", "risk2"]
    }},
    "market_sentiment": "bullish" | "bearish" | "neutral",
    "timeframe_validity": "minutes until signal expires"
}}

Consider:
1. Technical indicator alignment
2. Risk/reward ratio (minimum 1:2)
3. Current market volatility
4. Position sizing relative to account
5. Stop-loss placement for capital preservation
"""

    TREND_ANALYSIS_PROMPT = """
Analyze the trend strength and direction for {symbol}.

PRICE ACTION (last 20 candles):
{price_action}

MOVING AVERAGES:
- SMA(20): ${sma_20} ({sma_20_direction})
- SMA(50): ${sma_50} ({sma_50_direction})
- EMA(12): ${ema_12}
- EMA(26): ${ema_26}

TREND INDICATORS:
- ADX: {adx} ({trend_strength})
- MACD Histogram: {macd_histogram}
- Price vs SMA(20): {price_vs_sma20}%
- Price vs SMA(50): {price_vs_sma50}%

Determine:
1. Primary trend (up/down/sideways)
2. Trend strength (weak/moderate/strong)
3. Potential reversal signals
4. Support/resistance levels
"""

    RISK_ASSESSMENT_PROMPT = """
Evaluate the risk for a {side} position in {symbol}.

POSITION DETAILS:
- Entry Price: ${entry_price}
- Position Size: {position_size}
- Leverage: {leverage}x
- Current Price: ${current_price}

MARKET CONDITIONS:
- Volatility (ATR): ${atr_14} ({volatility_percent}%)
- 24h High/Low: ${high_24h} / ${low_24h}
- Volume: {volume_status}
- Order Book Imbalance: {orderbook_imbalance}%

ACCOUNT STATUS:
- Current Exposure: {current_exposure}%
- Daily P&L: {daily_pnl}%
- Win Rate: {win_rate}%
- Average Loss: {avg_loss}%

Assess:
1. Probability of stop-loss hit
2. Maximum expected drawdown
3. Risk/reward ratio
4. Position sizing appropriateness
5. Correlation risk with other positions
"""

    @staticmethod
    def build_market_analysis_prompt(
        symbol: str,
        market_data: Dict[str, Any],
        positions: List[Dict[str, Any]],
        risk_params: Dict[str, Any]
    ) -> str:
        """
        Build a complete market analysis prompt.
        """
        # Format positions
        if positions:
            positions_str = "\n".join([
                f"- {p['symbol']}: {p['side']} {p['quantity']} @ ${p['entry_price']} "
                f"(P&L: {p['unrealized_pnl']})"
                for p in positions
            ])
        else:
            positions_str = "No open positions"

        # Extract indicators
        indicators = market_data.get('indicators', {})

        # Build prompt
        prompt = PromptTemplates.MARKET_ANALYSIS_PROMPT.format(
            symbol=symbol,
            current_price=market_data['close'],
            price_change_24h=market_data.get('price_change_percent', 0),
            volume_24h=market_data.get('volume_24h', 0),
            rsi_14=indicators.get('rsi_14', 50),
            macd=indicators.get('macd', 0),
            macd_signal=indicators.get('macd_signal', 0),
            sma_20=indicators.get('sma_20', market_data['close']),
            sma_50=indicators.get('sma_50', market_data['close']),
            bb_upper=indicators.get('bb_upper', 0),
            bb_lower=indicators.get('bb_lower', 0),
            atr_14=indicators.get('atr_14', 0),
            volume_ratio=indicators.get('volume_ratio', 1.0),
            positions=positions_str,
            daily_loss_limit=risk_params['daily_loss_limit'],
            current_pnl=risk_params['current_pnl'],
            max_position_size=risk_params['max_position_size'],
            available_capital=risk_params['available_capital']
        )

        return prompt

    @staticmethod
    def build_multi_asset_prompt(
        market_data: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> str:
        """
        Build prompt for multi-asset portfolio decisions.
        """
        # Implementation for portfolio-wide analysis
        pass
```

### 3. Response Validation

**File**: `workspace/features/decision_engine/validator.py`

```python
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class TradingSignal(BaseModel):
    """
    Validated trading signal model.
    """
    signal: str = Field(..., regex="^(entry_long|entry_short|exit|hold)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommended_size: float = Field(..., gt=0)
    recommended_leverage: int = Field(..., ge=1, le=10)
    stop_loss_price: float = Field(..., gt=0)
    take_profit_price: float = Field(..., gt=0)
    reasoning: str = Field(..., min_length=10)
    risk_assessment: Dict[str, Any]
    market_sentiment: str = Field(..., regex="^(bullish|bearish|neutral)$")
    timeframe_validity: int = Field(..., ge=1, le=60)

    @validator('risk_assessment')
    def validate_risk_assessment(cls, v):
        required_fields = ['risk_score', 'max_drawdown_expected', 'key_risks']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Missing required field: {field}")

        if not 0 <= v['risk_score'] <= 1:
            raise ValueError("Risk score must be between 0 and 1")

        return v

    @validator('stop_loss_price')
    def validate_stop_loss(cls, v, values):
        # Additional validation can check against current price
        return v

class ResponseValidator:
    """
    Validates and sanitizes LLM responses.
    """

    @staticmethod
    def validate_trading_signal(
        response: Dict[str, Any],
        current_price: Decimal
    ) -> Optional[TradingSignal]:
        """
        Validate trading signal from LLM.
        """
        try:
            # Parse with Pydantic model
            signal = TradingSignal(**response)

            # Additional business logic validation
            if signal.signal in ['entry_long', 'entry_short']:
                # Validate stop-loss placement
                if signal.signal == 'entry_long':
                    if signal.stop_loss_price >= float(current_price):
                        logger.warning("Invalid stop-loss for long position")
                        signal.stop_loss_price = float(current_price) * 0.97

                    if signal.take_profit_price <= float(current_price):
                        logger.warning("Invalid take-profit for long position")
                        signal.take_profit_price = float(current_price) * 1.05

                elif signal.signal == 'entry_short':
                    if signal.stop_loss_price <= float(current_price):
                        logger.warning("Invalid stop-loss for short position")
                        signal.stop_loss_price = float(current_price) * 1.03

                    if signal.take_profit_price >= float(current_price):
                        logger.warning("Invalid take-profit for short position")
                        signal.take_profit_price = float(current_price) * 0.95

            return signal

        except Exception as e:
            logger.error(f"Signal validation failed: {e}")
            return None

    @staticmethod
    def create_safe_default_signal(reason: str = "validation_failed") -> Dict[str, Any]:
        """
        Create a safe default signal when validation fails.
        """
        return {
            "signal": "hold",
            "confidence": 0.0,
            "recommended_size": 0,
            "recommended_leverage": 1,
            "stop_loss_price": 0,
            "take_profit_price": 0,
            "reasoning": f"Using safe default due to: {reason}",
            "risk_assessment": {
                "risk_score": 1.0,
                "max_drawdown_expected": 0,
                "key_risks": ["validation_failure"]
            },
            "market_sentiment": "neutral",
            "timeframe_validity": 3
        }
```

### 4. Decision Engine Service

**File**: `workspace/features/decision_engine/service.py`

```python
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from decimal import Decimal
import logging

from .llm_client import LLMOrchestrator
from .prompts import PromptTemplates
from .validator import ResponseValidator, TradingSignal
from ..database.connection import DatabaseConnection
from ..cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

class DecisionEngine:
    """
    Main decision engine orchestrating LLM analysis and signal generation.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.llm = LLMOrchestrator(config['llm'])
        self.validator = ResponseValidator()
        self.db = DatabaseConnection(config['database'])
        self.redis = RedisClient(config['redis'])

        # Performance tracking
        self.decision_count = 0
        self.total_latency_ms = 0
        self.success_count = 0

    async def analyze_market(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        positions: List[Dict[str, Any]],
        risk_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze market and generate trading decision.
        """
        start_time = datetime.now(UTC)
        cycle_id = f"decision_{symbol}_{start_time.timestamp()}"

        try:
            # Build prompt
            prompt = PromptTemplates.build_market_analysis_prompt(
                symbol=symbol,
                market_data=market_data,
                positions=positions,
                risk_params=risk_params
            )

            # Check token count
            estimated_tokens = len(prompt) // 4
            if estimated_tokens > 2000:
                logger.warning(f"Prompt too long ({estimated_tokens} tokens), truncating")
                prompt = prompt[:8000]  # ~2000 tokens

            # Generate decision
            llm_response = await self.llm.generate_decision(prompt)

            if 'error' in llm_response:
                logger.error(f"LLM generation failed: {llm_response['error']}")
                decision = self.validator.create_safe_default_signal("llm_error")
            else:
                # Validate response
                current_price = Decimal(str(market_data['close']))
                validated_signal = self.validator.validate_trading_signal(
                    llm_response['decision'],
                    current_price
                )

                if validated_signal:
                    decision = validated_signal.dict()
                else:
                    decision = self.validator.create_safe_default_signal("validation_failed")

            # Calculate latency
            latency_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

            # Store decision in database
            await self._store_decision(
                cycle_id=cycle_id,
                symbol=symbol,
                decision=decision,
                llm_response=llm_response,
                market_snapshot=market_data,
                latency_ms=latency_ms
            )

            # Update metrics
            self.decision_count += 1
            self.total_latency_ms += latency_ms
            if decision['signal'] != 'hold' or decision['confidence'] > 0.5:
                self.success_count += 1

            # Cache decision
            await self.redis.set(
                f"decision:{symbol}:latest",
                decision,
                expire_seconds=180  # 3 minutes
            )

            return {
                "cycle_id": cycle_id,
                "symbol": symbol,
                "decision": decision,
                "latency_ms": latency_ms,
                "model_used": llm_response.get('model', 'unknown'),
                "tokens_used": llm_response.get('tokens_used', 0),
                "timestamp": start_time.isoformat()
            }

        except Exception as e:
            logger.error(f"Decision engine error for {symbol}: {e}")
            return {
                "cycle_id": cycle_id,
                "symbol": symbol,
                "decision": self.validator.create_safe_default_signal("engine_error"),
                "error": str(e),
                "timestamp": start_time.isoformat()
            }

    async def analyze_portfolio(
        self,
        market_data: Dict[str, Any],
        positions: List[Dict[str, Any]],
        risk_params: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze entire portfolio and generate decisions for all assets.
        """
        tasks = []
        for symbol in market_data.keys():
            task = self.analyze_market(
                symbol=symbol,
                market_data=market_data[symbol],
                positions=[p for p in positions if p['symbol'] == symbol],
                risk_params=risk_params
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        decisions = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Portfolio analysis error: {result}")
            else:
                decisions.append(result)

        return decisions

    async def _store_decision(
        self,
        cycle_id: str,
        symbol: str,
        decision: Dict[str, Any],
        llm_response: Dict[str, Any],
        market_snapshot: Dict[str, Any],
        latency_ms: int
    ) -> None:
        """
        Store decision in database for analysis.
        """
        try:
            await self.db.execute("""
                INSERT INTO trading.trading_signals (
                    id, symbol, signal_type, confidence,
                    llm_provider, llm_model, llm_response,
                    llm_reasoning, token_usage, response_time_ms,
                    recommended_size, recommended_leverage,
                    stop_loss_price, take_profit_price,
                    risk_score, indicators, cycle_id,
                    created_at
                ) VALUES (
                    gen_random_uuid(), $1, $2, $3,
                    $4, $5, $6, $7, $8, $9,
                    $10, $11, $12, $13, $14, $15, $16,
                    NOW()
                )
            """,
                symbol,
                decision['signal'],
                decision['confidence'],
                'openrouter',
                llm_response.get('model', 'unknown'),
                json.dumps(llm_response),
                decision['reasoning'],
                llm_response.get('tokens_used', 0),
                latency_ms,
                decision['recommended_size'],
                decision['recommended_leverage'],
                decision['stop_loss_price'],
                decision['take_profit_price'],
                decision['risk_assessment']['risk_score'],
                json.dumps(market_snapshot.get('indicators', {})),
                cycle_id
            )
        except Exception as e:
            logger.error(f"Failed to store decision: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get decision engine performance metrics.
        """
        avg_latency = (
            self.total_latency_ms / self.decision_count
            if self.decision_count > 0 else 0
        )

        success_rate = (
            self.success_count / self.decision_count
            if self.decision_count > 0 else 0
        )

        token_stats = self.llm.get_token_usage_stats()

        return {
            "total_decisions": self.decision_count,
            "avg_latency_ms": avg_latency,
            "success_rate": success_rate,
            "token_usage": token_stats
        }
```

## Validation Requirements

### Level 1: Unit Tests
```python
async def test_llm_response_generation():
    """Test LLM generates valid responses."""
    provider = DeepSeekProvider(test_api_key)
    response = await provider.generate(test_prompt)
    assert 'decision' in response
    assert response['latency_ms'] < 1000

async def test_signal_validation():
    """Test signal validation logic."""
    validator = ResponseValidator()
    valid_signal = {
        "signal": "entry_long",
        "confidence": 0.8,
        # ... complete signal
    }
    result = validator.validate_trading_signal(valid_signal, Decimal("50000"))
    assert result is not None

async def test_prompt_building():
    """Test prompt template generation."""
    prompt = PromptTemplates.build_market_analysis_prompt(
        symbol="BTC",
        market_data=test_market_data,
        positions=[],
        risk_params=test_risk_params
    )
    assert len(prompt) < 8000  # Token limit
```

### Level 2: Integration Tests
- End-to-end decision generation
- Failover to backup LLM
- Database storage verification
- Cache functionality

### Level 3: Performance Tests
- Decision latency <1 second
- Handle 6 assets concurrently
- Token usage optimization
- Cost tracking accuracy

## Acceptance Criteria

### Must Have
- [x] DeepSeek integration working
- [x] JSON response validation
- [x] <1 second latency
- [x] Failover to Qwen3
- [x] Token usage tracking
- [x] Safe defaults on error

### Should Have
- [x] Prompt optimization
- [x] Multi-asset analysis
- [x] Decision caching
- [x] Performance metrics

---

**PRP Status**: Ready for Implementation
**Estimated Hours**: 52 hours (26 story points)
**Priority**: Critical - Core decision making
**Dependencies**: Market Data Service must be complete