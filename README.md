# Trading Strategy DSL - Natural Language to Backtest Pipeline

A complete pipeline that converts natural language trading rules into executable backtests through a custom Domain-Specific Language (DSL).

## Architecture Overview

```
Natural Language -> JSON -> DSL -> AST -> Python Code -> Backtest Results
```

**Pipeline Components:**
1. **NL Parser** - Converts natural language to structured JSON using Groq API
2. **JSON to DSL Converter** - Transforms JSON into DSL text
3. **DSL Parser** - Parses DSL into Abstract Syntax Tree (AST) using Lark
4. **Code Generator** - Generates executable Python from AST
5. **Backtester** - Simulates strategy and calculates performance metrics

---

## Installation

```bash
pip install -r requirements.txt
```

**Set up API key:**
```bash
export GROQ_API_KEY='your-groq-api-key-here'
```

Or create a `.env` file:
```
GROQ_API_KEY=your-groq-api-key-here
```

---

## Quick Start

### Run the Complete Pipeline

```bash
python pipeline.py
```

This runs an example strategy end-to-end using Apple stock data.

### Run from Natural Language

```python
from pipeline import TradingStrategyPipeline
import yfinance as yf

# Initialize
pipeline = TradingStrategyPipeline()

# Load data
df = yf.Ticker("AAPL").history(start="2015-01-01", end="2025-01-01")

# Define strategy in natural language
nl_input = "Buy when close is above 20-day moving average and volume is above 1 million. Exit when RSI(14) is below 30."

# Run complete pipeline
results = pipeline.run(nl_input, df, initial_capital=10000)
```

### Run from DSL Directly (More Deterministic)

```python
dsl = """
ENTRY:
  close > SMA(close, 20) AND volume > 1000000

EXIT:
  RSI(close, 14) < 30
"""

results = pipeline.run_from_dsl(dsl, df, initial_capital=10000)
```

---

# Running Tests

## Test Individual Components

**Test DSL Parser:**
```bash
python dsl_parser.py
```

**Test Code Generator:**
```bash
python code_generator.py
```

**Test Indicators:**
```bash
python indicators.py
```

**Test Backtester:**
```bash
python backtest.py
```

**Test NL Parser:**
```bash
python nl_parser.py
```

### Test Determinism

Create `test_determinism.py`:

```python
from pipeline import TradingStrategyPipeline, load_sample_data

dsl = """
ENTRY:
  close > SMA(close, 20) AND volume > 1000000

EXIT:
  RSI(close, 14) < 30
"""

# Load data once
df = load_sample_data(start_date="2020-01-01", end_date="2024-01-01")

# Run multiple times
pipeline = TradingStrategyPipeline()
for i in range(3):
    results = pipeline.run_from_dsl(dsl, df, initial_capital=10000, verbose=False)
    print(f"Run {i+1}: {results['backtest_results']['total_trades']} trades, "
          f"Final: ${results['backtest_results']['final_equity']:,.2f}")
```

Run:
```bash
python test_determinism.py
```

All runs should produce identical results.

---

## Demo Scenarios

### Demo 1: Momentum Strategy

```python
from pipeline import TradingStrategyPipeline, load_sample_data

pipeline = TradingStrategyPipeline()
df = load_sample_data(start_date="2020-01-01", end_date="2024-01-01")

nl_input = "Enter when price crosses above yesterday's high and RSI is above 50. Exit when RSI drops below 40."

results = pipeline.run(nl_input, df, initial_capital=10000, verbose=True)
```

### Demo 2: Mean Reversion Strategy

```python
dsl = """
ENTRY:
  RSI(close, 14) < 30 AND close < SMA(close, 50)

EXIT:
  RSI(close, 14) > 70 OR close > SMA(close, 50)
"""

results = pipeline.run_from_dsl(dsl, df, initial_capital=10000, verbose=True)
print(f"\nWin Rate: {results['backtest_results']['win_rate']}%")
print(f"Total Return: {results['backtest_results']['total_return_pct']}%")
```

### Demo 3: Breakout Strategy

```python
dsl = """
ENTRY:
  close CROSSES_ABOVE PREV(high, 1) AND volume > PREV(volume, 1) * 2.0

EXIT:
  close < SMA(close, 10)
"""

results = pipeline.run_from_dsl(dsl, df, initial_capital=10000, verbose=True)
```

---

## Output Metrics

The backtest returns comprehensive performance metrics:

- **Total Trades** - Number of completed trades
- **Winning/Losing Trades** - Breakdown of profitable vs unprofitable
- **Win Rate** - Percentage of winning trades
- **Total Return** - Absolute and percentage returns
- **Max Drawdown** - Maximum peak-to-trough decline
- **Average Return** - Mean return per trade
- **Average Win/Loss** - Mean profit/loss for winning/losing trades
- **Profit Factor** - Ratio of gross profits to gross losses
- **Sharpe Ratio** - Risk-adjusted return metric
- **Trade Log** - Detailed entry/exit for each trade

---


## DSL Grammar Reference
Full DSL syntax and grammar specification is available here:
[DSL_GRAMMAR.md](docs/DSL_GRAMMER.md)

## File Structure

```
.
|-- pipeline.py           # Main orchestrator
|-- nl_parser.py          # Natural language → JSON
|-- dsl_converter.py      # JSON → DSL text
|-- dsl_parser.py         # DSL → AST (Lark grammar)
|-- code_generator.py     # AST → Python code
|-- indicators.py         # Technical indicator implementations
|-- backtest.py           # Backtesting engine
|-- docs
    |-- Design.md         # Why these tools + what's next
    |-- DSL_GRAMMAR.md    # Full DSL grammar specification        
|-- README.md             # Main documentation and usage guide

```

---

## Notes on Determinism

**Deterministic Results:**
- Use `run_from_dsl()` with fixed DSL strings
- Use fixed date ranges: `load_sample_data(start="2020-01-01", end="2024-01-01")`
- Same DSL + same data = identical results

**Non-Deterministic Results:**
- Using `run()` with natural language input
- LLM (Groq API) may produce slightly different JSON representations
- This is expected behavior for LLM-based parsing

---

## Troubleshooting

**Issue: "GROQ_API_KEY not found"**
```bash
export GROQ_API_KEY='your-key-here'
```

**Issue: "KeyError: 'close'"**
- DataFrame columns should be lowercase: `close`, `open`, `high`, `low`, `volume`
- The pipeline automatically normalizes yfinance data

**Issue: "min_periods must be an integer"**
- Ensure all indicator functions convert periods to int
- This is fixed in the provided `indicators.py`

**Issue: Different results on each run**
- Use `run_from_dsl()` instead of `run()` for determinism
- Use fixed date ranges instead of `period="max"`


---



