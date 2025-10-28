# Success Metrics & KPIs: LLM-Powered Cryptocurrency Trading System

**Document Version**: 1.0
**Date**: 2025-10-27
**Phase**: P1 - Business Discovery & Requirements
**Status**: Draft for Review
**Business Analyst**: Claude Business Analyst Agent

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Metrics Framework](#2-metrics-framework)
3. [Technical Performance Metrics](#3-technical-performance-metrics)
4. [Trading Performance Metrics](#4-trading-performance-metrics)
5. [Risk & Compliance Metrics](#5-risk--compliance-metrics)
6. [Operational Excellence Metrics](#6-operational-excellence-metrics)
7. [Cost Efficiency Metrics](#7-cost-efficiency-metrics)
8. [User Experience Metrics](#8-user-experience-metrics)
9. [Monitoring Strategy](#9-monitoring-strategy)
10. [Reporting Cadence](#10-reporting-cadence)
11. [Alerting Thresholds](#11-alerting-thresholds)
12. [Success Criteria by Phase](#12-success-criteria-by-phase)

---

## 1. Executive Summary

This document defines quantifiable success metrics for the LLM-Powered Cryptocurrency Trading System. Metrics are organized into 6 categories covering technical performance, trading outcomes, risk management, operations, costs, and user experience.

### Key Performance Indicators (North Star Metrics)

| Category | Metric | Target | Measurement |
|----------|--------|--------|-------------|
| **Profitability** | Sharpe Ratio | >0.5 | Monthly calculation |
| **Reliability** | System Uptime | >99.5% | Continuous monitoring |
| **Risk Control** | Stop-Loss Adherence | 100% | Real-time validation |
| **Efficiency** | Decision Latency | <2 seconds | Per-cycle measurement |
| **Cost** | LLM Operating Cost | <$100/month | Daily aggregation |

### Success Definition

The system is considered successful when:
1. Sharpe Ratio >0.5 sustained for 3 consecutive months
2. Zero critical incidents (data loss, uncontrolled losses) in 90 days
3. Operating costs remain within budget (<$150/month total)
4. Operator satisfaction score >8/10 (quarterly survey)

---

## 2. Metrics Framework

### Metrics Hierarchy

```
North Star Metrics (What matters most)
    ↓
Primary KPIs (Critical success indicators)
    ↓
Secondary Metrics (Supporting indicators)
    ↓
Diagnostic Metrics (Troubleshooting & optimization)
```

### Metrics Categorization

**Outcome Metrics** (Lagging Indicators):
- Profitability (Sharpe Ratio, Total Return, Win Rate)
- System Reliability (Uptime, MTBF)
- User Satisfaction

**Output Metrics** (Leading Indicators):
- Trading Cycle Success Rate
- Decision Confidence Levels
- Risk Limit Adherence

**Process Metrics** (Activity Indicators):
- API Call Volume
- Database Query Performance
- Error Rates

**Input Metrics** (Capacity Indicators):
- Market Data Quality
- LLM API Availability
- System Resource Utilization

---

## 3. Technical Performance Metrics

### 3.1 Decision Latency

**Definition**: Time from trading cycle trigger to decision ready for execution

**Measurement**:
```
Decision_Latency = timestamp(decision_ready) - timestamp(cycle_start)
```

**Targets**:
- **Target**: <2 seconds (average)
- **Acceptable**: <3 seconds (95th percentile)
- **Critical**: <5 seconds (99th percentile)

**Breakdown**:
- Market data fetch: <500ms
- Indicator calculation: <200ms
- LLM API call: <1000ms
- Response parsing: <100ms
- Signal validation: <50ms

**Collection Method**: Log timestamp at each pipeline stage

**Alerting**:
- Warning: Average latency >2.5s for 5 consecutive cycles
- Critical: Single cycle latency >5s

**Dashboard Visualization**: Time series line chart with percentile bands

---

### 3.2 System Uptime

**Definition**: Percentage of time system is operational and processing trading cycles

**Measurement**:
```
Uptime_Pct = (Total_Time - Downtime) / Total_Time × 100
```

**Targets**:
- **Target**: >99.5% (43 minutes downtime/month maximum)
- **Acceptable**: >99.0% (7 hours downtime/month)
- **Unacceptable**: <99.0%

**Downtime Classification**:
- **Planned**: Scheduled maintenance (excluded from SLA)
- **Unplanned**: Crashes, failures (counted against SLA)
- **Degraded**: Operating but with errors (50% weight in calculation)

**Collection Method**: Heartbeat monitoring (30-second intervals)

**Alerting**:
- Critical: System unresponsive for >3 minutes
- Warning: 3+ failed cycles in 30 minutes

**Dashboard Visualization**: Uptime percentage gauge + downtime incident log

---

### 3.3 API Response Time

**Definition**: Time for internal API endpoints to respond to requests

**Measurement**:
```
API_Response_Time = timestamp(response_sent) - timestamp(request_received)
```

**Targets by Endpoint**:
- GET /api/positions/current: <200ms (95th percentile)
- POST /api/trading/manual-trigger: <500ms
- GET /api/performance/metrics: <300ms
- GET /api/dashboard/realtime: <150ms

**Collection Method**: Middleware logging for all API requests

**Alerting**:
- Warning: 95th percentile >500ms for any endpoint
- Critical: 99th percentile >1000ms

**Dashboard Visualization**: Heatmap of response times by endpoint

---

### 3.4 Database Query Performance

**Definition**: Execution time for critical database queries

**Measurement**:
```
Query_Time = timestamp(query_end) - timestamp(query_start)
```

**Targets**:
- Position queries: <50ms (95th percentile)
- Market data queries: <100ms
- Performance metric queries: <200ms
- Audit log writes: <30ms

**Collection Method**: Database query logging with execution plans

**Alerting**:
- Warning: Query time >100ms for position queries
- Critical: Any query >1000ms (indicates indexing issue)

**Optimization Triggers**:
- Slow query threshold: >200ms → investigate indexes
- Connection pool exhaustion → scale connections

**Dashboard Visualization**: Slowest queries table + query time distribution

---

### 3.5 Memory & CPU Utilization

**Definition**: System resource consumption

**Measurement**:
- Memory: `psutil.virtual_memory().percent`
- CPU: `psutil.cpu_percent(interval=1)`

**Targets**:
- Memory usage: <2GB sustained, <3GB peak
- CPU usage: <50% average, <80% peak (during trading cycle)

**Collection Method**: System monitoring every 30 seconds

**Alerting**:
- Warning: Memory >2.5GB for >5 minutes
- Critical: Memory >3GB (risk of OOM kill)
- Warning: CPU >70% for >10 minutes

**Dashboard Visualization**: Resource usage time series with alert thresholds

---

### 3.6 Cache Hit Rate

**Definition**: Percentage of data requests served from cache vs. database

**Measurement**:
```
Cache_Hit_Rate = Cache_Hits / (Cache_Hits + Cache_Misses) × 100
```

**Targets**:
- Market data cache: >95% hit rate
- Position cache: >90% hit rate
- Configuration cache: >99% hit rate

**Collection Method**: Redis metrics + application-level counters

**Alerting**:
- Warning: Cache hit rate <90% for market data (indicates cache issues)

**Dashboard Visualization**: Hit rate gauge + cache performance breakdown

---

## 4. Trading Performance Metrics

### 4.1 Sharpe Ratio

**Definition**: Risk-adjusted return metric (annualized)

**Measurement**:
```
Sharpe_Ratio = (Mean_Return - Risk_Free_Rate) / StdDev_Returns
```

Where:
- Mean_Return: Average daily return (annualized)
- Risk_Free_Rate: 0% (assume zero for crypto)
- StdDev_Returns: Standard deviation of daily returns (annualized)

**Targets**:
- **Excellent**: >1.0 (top quartile trading systems)
- **Target**: >0.5 (demonstrable alpha)
- **Acceptable**: >0.3 (better than random)
- **Poor**: <0.3 (investigate strategy issues)

**Calculation Period**: Rolling 30-day window, recalculated daily

**Collection Method**: Daily P&L aggregation from closed positions

**Alerting**:
- Warning: Sharpe ratio <0.3 for 14 consecutive days
- Critical: Sharpe ratio negative for 7 consecutive days

**Dashboard Visualization**: Line chart of rolling 30-day Sharpe ratio

---

### 4.2 Total Return (ROI)

**Definition**: Cumulative profit or loss as percentage of initial capital

**Measurement**:
```
Total_Return_Pct = (Current_Portfolio_Value - Initial_Capital) / Initial_Capital × 100
```

**Targets**:
- Monthly: Positive return (>0%)
- Quarterly: >5% return
- Annual: >20% return (aspirational, market-dependent)

**Breakdown**:
- Realized return: From closed positions only
- Unrealized return: Including open position P&L

**Collection Method**: Portfolio valuation at 00:00 UTC daily

**Alerting**:
- Warning: Monthly return <-5%
- Critical: Quarterly return <-10%

**Dashboard Visualization**: Equity curve (cumulative return over time)

---

### 4.3 Win Rate

**Definition**: Percentage of profitable trades vs. total trades

**Measurement**:
```
Win_Rate = Profitable_Trades / Total_Closed_Trades × 100
```

**Targets**:
- **Excellent**: >60%
- **Target**: >45%
- **Acceptable**: >40%
- **Poor**: <40% (strategy issue)

**Considerations**:
- Win rate alone is insufficient (need profit factor)
- High win rate with small wins, rare large losses = bad
- Low win rate with large wins, frequent small losses = acceptable

**Collection Method**: Classify trades as profitable (realized P&L > 0) or unprofitable

**Alerting**:
- Warning: Win rate <40% for 50 consecutive trades
- Informational: Win rate >70% (may indicate overfitting or cherry-picking)

**Dashboard Visualization**: Win rate gauge + trade P&L distribution histogram

---

### 4.4 Average Profit per Trade

**Definition**: Mean realized profit/loss per closed trade

**Measurement**:
```
Avg_Profit = Sum(Realized_P&L) / Total_Closed_Trades
```

**Targets**:
- **Target**: >$50 per trade (covers fees + generates profit)
- **Acceptable**: >$20 per trade
- **Poor**: <$10 per trade or negative

**Breakdown**:
- Average winning trade: >$100
- Average losing trade: <-$40 (should be smaller than wins)
- Profit factor = Avg_Win / Abs(Avg_Loss) > 2.0 (target)

**Collection Method**: Aggregate realized P&L from closed positions

**Alerting**:
- Warning: Average profit <$10 for 30 consecutive trades

**Dashboard Visualization**: Bar chart of avg win vs. avg loss

---

### 4.5 Maximum Drawdown

**Definition**: Largest peak-to-trough decline in portfolio value

**Measurement**:
```
Max_Drawdown_Pct = (Trough_Value - Peak_Value) / Peak_Value × 100
```

**Targets**:
- **Excellent**: <10%
- **Target**: <15%
- **Acceptable**: <20%
- **Unacceptable**: >25% (risk management failure)

**Types**:
- Unrealized drawdown: Including open positions
- Realized drawdown: From closed positions only
- Current drawdown: Distance from all-time high

**Collection Method**: Track portfolio high-water mark, calculate drawdown daily

**Alerting**:
- Warning: Current drawdown >15%
- Critical: Current drawdown >20% (consider pausing trading)

**Dashboard Visualization**: Drawdown chart (underwater equity curve)

---

### 4.6 Profit Factor

**Definition**: Ratio of gross profit to gross loss

**Measurement**:
```
Profit_Factor = Gross_Profit / Abs(Gross_Loss)
```

Where:
- Gross_Profit = Sum of all profitable trades
- Gross_Loss = Sum of all losing trades (absolute value)

**Targets**:
- **Excellent**: >2.0 (wins are 2x larger than losses)
- **Target**: >1.5
- **Acceptable**: >1.2
- **Poor**: <1.0 (losing more than gaining)

**Collection Method**: Aggregate winning and losing trade P&L separately

**Alerting**:
- Warning: Profit factor <1.2 for 50 consecutive trades
- Critical: Profit factor <1.0 (system losing money)

**Dashboard Visualization**: Profit factor gauge + trend line

---

### 4.7 Trade Frequency

**Definition**: Number of trades executed per time period

**Measurement**:
- Trades per day
- Trades per week
- Trades per symbol

**Targets**:
- **Expected**: 5-15 trades/day (across 6 symbols)
- **Acceptable**: 3-20 trades/day
- **Low**: <3 trades/day (signal generation issue)
- **High**: >20 trades/day (overtrading, check confidence thresholds)

**Collection Method**: Count position entries from database

**Alerting**:
- Warning: <3 trades in 24 hours (signal generation issue)
- Warning: >25 trades in 24 hours (overtrading)

**Dashboard Visualization**: Trade frequency histogram by day/symbol

---

## 5. Risk & Compliance Metrics

### 5.1 Stop-Loss Adherence Rate

**Definition**: Percentage of positions with stop-loss orders properly placed and maintained

**Measurement**:
```
Stop_Loss_Adherence = Positions_With_Stop_Loss / Total_Active_Positions × 100
```

**Target**: **100%** (zero tolerance)

**Monitoring**:
- Verify stop-loss order exists on exchange for every position
- Check stop-loss order is active (not cancelled or expired)
- Validate stop-loss price is within acceptable range of entry

**Collection Method**: Position reconciliation every 30 minutes

**Alerting**:
- **Critical**: ANY position without stop-loss (immediate alert)
- Automated action: Close position if stop-loss placement fails

**Dashboard Visualization**: Stop-loss adherence gauge (must show 100%)

---

### 5.2 Risk Limit Violations

**Definition**: Number of instances where risk limits are breached

**Measurement**: Count of violations by type:
- Leverage outside 5-40x range
- Position size exceeds risk_usd limit
- Total exposure exceeds 80% of account
- Daily loss exceeds circuit breaker threshold

**Target**: **Zero violations** (100% compliance)

**Collection Method**: Log all risk check failures before order execution

**Alerting**:
- **Critical**: Any risk limit violation (indicates control failure)

**Dashboard Visualization**: Violation count by type (should be zero)

---

### 5.3 Position Reconciliation Accuracy

**Definition**: Agreement between system position records and exchange positions

**Measurement**:
```
Reconciliation_Accuracy = Matching_Positions / Total_Positions × 100
```

**Target**: >99.9% (allows for temporary sync delays)

**Discrepancy Types**:
- Orphaned positions (on exchange, not in system)
- Ghost positions (in system, not on exchange)
- Quantity mismatches
- Price mismatches

**Collection Method**: Reconciliation process every 30 minutes

**Alerting**:
- Warning: Any discrepancy detected
- Critical: Discrepancy value >$100 or persists >1 hour

**Dashboard Visualization**: Reconciliation status + discrepancy log

---

### 5.4 Audit Log Completeness

**Definition**: Percentage of trading decisions with complete audit trail

**Measurement**:
```
Audit_Completeness = Complete_Audit_Records / Total_Decisions × 100
```

Required fields for completeness:
- Timestamp, symbol, market data snapshot, LLM model, prompt, response, decision, execution result

**Target**: 100% (all decisions logged)

**Collection Method**: Validate audit log entries on each decision

**Alerting**:
- Warning: Missing audit data for any decision

**Dashboard Visualization**: Audit completeness gauge

---

### 5.5 Daily Loss Limit Usage

**Definition**: Current daily loss as percentage of circuit breaker limit

**Measurement**:
```
Loss_Limit_Usage = Current_Daily_Loss / Daily_Loss_Limit × 100
```

**Targets**:
- **Safe**: <50% (well within limit)
- **Caution**: 50-70% (monitor closely)
- **Warning**: 70-90% (reduce risk)
- **Critical**: >90% (approaching circuit breaker)

**Collection Method**: Real-time aggregation of closed position P&L

**Alerting**:
- Warning: Usage >70%
- Critical: Usage >90%
- Automated action: Close all positions at 100% (circuit breaker)

**Dashboard Visualization**: Loss limit usage gauge with color zones

---

## 6. Operational Excellence Metrics

### 6.1 Trading Cycle Success Rate

**Definition**: Percentage of trading cycles that complete successfully

**Measurement**:
```
Cycle_Success_Rate = Successful_Cycles / Total_Cycles × 100
```

**Success Definition**: Cycle completes all stages without errors:
- Market data fetched
- Indicators calculated
- LLM decision obtained
- Signals validated
- Execution completed (or skipped if "hold")

**Targets**:
- **Target**: >99% success rate
- **Acceptable**: >95%
- **Poor**: <95% (system instability)

**Failure Classification**:
- Data failures (market data unavailable)
- LLM failures (API timeout, invalid response)
- Execution failures (order rejected)
- System failures (crashes, timeouts)

**Collection Method**: Log outcome of each trading cycle (success/failure/reason)

**Alerting**:
- Warning: <97% success rate over 100 cycles
- Critical: 5 consecutive cycle failures

**Dashboard Visualization**: Success rate trend + failure breakdown pie chart

---

### 6.2 Mean Time Between Failures (MTBF)

**Definition**: Average time between system failures

**Measurement**:
```
MTBF = Total_Operating_Time / Number_of_Failures
```

Failure defined as: System crash, unplanned restart, critical error requiring intervention

**Target**: >168 hours (7 days)

**Collection Method**: Track system restarts and critical error events

**Alerting**:
- Warning: MTBF <72 hours (3 days) over 30-day period

**Dashboard Visualization**: MTBF trend line + failure incident timeline

---

### 6.3 Mean Time To Recovery (MTTR)

**Definition**: Average time to restore service after failure

**Measurement**:
```
MTTR = Sum(Recovery_Times) / Number_of_Failures
```

Recovery time = timestamp(service_restored) - timestamp(failure_detected)

**Targets**:
- **Excellent**: <3 minutes (automatic recovery)
- **Target**: <10 minutes (minimal manual intervention)
- **Acceptable**: <30 minutes
- **Poor**: >30 minutes (requires significant troubleshooting)

**Collection Method**: Log failure and recovery timestamps

**Alerting**:
- Informational: MTTR >10 minutes (review recovery procedures)

**Dashboard Visualization**: MTTR by failure type

---

### 6.4 Error Rate by Category

**Definition**: Frequency of errors by type

**Measurement**: Errors per 1000 operations, categorized:
- Market data errors
- LLM API errors
- Exchange API errors
- Database errors
- Application logic errors

**Targets**:
- Critical errors: <1 per 1000 operations
- Warnings: <10 per 1000 operations
- Info-level issues: <50 per 1000 operations

**Collection Method**: Aggregate application logs by severity and category

**Alerting**:
- Warning: Error rate spike (2x baseline)
- Critical: Critical error rate >5 per 1000

**Dashboard Visualization**: Error rate heatmap by category and severity

---

### 6.5 Deployment Success Rate

**Definition**: Percentage of deployments that complete without rollback

**Measurement**:
```
Deployment_Success = Successful_Deployments / Total_Deployments × 100
```

**Target**: >95% (no more than 1 in 20 deployments require rollback)

**Collection Method**: Track deployment events and rollback events

**Alerting**:
- Informational: Deployment rollback (review deployment process)

**Dashboard Visualization**: Deployment history with success/failure indicators

---

## 7. Cost Efficiency Metrics

### 7.1 LLM Token Usage & Cost

**Definition**: Total tokens consumed and cost incurred from LLM APIs

**Measurement**:
- Tokens per decision (prompt + completion)
- Cost per decision ($ per LLM call)
- Daily cost, monthly cost

**Targets**:
- **Tokens per decision**: <2000 tokens average
- **Cost per decision**: <$0.01 average
- **Daily cost**: <$3.30 ($100/month ÷ 30 days)
- **Monthly cost**: <$100 (hard limit)

**Cost Breakdown**:
- By model (which models are most expensive)
- By symbol (does one asset cost more to analyze)
- By time of day (cost variations)

**Collection Method**: Extract token usage from LLM API responses, calculate cost using model pricing

**Alerting**:
- Warning: Daily cost >$2.50 (75% of budget)
- Critical: Monthly cost >$80 (approaching limit)
- Automated action: Switch to cheaper model at $90/month

**Dashboard Visualization**: Cost trend line + budget usage gauge

---

### 7.2 Cost Per Trade

**Definition**: Total operating cost divided by number of trades

**Measurement**:
```
Cost_Per_Trade = (LLM_Costs + Infrastructure_Costs + Exchange_Fees) / Total_Trades
```

**Targets**:
- **Target**: <$5 per trade (all costs included)
- **Acceptable**: <$10 per trade
- **Poor**: >$10 per trade (cost efficiency issue)

**Breakdown**:
- LLM cost component: ~$0.50-$1.00
- Infrastructure cost component: ~$1.50 ($50/month ÷ ~30 trades/month)
- Exchange fee component: ~$2-$4 (0.04% × $5000 position × 2 trades)

**Collection Method**: Aggregate all costs and trade counts monthly

**Alerting**:
- Informational: Cost per trade >$10 (review cost optimization)

**Dashboard Visualization**: Cost per trade stacked bar (by component)

---

### 7.3 Infrastructure Cost

**Definition**: Hosting, database, and service costs

**Measurement**:
- Cloud hosting: VPS or cloud instance monthly cost
- Database: PostgreSQL hosting (if separate)
- Redis: Cache service cost (if managed)
- Monitoring: Optional monitoring service costs

**Budget**: <$50/month

**Collection Method**: Track monthly infrastructure invoices

**Dashboard Visualization**: Cost breakdown by service

---

### 7.4 Cost Efficiency Ratio

**Definition**: Revenue generated per dollar of operating cost

**Measurement**:
```
Cost_Efficiency = Gross_Profit / Total_Operating_Costs
```

**Targets**:
- **Excellent**: >10:1 (generate $10 for every $1 spent)
- **Target**: >5:1
- **Acceptable**: >2:1
- **Poor**: <2:1 (costs eating into profits)

**Collection Method**: Compare gross profit (before costs) to total operating costs

**Alerting**:
- Warning: Ratio <3:1 for consecutive month

**Dashboard Visualization**: Efficiency ratio trend

---

## 8. User Experience Metrics

### 8.1 Operator Satisfaction Score

**Definition**: Subjective assessment of operator happiness with system

**Measurement**: Quarterly survey with questions:
- Ease of use (1-10)
- Reliability (1-10)
- Clarity of information (1-10)
- Confidence in system (1-10)
- Would you recommend? (1-10)

**Target**: >8/10 average across all questions

**Collection Method**: Quarterly survey (Google Forms or similar)

**Dashboard Visualization**: Satisfaction score trend + question breakdown

---

### 8.2 Alert Fatigue Index

**Definition**: Ratio of actionable alerts to total alerts

**Measurement**:
```
Alert_Fatigue = Actionable_Alerts / Total_Alerts × 100
```

Actionable defined as: Alert that required operator action or investigation

**Targets**:
- **Excellent**: >80% of alerts are actionable
- **Acceptable**: >60%
- **Poor**: <50% (too many false alarms)

**Collection Method**: Track alerts sent and operator action logs

**Alerting**:
- Informational: Alert fatigue <60% (tune alert thresholds)

**Dashboard Visualization**: Alert volume + actionable percentage

---

### 8.3 Dashboard Load Time

**Definition**: Time for dashboard to load and display data

**Measurement**: Time from page request to fully rendered (client-side measurement)

**Target**: <2 seconds (95th percentile)

**Collection Method**: Browser performance API in dashboard frontend

**Dashboard Visualization**: Load time distribution histogram

---

## 9. Monitoring Strategy

### 9.1 Monitoring Architecture

```
┌─────────────────────────────────────────────────┐
│         Application Metrics Layer               │
│  (Custom metrics from trading system)           │
│  - Trading cycle outcomes                       │
│  - Position states                              │
│  - LLM API interactions                         │
└─────────────────────┬───────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│      System Metrics Layer (Prometheus)          │
│  - CPU, Memory, Disk                            │
│  - Network I/O                                  │
│  - Database connections                         │
└─────────────────────┬───────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│    Visualization Layer (Grafana/Dashboard)      │
│  - Real-time dashboards                         │
│  - Historical analysis                          │
│  - Custom widgets                               │
└─────────────────────┬───────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│       Alerting Layer (Email/SMS/Slack)          │
│  - Threshold-based alerts                       │
│  - Anomaly detection alerts                     │
│  - Critical incident notifications              │
└─────────────────────────────────────────────────┘
```

### 9.2 Data Collection Methods

**Real-Time Metrics** (Updated every cycle):
- Trading cycle success/failure
- Position P&L
- Decision latency
- Active position count

**Near Real-Time** (Updated every 30 seconds):
- System resource utilization
- API response times
- Error rates

**Periodic Metrics** (Updated hourly/daily):
- Sharpe ratio
- Maximum drawdown
- Cost accumulation
- Win rate

**Batch Metrics** (Calculated on demand):
- Monthly performance summary
- Model comparison analytics
- Audit reports

### 9.3 Metric Storage

**Time Series Database** (Prometheus/InfluxDB):
- All continuous metrics (latency, CPU, memory, etc.)
- Retention: 90 days high-resolution, 2 years downsampled

**Relational Database** (PostgreSQL):
- Audit logs (7 years retention)
- Trade history (indefinite retention)
- Position records (indefinite retention)

**Redis** (Cache):
- Real-time metrics (5-minute TTL)
- Current position states (no expiry)
- Recent error logs (1-hour TTL)

---

## 10. Reporting Cadence

### 10.1 Real-Time Dashboard (Continuous)

**Audience**: System operator (active monitoring)

**Contents**:
- Current positions with live P&L
- Last trading cycle outcome
- System health indicators (green/yellow/red)
- Recent alerts (last 10)
- Key metrics: Uptime, cycle success rate, daily P&L

**Update Frequency**: Every 3 minutes (after each trading cycle)

**Access**: Web dashboard, always available

---

### 10.2 Daily Report (00:00 UTC)

**Audience**: System operator, risk manager

**Contents**:
- Summary of trading activity (# trades, symbols active)
- Daily P&L (realized + unrealized)
- Win rate and profit factor for day
- System performance (uptime, cycle success rate)
- Cost summary (LLM usage, total cost)
- Notable events (errors, alerts, manual interventions)

**Delivery**: Email, dashboard archive

---

### 10.3 Weekly Report (Sunday 00:00 UTC)

**Audience**: System operator, performance analyst

**Contents**:
- Weekly P&L and comparison to previous weeks
- Sharpe ratio trend
- Model performance comparison (if A/B testing)
- Top performing and worst performing trades
- System reliability metrics (uptime, MTBF, MTTR)
- Cost efficiency analysis
- Risk metrics (drawdown, exposure, violations)

**Delivery**: Email, PDF export

---

### 10.4 Monthly Report (1st of month, 00:00 UTC)

**Audience**: All stakeholders

**Contents**:
- Comprehensive performance analysis
- Monthly P&L and ROI
- Sharpe ratio, maximum drawdown, profit factor
- Trade statistics (count, win rate, avg profit)
- Cost summary (LLM, infrastructure, exchange fees)
- Cost efficiency ratio
- System reliability summary
- Incident log (all failures, recoveries)
- Recommendations for next month (strategy adjustments, optimizations)

**Delivery**: Email, PDF report, presentation deck

---

### 10.5 Quarterly Business Review

**Audience**: All stakeholders, external stakeholders if applicable

**Contents**:
- Quarterly performance vs. targets
- ROI vs. buy-and-hold benchmark
- Risk-adjusted returns analysis
- Operational excellence summary
- Cost-benefit analysis
- Operator satisfaction survey results
- Strategic recommendations
- Roadmap for next quarter

**Delivery**: In-person or video meeting + presentation deck

---

## 11. Alerting Thresholds

### 11.1 Alert Severity Levels

**CRITICAL** (Immediate action required):
- Any position without stop-loss
- Daily loss limit approaching (>90%)
- System crash or unresponsive >3 minutes
- Risk limit violation
- API key authentication failure
- Data loss or corruption detected

**WARNING** (Investigation needed within 1 hour):
- Decision latency >2.5s for 5+ cycles
- LLM cost >$2.50/day (75% of budget)
- Cycle success rate <97%
- Cache hit rate <90%
- Error rate spike (2x baseline)
- Position reconciliation discrepancy

**INFORMATIONAL** (Awareness, no immediate action):
- Sharpe ratio trending down
- Model performance variance detected
- Deployment completed
- Configuration changed
- Circuit breaker tripped (after positions closed)

### 11.2 Alert Delivery Channels

**Critical Alerts**:
- Email (immediate)
- SMS (if configured)
- Dashboard (red banner)
- System log (ERROR level)

**Warning Alerts**:
- Email (within 5 minutes)
- Dashboard (yellow banner)
- System log (WARNING level)

**Informational Alerts**:
- Dashboard only (blue notification)
- System log (INFO level)

### 11.3 Alert Aggregation

To prevent alert fatigue:
- **Deduplication**: Same alert within 10 minutes = single notification
- **Aggregation**: Multiple warnings of same type = single summary alert
- **Quiet hours**: Informational alerts suppressed 22:00-08:00 (configurable)
- **Rate limiting**: Max 10 alerts per hour (critical always sent)

---

## 12. Success Criteria by Phase

### Phase 0: Foundation (Week 1-2)

**Success Criteria**:
- [ ] Database schema deployed and tested
- [ ] Exchange API connection established
- [ ] Market data fetching functional (all 6 symbols)
- [ ] Basic monitoring dashboard accessible

**Key Metrics**:
- Market data uptime: >95%
- API connection success rate: >99%

---

### Phase 1: Core Trading (Week 3-4)

**Success Criteria**:
- [ ] Position management system operational
- [ ] Order execution with retry logic functional
- [ ] Stop-loss orders placed automatically on all positions
- [ ] Position reconciliation working

**Key Metrics**:
- Order execution success rate: >95%
- Stop-loss adherence: 100%
- Position reconciliation accuracy: >99%

---

### Phase 2: LLM Integration (Week 5-6)

**Success Criteria**:
- [ ] OpenRouter API integrated with 3+ models
- [ ] LLM decisions parsed and validated correctly
- [ ] Token usage tracking functional
- [ ] Model failover working

**Key Metrics**:
- LLM API success rate: >98%
- JSON parsing success rate: >95%
- Decision latency: <2s average
- Token cost: <$0.01 per decision

---

### Phase 3: Risk & Monitoring (Week 7-8)

**Success Criteria**:
- [ ] Stop-loss monitoring active for all positions
- [ ] Daily loss limit circuit breaker functional
- [ ] Performance tracking and analytics working
- [ ] Alert system operational

**Key Metrics**:
- Stop-loss adherence: 100%
- Risk limit violations: 0
- Alert delivery success rate: 100%

---

### Phase 4: Paper Trading Validation (Week 9)

**Success Criteria**:
- [ ] System runs autonomously for 7 consecutive days
- [ ] All 6 cryptocurrencies traded
- [ ] Zero critical incidents
- [ ] Positive Sharpe ratio >0.3

**Key Metrics**:
- System uptime: >95%
- Cycle success rate: >95%
- Sharpe ratio: >0.3
- Win rate: >40%
- Decision latency: <2s

---

### Phase 5: Go-Live (Week 10+)

**Success Criteria**:
- [ ] Paper trading results validated
- [ ] All stakeholders signed off
- [ ] Real capital deployed
- [ ] 30-day live trading with positive results

**Key Metrics**:
- System uptime: >99.5%
- Cycle success rate: >99%
- Sharpe ratio: >0.5
- Win rate: >45%
- LLM cost: <$100/month
- Stop-loss adherence: 100%
- Zero risk violations

---

## Appendix A: Metrics Collection Code Examples

### Example 1: Decision Latency Tracking

```python
import time
from prometheus_client import Histogram

decision_latency = Histogram(
    'trading_decision_latency_seconds',
    'Time to complete trading decision',
    buckets=[0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
)

@decision_latency.time()
def execute_trading_cycle():
    start_time = time.time()

    # Fetch market data
    market_data = fetch_market_data()

    # Calculate indicators
    indicators = calculate_indicators(market_data)

    # Get LLM decision
    decision = get_llm_decision(market_data, indicators)

    # Validate and execute
    execute_signals(decision)

    latency = time.time() - start_time
    logger.info(f"Trading cycle completed in {latency:.2f}s")
```

### Example 2: Win Rate Calculation

```python
def calculate_win_rate(start_date, end_date):
    closed_positions = Position.query.filter(
        Position.status.in_(['CLOSED_MANUAL', 'CLOSED_STOP_LOSS',
                             'CLOSED_TAKE_PROFIT', 'CLOSED_INVALIDATED']),
        Position.exit_timestamp.between(start_date, end_date)
    ).all()

    profitable_trades = sum(1 for p in closed_positions if p.realized_pnl > 0)
    total_trades = len(closed_positions)

    win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0

    return {
        'win_rate': win_rate,
        'profitable_trades': profitable_trades,
        'total_trades': total_trades,
        'average_profit': sum(p.realized_pnl for p in closed_positions) / total_trades
    }
```

### Example 3: Sharpe Ratio Calculation

```python
import numpy as np

def calculate_sharpe_ratio(returns, periods_per_year=120):
    """
    Calculate annualized Sharpe ratio

    Args:
        returns: Array of daily returns (decimal, not percentage)
        periods_per_year: 120 for 3-minute cycles = 480 cycles/day * 30 days / 12 months

    Returns:
        Sharpe ratio (annualized)
    """
    if len(returns) < 2:
        return 0.0

    mean_return = np.mean(returns)
    std_return = np.std(returns)

    if std_return == 0:
        return 0.0

    # Annualize
    annualized_return = mean_return * periods_per_year
    annualized_std = std_return * np.sqrt(periods_per_year)

    sharpe_ratio = annualized_return / annualized_std

    return sharpe_ratio
```

---

## Appendix B: Dashboard Layout Recommendation

### Main Dashboard (Real-Time)

```
┌─────────────────────────────────────────────────────────┐
│  SYSTEM STATUS: ● Online   Uptime: 99.8%                │
│  Last Cycle: 2s ago (Success)   Daily P&L: +$127.43     │
├─────────────────────────────────────────────────────────┤
│  ACTIVE POSITIONS (3)                                    │
│  ┌─────────┬────────┬──────────┬──────────┬──────────┐ │
│  │ Symbol  │ Side   │ Unreal PL│ Entry    │ Stop Loss│ │
│  ├─────────┼────────┼──────────┼──────────┼──────────┤ │
│  │ BTCUSDT │ LONG   │ +$45.23  │ 67,234   │ 65,000   │ │
│  │ ETHUSDT │ SHORT  │ -$12.34  │ 3,456    │ 3,550    │ │
│  │ SOLUSDT │ LONG   │ +$23.11  │ 145.67   │ 140.00   │ │
│  └─────────┴────────┴──────────┴──────────┴──────────┘ │
├─────────────────────────────────────────────────────────┤
│  KEY METRICS                                             │
│  ┌──────────────────┬──────────────────┬──────────────┐│
│  │ Sharpe Ratio     │ Win Rate         │ Cycle Success││
│  │ 0.67 ↑           │ 52% ↑            │ 99.2% →      ││
│  └──────────────────┴──────────────────┴──────────────┘│
├─────────────────────────────────────────────────────────┤
│  RECENT ALERTS (Last 10)                                 │
│  ⚠ Warning: Decision latency 2.8s (3 min ago)          │
│  ℹ Info: Daily loss limit 45% used (5 min ago)         │
└─────────────────────────────────────────────────────────┘
```

### Performance Analytics Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  PERFORMANCE OVERVIEW - Last 30 Days                     │
├─────────────────────────────────────────────────────────┤
│  [Equity Curve Chart: Portfolio value over time]        │
│  [Drawdown Chart: Underwater equity curve]              │
├─────────────────────────────────────────────────────────┤
│  TRADE STATISTICS                                        │
│  Total Trades: 127    Win Rate: 54%    Avg Profit: $67  │
│  Profit Factor: 1.8   Max Drawdown: 12%   Sharpe: 0.67  │
├─────────────────────────────────────────────────────────┤
│  [Trade P&L Distribution Histogram]                     │
│  [Win/Loss by Symbol Bar Chart]                         │
└─────────────────────────────────────────────────────────┘
```

---

**Document Control**:
- Version: 1.0
- Status: Draft for Review
- Total Metrics Defined: 50+
- Categories: 6 (Technical, Trading, Risk, Operational, Cost, UX)
- Next Review Date: Upon stakeholder feedback
- Document Owner: Business Analyst Agent
- Location: `/Users/tobiprivat/Documents/GitProjects/personal/trader/PRPs/planning/backlog/trading-system-success-metrics.md`
