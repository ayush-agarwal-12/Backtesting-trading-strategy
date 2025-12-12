# Trading Strategy DSL - Grammar Specification

## Overview

This document describes the Domain-Specific Language (DSL) for expressing trading strategies. The DSL is designed to be human-readable, unambiguous, and expressive enough to capture common trading patterns while remaining simple to parse and validate.

## Design Philosophy

**Goals:**
- Readable by non-programmers familiar with trading
- Unambiguous syntax (no hidden behavior)
- Easy to validate and provide helpful error messages
- Extensible for future indicators and operators

**Influences:**
- SQL (declarative keywords: ENTRY, EXIT)
- Trading domain terminology (close, volume, SMA, RSI)
- Mathematical notation (>, <, AND, OR)

## Grammar Structure

### High-Level Structure

Every strategy consists of two sections:

```
ENTRY:
  <condition>

EXIT:
  <condition>
```

- **ENTRY**: Defines when to enter a position (buy)
- **EXIT**: Defines when to exit a position (sell)
- Both sections are required
- Empty conditions can be expressed as `TRUE` or `FALSE`

### Basic Syntax Rules

1. **Keywords are UPPERCASE**: `ENTRY`, `EXIT`, `AND`, `OR`, `CROSSES_ABOVE`, `CROSSES_BELOW`
2. **Field names are lowercase**: `close`, `open`, `high`, `low`, `volume`
3. **Indicator names are UPPERCASE**: `SMA()`, `EMA()`, `RSI()`, `PREV()`
4. **Indentation**: 2 spaces after section headers (recommended for readability)
5. **Case sensitivity**: Field names and keywords are case-sensitive

## Language Components

### 1. Fields

Available fields from OHLCV data:

| Field | Description | Example Value |
|-------|-------------|---------------|
| `open` | Opening price | 150.25 |
| `high` | Highest price | 152.80 |
| `low` | Lowest price | 149.50 |
| `close` | Closing price | 151.75 |
| `volume` | Trading volume | 5000000 |

### 2. Comparison Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `>` | Greater than | `close > 100` |
| `<` | Less than | `volume < 1000000` |
| `>=` | Greater than or equal | `close >= open` |
| `<=` | Less than or equal | `low <= 50` |
| `==` | Equal to | `close == high` |

### 3. Special Operators

#### Cross Operators

| Operator | Meaning | When It Triggers |
|----------|---------|------------------|
| `CROSSES_ABOVE` | Crosses above threshold | Current > threshold AND previous <= threshold |
| `CROSSES_BELOW` | Crosses below threshold | Current < threshold AND previous >= threshold |

**Example:**
```
close CROSSES_ABOVE SMA(close, 50)
```
This triggers when:
- Today: close > SMA(50)
- Yesterday: close <= SMA(50)

### 4. Logical Operators

Combine multiple conditions:

| Operator | Meaning | Syntax |
|----------|---------|--------|
| `AND` | Both conditions must be true | `condition1 AND condition2` |
| `OR` | At least one condition must be true | `condition1 OR condition2` |

**Precedence:**
- `AND` has higher precedence than `OR`
- Use parentheses for explicit grouping: `(A OR B) AND C`

### 5. Arithmetic Operators

Perform calculations on fields and values:

| Operator | Meaning | Example |
|----------|---------|---------|
| `+` | Addition | `close + 10` |
| `-` | Subtraction | `high - low` |
| `*` | Multiplication | `volume * 1.5` |
| `/` | Division | `close / 2` |

**Example:**
```
volume > PREV(volume, 1) * 1.30
```
Entry when volume is 30% higher than previous day.

### 6. Technical Indicators

#### Simple Moving Average (SMA)

**Syntax:** `SMA(field, period)`

**Parameters:**
- `field`: Which price field to average (typically `close`)
- `period`: Number of periods (must be integer)

**Examples:**
```
close > SMA(close, 20)      # Close above 20-day moving average
SMA(close, 50) > SMA(close, 200)  # Golden cross
```

#### Exponential Moving Average (EMA)

**Syntax:** `EMA(field, period)`

**Parameters:**
- `field`: Which price field to average
- `period`: Number of periods for decay calculation

**Examples:**
```
close > EMA(close, 12)      # Close above 12-period EMA
EMA(close, 12) CROSSES_ABOVE EMA(close, 26)  # MACD-style cross
```

#### Relative Strength Index (RSI)

**Syntax:** `RSI(field, period)`

**Parameters:**
- `field`: Price field (typically `close`)
- `period`: Lookback period (commonly 14)

**Returns:** Value between 0 and 100

**Examples:**
```
RSI(close, 14) < 30         # Oversold condition
RSI(close, 14) > 70         # Overbought condition
```

#### Previous Value (PREV)

**Syntax:** `PREV(field, N)`

**Parameters:**
- `field`: Which field to look back
- `N`: Number of periods ago (1 = yesterday)

**Examples:**
```
close > PREV(high, 1)       # Close above yesterday's high
volume > PREV(volume, 5)    # Volume above 5 days ago
```

## Complete Examples

### Example 1: Simple Moving Average Crossover

**Strategy:** Buy when price crosses above 50-day MA, sell when crosses below.

```
ENTRY:
  close CROSSES_ABOVE SMA(close, 50)

EXIT:
  close CROSSES_BELOW SMA(close, 50)
```

### Example 2: RSI Mean Reversion

**Strategy:** Buy oversold (RSI < 30), sell overbought (RSI > 70).

```
ENTRY:
  RSI(close, 14) < 30

EXIT:
  RSI(close, 14) > 70
```

### Example 3: Breakout with Volume Confirmation

**Strategy:** Buy on new high with high volume, exit on RSI overbought.

```
ENTRY:
  close > PREV(high, 1) AND volume > PREV(volume, 1) * 2.0

EXIT:
  RSI(close, 14) > 70
```

### Example 4: Multiple Moving Average System

**Strategy:** Buy when fast MA above slow MA and price above both, exit when fast MA crosses below slow MA.

```
ENTRY:
  close > SMA(close, 20) AND close > SMA(close, 50) AND SMA(close, 20) > SMA(close, 50)

EXIT:
  SMA(close, 20) CROSSES_BELOW SMA(close, 50)
```

### Example 5: Complex Multi-Condition Entry

**Strategy:** Buy on trending + volume spike, exit on stop or target.

```
ENTRY:
  close > SMA(close, 20) AND SMA(close, 20) > SMA(close, 50) AND volume > SMA(volume, 20) * 1.5

EXIT:
  RSI(close, 14) < 30 OR close < SMA(close, 20)
```

### Example 6: Percentage-Based Stop

**Strategy:** Enter on moving average cross, exit on 5% loss or 10% gain.

```
ENTRY:
  close CROSSES_ABOVE SMA(close, 50)

EXIT:
  close < SMA(close, 50) * 0.95 OR close > SMA(close, 50) * 1.10
```

## Grammar Formal Specification (EBNF)

```ebnf
strategy       ::= entry_section exit_section

entry_section  ::= "ENTRY:" expression
exit_section   ::= "EXIT:" expression

expression     ::= or_expr
or_expr        ::= and_expr ("OR" and_expr)*
and_expr       ::= comparison ("AND" comparison)*

comparison     ::= term operator term
                 | term cross_operator term

term           ::= field
                 | indicator
                 | number
                 | arithmetic_expr
                 | "(" expression ")"

arithmetic_expr ::= term arith_op term

indicator      ::= identifier "(" term ("," term)* ")"
field          ::= identifier

operator       ::= ">" | "<" | ">=" | "<=" | "=="
cross_operator ::= "CROSSES_ABOVE" | "CROSSES_BELOW"
arith_op       ::= "+" | "-" | "*" | "/"

identifier     ::= [a-zA-Z_][a-zA-Z0-9_]*
number         ::= [0-9]+ ("." [0-9]+)?
```

## Validation Rules

The parser enforces these constraints:

1. **Valid field names**: Only `open`, `high`, `low`, `close`, `volume`
2. **Valid indicators**: Only `SMA`, `EMA`, `RSI`, `PREV`
3. **Integer periods**: Indicator periods must be whole numbers (converted automatically)
4. **Required sections**: Both `ENTRY` and `EXIT` must be present
5. **Balanced parentheses**: All opening parentheses must have closing pairs
6. **Type consistency**: Cannot compare incompatible types

## Common Patterns

### Trend Following
```
ENTRY:
  close > SMA(close, 50) AND SMA(close, 50) > SMA(close, 200)

EXIT:
  close < SMA(close, 50)
```

### Mean Reversion
```
ENTRY:
  RSI(close, 14) < 30 AND close < SMA(close, 20)

EXIT:
  RSI(close, 14) > 50
```

### Momentum Breakout
```
ENTRY:
  close CROSSES_ABOVE PREV(high, 1) AND volume > SMA(volume, 20) * 2

EXIT:
  close < SMA(close, 10)
```

### Volatility Breakout
```
ENTRY:
  high - low > SMA(high - low, 20) * 1.5 AND close > open

EXIT:
  close < SMA(close, 20)
```

## Error Handling

The parser provides clear error messages:

**Invalid field:**
```
ENTRY:
  price > 100
```
Error: `Unknown field: price. Valid fields: {open, high, low, close, volume}`

**Invalid indicator:**
```
ENTRY:
  MACD(close, 12, 26) > 0
```
Error: `Unknown indicator: macd. Valid indicators: {sma, ema, rsi, prev}`

**Missing section:**
```
ENTRY:
  close > 100
```
Error: `Missing 'exit' section`

**Syntax error:**
```
ENTRY:
  close > SMA(close 20)
```
Error: `Expected comma in indicator parameters at line 2`

## Limitations and Future Extensions

### Current Limitations

1. **No position sizing**: Always all-in trades
2. **No stop loss/take profit**: Must express as exit conditions
3. **Long only**: No short selling support
4. **Single asset**: No portfolio strategies
5. **No time-based rules**: Cannot express "exit after 5 days"

### Planned Extensions

1. **Position sizing**: `SIZE: 50%` (half capital per trade)
2. **Risk management**: `STOP_LOSS: 2%`, `TAKE_PROFIT: 5%`
3. **Time filters**: `ENTRY_TIME: 09:30-16:00`
4. **More indicators**: Bollinger Bands, MACD, ATR, Stochastic
5. **Multi-timeframe**: `SMA(close[1h], 20)` for hourly data

## Best Practices

### 1. Be Explicit
```
# Good: Clear and explicit
close > SMA(close, 20) AND volume > 1000000

# Avoid: Implicit assumptions
close > 20  # 20 what? Price, MA, RSI?
```

### 2. Use Meaningful Periods
```
# Good: Standard periods
RSI(close, 14)  # Standard RSI period
SMA(close, 50)  # Common moving average

# Avoid: Arbitrary periods
RSI(close, 17)  # Non-standard, hard to understand
```

### 3. Document Complex Conditions
```
# Good: Complex but understandable
# Golden cross with volume confirmation
SMA(close, 50) CROSSES_ABOVE SMA(close, 200) AND volume > SMA(volume, 20) * 2

# Avoid: Overly complex without documentation
(A AND B AND C) OR (D AND E) OR (F AND G AND H)
```

### 4. Symmetric Entry/Exit
```
# Good: Symmetric logic
ENTRY:
  close CROSSES_ABOVE SMA(close, 50)
EXIT:
  close CROSSES_BELOW SMA(close, 50)

# Avoid: Mismatched logic (unless intentional)
ENTRY:
  close > SMA(close, 50)
EXIT:
  RSI(close, 14) < 30
```

## Appendix: Complete Grammar in Lark Format

The actual implementation uses Lark parser with this grammar:

```lark
start: entry_section exit_section

entry_section: "ENTRY:" expression
exit_section: "EXIT:" expression

?expression: or_expr

or_expr: and_expr ("OR" and_expr)*
and_expr: comparison ("AND" comparison)*

comparison: term OPERATOR term
         | term CROSS_OPERATOR term

?term: field
     | indicator  
     | number
     | arithmetic_expr
     | "(" expression ")"

arithmetic_expr: term ARITH_OP term

indicator: IDENTIFIER "(" term ("," term)* ")"
field: IDENTIFIER

OPERATOR: ">" | "<" | ">=" | "<=" | "=="
CROSS_OPERATOR: "CROSSES_ABOVE" | "CROSSES_BELOW"
ARITH_OP: "*" | "/" | "+" | "-"

number: SIGNED_NUMBER

IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/

%import common.SIGNED_NUMBER
%import common.WS
%ignore WS
```

## Summary

This DSL provides:
- **Clear syntax**: Easy to read and write
- **Type safety**: Validated at parse time
- **Expressiveness**: Can capture common trading patterns
- **Extensibility**: Easy to add new indicators and operators
- **Good errors**: Helpful messages for debugging

For implementation details, see `dsl_parser.py` and `DESIGN.md`.