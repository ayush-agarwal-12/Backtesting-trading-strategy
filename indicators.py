"""
Technical Indicators Implementation
Pure NumPy/Pandas implementations without TA-Lib
"""

import numpy as np
import pandas as pd


def calculate_sma(series, period):
    """
    Simple Moving Average
    
    Args:
        series: pandas Series
        period: int or float, window period
        
    Returns:
        pandas Series
    """
    period = int(period)  # Ensure period is an integer
    return series.rolling(window=period, min_periods=period).mean()


def calculate_ema(series, period):
    """
    Exponential Moving Average
    
    Args:
        series: pandas Series
        period: int or float, span for EMA
        
    Returns:
        pandas Series
    """
    period = int(period)  # Ensure period is an integer
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def calculate_rsi(series, period=14):
    """
    Relative Strength Index
    
    Args:
        series: pandas Series (typically close prices)
        period: int or float, RSI period (default 14)
        
    Returns:
        pandas Series with RSI values (0-100)
    """
    period = int(period)  # Ensure period is an integer
    
    # Calculate price changes
    delta = series.diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate average gain and loss
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_bollinger_bands(series, period=20, std_dev=2):
    """
    Bollinger Bands
    
    Args:
        series: pandas Series
        period: int or float, window period
        std_dev: float, number of standard deviations
        
    Returns:
        tuple: (upper_band, middle_band, lower_band)
    """
    period = int(period)  # Ensure period is an integer
    middle = calculate_sma(series, period)
    std = series.rolling(window=period, min_periods=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return upper, middle, lower


def calculate_macd(series, fast=12, slow=26, signal=9):
    """
    MACD (Moving Average Convergence Divergence)
    
    Args:
        series: pandas Series
        fast: int or float, fast EMA period
        slow: int or float, slow EMA period
        signal: int or float, signal line period
        
    Returns:
        tuple: (macd_line, signal_line, histogram)
    """
    fast = int(fast)
    slow = int(slow)
    signal = int(signal)
    
    ema_fast = calculate_ema(series, fast)
    ema_slow = calculate_ema(series, slow)
    
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_atr(high, low, close, period=14):
    """
    Average True Range
    
    Args:
        high: pandas Series
        low: pandas Series
        close: pandas Series
        period: int or float, ATR period
        
    Returns:
        pandas Series
    """
    period = int(period)  # Ensure period is an integer
    
    # True Range components
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    # True Range is max of the three
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR is SMA of True Range
    atr = tr.rolling(window=period, min_periods=period).mean()
    
    return atr


def calculate_stochastic(high, low, close, k_period=14, d_period=3):
    """
    Stochastic Oscillator
    
    Args:
        high: pandas Series
        low: pandas Series
        close: pandas Series
        k_period: int or float, %K period
        d_period: int or float, %D period
        
    Returns:
        tuple: (k_values, d_values)
    """
    k_period = int(k_period)
    d_period = int(d_period)
    
    # Lowest low and highest high over k_period
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()
    
    # %K
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    
    # %D is SMA of %K
    d = k.rolling(window=d_period, min_periods=d_period).mean()
    
    return k, d


def prev(series, n=1):
    """
    Get value from N periods ago
    
    Args:
        series: pandas Series
        n: int or float, number of periods to look back
        
    Returns:
        pandas Series, shifted by n periods
    """
    n = int(n)  # Ensure n is an integer
    return series.shift(n)


# Indicator registry for dynamic lookup
INDICATOR_FUNCTIONS = {
    'sma': calculate_sma,
    'ema': calculate_ema,
    'rsi': calculate_rsi,
    'prev': prev,
    'bollinger': calculate_bollinger_bands,
    'macd': calculate_macd,
    'atr': calculate_atr,
    'stochastic': calculate_stochastic
}


if __name__ == "__main__":
    # Example usage with sample data
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    
    # Generate sample price data
    np.random.seed(42)
    close_prices = pd.Series(
        100 + np.cumsum(np.random.randn(100) * 2),
        index=dates,
        name='close'
    )
    
    print("Sample Close Prices (first 10):")
    print(close_prices.head(10))
    print()
    
    # Calculate indicators
    sma_20 = calculate_sma(close_prices, 20)
    print("SMA(20) - first 25 values:")
    print(sma_20.head(25))
    print()
    
    rsi_14 = calculate_rsi(close_prices, 14)
    print("RSI(14) - first 20 values:")
    print(rsi_14.head(20))
    print()
    
    ema_12 = calculate_ema(close_prices, 12)
    print("EMA(12) - first 15 values:")
    print(ema_12.head(15))