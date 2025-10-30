"""
LLM Decision Engine

Integrates with LLM providers (OpenRouter) to generate trading decisions
based on market data analysis.

Author: Decision Engine Implementation Team
Date: 2025-10-28
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

import httpx

from workspace.features.caching import CacheService
from workspace.features.market_data import MarketDataSnapshot
from workspace.features.trading_loop import TradingDecision, TradingSignal

from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OPENROUTER = "openrouter"
    ANTHROPIC = "anthropic"  # Direct Anthropic API (future)
    OPENAI = "openai"  # Direct OpenAI API (future)


@dataclass
class LLMConfig:
    """LLM configuration"""

    provider: LLMProvider
    model: str
    api_key: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: float = 30.0


class LLMDecisionEngine:
    """
    LLM Decision Engine

    Uses Large Language Models to analyze market data and generate
    trading signals with reasoning.

    Features:
    - OpenRouter API integration
    - Multi-model support (Claude, GPT-4, etc.)
    - Structured prompt engineering
    - JSON response parsing
    - Error handling and retry logic

    Attributes:
        config: LLM configuration
        prompt_builder: Prompt builder instance
        client: HTTP client for API calls

    Example:
        ```python
        engine = LLMDecisionEngine(
            provider="openrouter",
            model="anthropic/claude-3.5-sonnet",
            api_key="your-api-key",
        )

        signals = await engine.generate_signals(
            snapshots={'BTCUSDT': snapshot},
            capital_chf=Decimal("2626.96"),
        )
        ```
    """

    # OpenRouter API endpoint
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(
        self,
        provider: str = "openrouter",
        model: str = "anthropic/claude-3.5-sonnet",
        api_key: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 30.0,
        cache_service: Optional[CacheService] = None,
    ):
        """
        Initialize LLM Decision Engine

        Args:
            provider: LLM provider (default: "openrouter")
            model: Model identifier (e.g., "anthropic/claude-3.5-sonnet")
            api_key: API key for the provider
            temperature: Sampling temperature (0.0-1.0, default: 0.7)
            max_tokens: Maximum response tokens (default: 2000)
            timeout: Request timeout in seconds (default: 30.0)
            cache_service: Optional CacheService instance (default: creates new one)
        """
        self.config = LLMConfig(
            provider=LLMProvider(provider),
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )

        self.prompt_builder = PromptBuilder()
        self.client = httpx.AsyncClient(timeout=timeout)

        # Initialize cache service
        if cache_service is not None:
            self.cache = cache_service
        else:
            self.cache = CacheService()

        logger.info("LLM Decision Engine initialized with caching")

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    def _generate_cache_key(
        self,
        snapshots: Dict[str, MarketDataSnapshot],
    ) -> str:
        """
        Generate cache key from market snapshots

        Key includes:
        - Symbol
        - Rounded price (to nearest $10 for BTC, $1 for others)
        - Rounded indicators (RSI to nearest 5, MACD to 2 decimals)
        - Model name

        This allows caching similar market conditions.

        Args:
            snapshots: Market data snapshots

        Returns:
            Cache key string
        """
        # Build cache input by rounding market data for each symbol
        cache_inputs = {}

        for symbol, snapshot in snapshots.items():
            # Extract price from ticker
            price = float(snapshot.ticker.last) if snapshot.ticker else 0.0

            # Round price to reduce cache misses
            if "BTC" in symbol:
                rounded_price = round(price / 10) * 10  # Nearest $10
            else:
                rounded_price = round(price)  # Nearest $1

            # Round indicators
            # RSI and MACD can be objects or Decimals, handle both
            if snapshot.rsi:
                if hasattr(snapshot.rsi, "value"):
                    rsi = float(snapshot.rsi.value)
                else:
                    # RSI object, extract numeric value
                    rsi = float(str(snapshot.rsi))  # type: ignore
                rounded_rsi = round(rsi / 5) * 5  # Nearest 5
            else:
                rounded_rsi = 0

            if snapshot.macd:
                if hasattr(snapshot.macd, "macd_line"):
                    macd = float(snapshot.macd.macd_line)
                else:
                    # MACD object, extract numeric value
                    macd = float(str(snapshot.macd))  # type: ignore
                rounded_macd = round(macd, 2)  # 2 decimals
            else:
                rounded_macd = 0

            cache_inputs[symbol] = {
                "price": rounded_price,
                "rsi": rounded_rsi,
                "macd": rounded_macd,
            }

        # Create hashable representation
        cache_data = {
            "snapshots": cache_inputs,
            "model": self.config.model,
        }

        # Generate cache key (MD5 used for cache key generation only, not security)
        cache_key = f"llm:signals:{hashlib.md5(json.dumps(cache_data, sort_keys=True).encode(), usedforsecurity=False).hexdigest()}"

        return cache_key

    async def generate_signals(
        self,
        snapshots: Dict[str, MarketDataSnapshot],
        capital_chf: Decimal = Decimal("2626.96"),
        max_position_size_chf: Decimal = Decimal("525.39"),
        current_positions: Optional[Dict[str, Dict]] = None,
        risk_context: Optional[Dict] = None,
        use_cache: bool = True,
    ) -> Dict[str, TradingSignal]:
        """
        Generate trading signals for all symbols with LLM response caching

        Cache TTL: 180 seconds (3 minutes - one decision cycle)

        Args:
            snapshots: Market data snapshots for each symbol
            capital_chf: Available trading capital
            max_position_size_chf: Maximum position size per trade
            current_positions: Current open positions (optional)
            risk_context: Additional risk context (optional)
            use_cache: Whether to use cache (default: True)

        Returns:
            Dictionary mapping symbol to TradingSignal

        Raises:
            Exception: If LLM API call fails or response parsing fails
        """
        import time

        start_time = time.time()

        logger.info(f"Generating trading signals for {len(snapshots)} symbols")

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(snapshots)

            # Try cache first
            if use_cache:
                cached_signals = await self.cache.get(cache_key)
                if cached_signals is not None:
                    logger.info(f"LLM cache hit for {len(snapshots)} symbols")

                    # Reconstruct signals from cached data
                    signals = {}
                    for symbol, signal_data in cached_signals.items():
                        signal = TradingSignal(
                            symbol=signal_data["symbol"],
                            decision=TradingDecision(signal_data["decision"]),
                            confidence=Decimal(str(signal_data["confidence"])),
                            size_pct=Decimal(str(signal_data["size_pct"])),
                            stop_loss_pct=(
                                Decimal(str(signal_data["stop_loss_pct"]))
                                if signal_data.get("stop_loss_pct")
                                else None
                            ),
                            take_profit_pct=(
                                Decimal(str(signal_data["take_profit_pct"]))
                                if signal_data.get("take_profit_pct")
                                else None
                            ),
                            reasoning=signal_data.get("reasoning", ""),
                            model_used=signal_data.get("model_used", ""),
                            tokens_input=signal_data.get("tokens_input", 0),
                            tokens_output=signal_data.get("tokens_output", 0),
                            cost_usd=Decimal(str(signal_data.get("cost_usd", 0))),
                            generation_time_ms=signal_data.get("generation_time_ms", 0),
                        )
                        signals[symbol] = signal

                    # Add cache metadata
                    for signal in signals.values():
                        signal.from_cache = True

                    return signals

            # Cache miss - call LLM
            logger.info(f"LLM cache miss for {len(snapshots)} symbols, calling LLM")

            # Build prompt
            prompt = self.prompt_builder.build_trading_prompt(
                snapshots=snapshots,
                capital_chf=capital_chf,
                max_position_size_chf=max_position_size_chf,
                current_positions=current_positions,
                risk_context=risk_context,
            )

            prompt_tokens = len(prompt.split())  # Rough estimate
            logger.debug(
                f"Prompt length: {len(prompt)} characters (~{prompt_tokens} tokens)"
            )

            # Call LLM and capture usage data
            response_text, usage_data = await self._call_llm(prompt)

            logger.debug(f"LLM response length: {len(response_text)} characters")

            # Calculate generation time
            generation_time_ms = int((time.time() - start_time) * 1000)

            # Parse response
            signals = self._parse_response(response_text, snapshots)

            # Add observability fields to all signals
            for signal in signals.values():
                signal.model_used = self.config.model
                signal.tokens_input = usage_data.get("prompt_tokens", prompt_tokens)
                signal.tokens_output = usage_data.get(
                    "completion_tokens", len(response_text.split())
                )
                signal.generation_time_ms = generation_time_ms
                signal.from_cache = False

                # Calculate cost based on provider/model
                if signal.tokens_input and signal.tokens_output:
                    signal.cost_usd = self._calculate_cost(
                        signal.tokens_input, signal.tokens_output, self.config.model
                    )

            logger.info(
                f"Generated {len(signals)} trading signals "
                f"(tokens: {usage_data.get('prompt_tokens', 0)}/{usage_data.get('completion_tokens', 0)}, "
                f"cost: ${sum(s.cost_usd or Decimal('0') for s in signals.values()):.4f}, "
                f"time: {generation_time_ms}ms)"
            )

            # Cache the signals for 180 seconds (one decision cycle)
            if use_cache:
                # Serialize signals for caching
                serialized_signals = {}
                for symbol, signal in signals.items():
                    serialized_signals[symbol] = {
                        "symbol": signal.symbol,
                        "decision": signal.decision.value,
                        "confidence": str(signal.confidence),
                        "size_pct": str(signal.size_pct),
                        "stop_loss_pct": (
                            str(signal.stop_loss_pct) if signal.stop_loss_pct else None
                        ),
                        "take_profit_pct": (
                            str(signal.take_profit_pct)
                            if signal.take_profit_pct
                            else None
                        ),
                        "reasoning": signal.reasoning or "",
                        "model_used": signal.model_used or "",
                        "tokens_input": signal.tokens_input or 0,
                        "tokens_output": signal.tokens_output or 0,
                        "cost_usd": str(signal.cost_usd) if signal.cost_usd else "0",
                        "generation_time_ms": signal.generation_time_ms or 0,
                    }

                await self.cache.set(cache_key, serialized_signals, ttl_seconds=180)
                logger.debug(f"Cached LLM signals with key: {cache_key[:16]}...")

            return signals

        except Exception as e:
            logger.error(f"Error generating signals: {e}", exc_info=True)
            # Return HOLD signals on error (fail-safe)
            return self._generate_fallback_signals(snapshots)

    async def _call_llm(self, prompt: str) -> tuple[str, Dict[str, int]]:
        """
        Call LLM API with prompt

        Args:
            prompt: Formatted prompt text

        Returns:
            Tuple of (response_text, usage_data)
            usage_data contains: {'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int}

        Raises:
            Exception: If API call fails
        """
        if self.config.provider == LLMProvider.OPENROUTER:
            return await self._call_openrouter(prompt)
        else:
            raise NotImplementedError(
                f"Provider {self.config.provider} not implemented"
            )

    async def _call_openrouter(self, prompt: str) -> tuple[str, Dict[str, int]]:
        """
        Call OpenRouter API

        Args:
            prompt: Formatted prompt text

        Returns:
            Tuple of (response_text, usage_data)

        Raises:
            Exception: If API call fails
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional
            "X-Title": "LLM Crypto Trading System",  # Optional
        }

        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        logger.debug(f"Calling OpenRouter API: {self.config.model}")

        try:
            response = await self.client.post(
                self.OPENROUTER_URL,
                headers=headers,
                json=payload,
            )

            response.raise_for_status()

            data = response.json()

            # Extract response text
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0].get("message", {})
                content = message.get("content", "")

                if not content:
                    raise ValueError("Empty response from LLM")

                # Extract usage data
                usage_data = {}
                if "usage" in data:
                    usage_data = {
                        "prompt_tokens": data["usage"].get("prompt_tokens", 0),
                        "completion_tokens": data["usage"].get("completion_tokens", 0),
                        "total_tokens": data["usage"].get("total_tokens", 0),
                    }
                    logger.debug(
                        f"Token usage: {usage_data['prompt_tokens']} input / "
                        f"{usage_data['completion_tokens']} output"
                    )
                else:
                    # Estimate if usage not provided
                    usage_data = {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(content.split()),
                        "total_tokens": len(prompt.split()) + len(content.split()),
                    }

                return content, usage_data

            else:
                raise ValueError("Invalid response structure from OpenRouter")

        except httpx.HTTPStatusError as e:
            logger.error(
                f"OpenRouter API error: {e.response.status_code} - {e.response.text}"
            )
            raise Exception(f"OpenRouter API error: {e.response.status_code}")

        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}", exc_info=True)
            raise

    def _parse_response(
        self,
        response_text: str,
        snapshots: Dict[str, MarketDataSnapshot],
    ) -> Dict[str, TradingSignal]:
        """
        Parse LLM response into trading signals

        Args:
            response_text: Raw LLM response text
            snapshots: Market data snapshots (for validation)

        Returns:
            Dictionary mapping symbol to TradingSignal
        """
        signals = {}

        try:
            # Extract JSON blocks from response
            json_blocks = self._extract_json_blocks(response_text)

            if not json_blocks:
                logger.warning("No JSON blocks found in LLM response")
                return self._generate_fallback_signals(snapshots)

            # Parse each JSON block
            for json_str in json_blocks:
                try:
                    data = json.loads(json_str)

                    # Validate and create signal
                    signal = self._create_signal_from_json(data)

                    if signal and signal.symbol in snapshots:
                        signals[signal.symbol] = signal
                    else:
                        logger.warning(
                            f"Invalid or unknown symbol in signal: {data.get('symbol')}"
                        )

                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON block: {e}")
                    continue

                except Exception as e:
                    logger.warning(f"Failed to create signal from JSON: {e}")
                    continue

            # Generate HOLD signals for missing symbols
            for symbol in snapshots:
                if symbol not in signals:
                    logger.warning(f"No signal generated for {symbol}, using HOLD")
                    signals[symbol] = TradingSignal(
                        symbol=symbol,
                        decision=TradingDecision.HOLD,
                        confidence=Decimal("0.5"),
                        size_pct=Decimal("0.0"),
                        reasoning="No signal generated by LLM",
                    )

            return signals

        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}", exc_info=True)
            return self._generate_fallback_signals(snapshots)

    def _extract_json_blocks(self, text: str) -> List[str]:
        """
        Extract JSON code blocks from text

        Looks for JSON between ```json and ``` markers, or standalone {} blocks.

        Args:
            text: Text containing JSON blocks

        Returns:
            List of JSON strings
        """
        json_blocks = []

        # Method 1: Extract from ```json code blocks
        import re

        pattern = r"```json\s*(\{.*?\})\s*```"
        matches = re.findall(pattern, text, re.DOTALL)
        json_blocks.extend(matches)

        # Method 2: Extract standalone JSON objects
        if not json_blocks:
            # Try to find JSON objects in the text
            pattern = r'\{[^{}]*"symbol"[^{}]*\}'
            matches = re.findall(pattern, text, re.DOTALL)
            json_blocks.extend(matches)

        return json_blocks

    def _create_signal_from_json(self, data: dict) -> Optional[TradingSignal]:
        """
        Create TradingSignal from parsed JSON

        Args:
            data: Parsed JSON dictionary

        Returns:
            TradingSignal or None if invalid
        """
        try:
            # Required fields
            symbol = data.get("symbol")
            decision_str = data.get("decision", "").upper()
            confidence = data.get("confidence", 0.5)
            size_pct = data.get("size_pct", 0.0)

            if not symbol or not decision_str:
                return None

            # Validate decision
            try:
                decision = TradingDecision(decision_str.lower())
            except ValueError:
                logger.warning(f"Invalid decision: {decision_str}")
                return None

            # Optional fields
            stop_loss_pct = data.get("stop_loss_pct")
            take_profit_pct = data.get("take_profit_pct")
            reasoning = data.get("reasoning", "")

            # Convert to Decimal
            signal = TradingSignal(
                symbol=symbol,
                decision=decision,
                confidence=Decimal(str(confidence)),
                size_pct=Decimal(str(size_pct)),
                stop_loss_pct=Decimal(str(stop_loss_pct)) if stop_loss_pct else None,
                take_profit_pct=(
                    Decimal(str(take_profit_pct)) if take_profit_pct else None
                ),
                reasoning=reasoning,
            )

            return signal

        except Exception as e:
            logger.warning(f"Failed to create signal from JSON: {e}")
            return None

    def _generate_fallback_signals(
        self,
        snapshots: Dict[str, MarketDataSnapshot],
    ) -> Dict[str, TradingSignal]:
        """
        Generate fallback HOLD signals

        Used when LLM fails or returns invalid response.

        Args:
            snapshots: Market data snapshots

        Returns:
            Dictionary of HOLD signals for all symbols
        """
        logger.warning("Generating fallback HOLD signals")

        signals = {}
        for symbol in snapshots:
            signals[symbol] = TradingSignal(
                symbol=symbol,
                decision=TradingDecision.HOLD,
                confidence=Decimal("0.5"),
                size_pct=Decimal("0.0"),
                reasoning="Fallback signal - LLM error or invalid response",
            )

        return signals

    def _calculate_cost(
        self, input_tokens: int, output_tokens: int, model: str
    ) -> Decimal:
        """
        Calculate estimated cost in USD for LLM API call

        Pricing as of 2025-10-28:
        - Claude 3.5 Sonnet (via OpenRouter): $3.00/1M input, $15.00/1M output
        - Claude 3 Haiku (via OpenRouter): $0.25/1M input, $1.25/1M output
        - GPT-4 Turbo (via OpenRouter): $10.00/1M input, $30.00/1M output
        - GPT-3.5 Turbo (via OpenRouter): $0.50/1M input, $1.50/1M output

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        # Pricing table (per 1M tokens)
        pricing = {
            # Claude models
            "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
            "anthropic/claude-3-sonnet": {"input": 3.00, "output": 15.00},
            "anthropic/claude-3-haiku": {"input": 0.25, "output": 1.25},
            "anthropic/claude-3-opus": {"input": 15.00, "output": 75.00},
            # GPT models
            "openai/gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "openai/gpt-4": {"input": 30.00, "output": 60.00},
            "openai/gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            # DeepSeek models (if available)
            "deepseek/deepseek-chat": {"input": 0.27, "output": 1.10},
            # Default pricing if model not found
            "default": {"input": 1.00, "output": 3.00},
        }

        # Get pricing for model (or use default)
        model_pricing = pricing.get(model.lower(), pricing["default"])

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
        total_cost = input_cost + output_cost

        return Decimal(str(total_cost))


# Export
__all__ = [
    "LLMDecisionEngine",
    "LLMProvider",
    "LLMConfig",
]
