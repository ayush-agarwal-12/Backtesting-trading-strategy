"""
Backtest Simulator
Simulates strategy execution and calculates performance metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime


class Backtester:
    """Simple backtest simulator for entry/exit strategies"""
    
    def __init__(self, df, initial_capital=10000):
        """
        Initialize backtester
        
        Args:
            df: DataFrame with OHLCV data
            initial_capital: Starting capital (default 10000)
        """
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.trades = []
        self.equity_curve = []
        self.current_position = None
    
    def run(self, entry_signals, exit_signals):
        """
        Simulate strategy execution over historical data
        
        State machine implementation:
        - States: NO_POSITION, IN_POSITION
        - Transitions:
        * NO_POSITION + entry_signal -> IN_POSITION (buy)
        * IN_POSITION + exit_signal -> NO_POSITION (sell)
        
        Design decision: Entry and exit on same bar
        - Entry uses close price of signal bar
        - Exit uses close price of signal bar
        
        Real-world consideration: This has lookahead bias
        In live trading, you can't know close price until market closes.
        More realistic: Entry at next bar's open price.
        
        Why accepted for this implementation:
        - Simplifies backtest logic significantly
        - Common approach in academic backtests
        - Users can adjust for realism in production
        - Documented in limitations section
        
        Future improvement: Add config option for entry/exit timing
        CONFIG: entry_timing = next_open | same_close
        """
        # Reset state
        self.trades = []
        self.equity_curve = []
        self.current_position = None
        
        equity = self.initial_capital
        peak_equity = self.initial_capital
        max_drawdown = 0.0
        
        # State: 'NO_POSITION' or 'IN_POSITION'
        state = 'NO_POSITION'
        
        for i in range(len(self.df)):
            date = self.df.index[i]
            
            # Skip if signals are NaN (insufficient data for indicators)
            if pd.isna(entry_signals.iloc[i]) or pd.isna(exit_signals.iloc[i]):
                self.equity_curve.append(equity)
                continue
            
            # Entry logic
            if state == 'NO_POSITION' and entry_signals.iloc[i]:
                # Enter position at close price
                entry_price = self.df['close'].iloc[i]
                
                self.current_position = {
                    'entry_date': date,
                    'entry_price': entry_price,
                    'entry_index': i,
                    'shares': equity / entry_price  # Buy with all available capital
                }
                
                state = 'IN_POSITION'
            
            # Exit logic
            elif state == 'IN_POSITION' and exit_signals.iloc[i]:
                # Exit position at close price
                exit_price = self.df['close'].iloc[i]
                
                # Calculate P&L
                shares = self.current_position['shares']
                entry_price = self.current_position['entry_price']
                
                pnl = shares * (exit_price - entry_price)
                pnl_pct = (exit_price - entry_price) / entry_price
                
                equity += pnl
                
                # Record trade
                trade = {
                    'entry_date': self.current_position['entry_date'],
                    'exit_date': date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'shares': shares,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                    'return': pnl_pct * 100  # Percentage
                }
                self.trades.append(trade)
                
                # Reset position
                self.current_position = None
                state = 'NO_POSITION'
            
            # Update equity for position
            elif state == 'IN_POSITION':
                # Mark-to-market equity
                current_price = self.df['close'].iloc[i]
                shares = self.current_position['shares']
                equity = shares * current_price
            
            # Track drawdown
            if equity > peak_equity:
                peak_equity = equity
            
            drawdown = (equity - peak_equity) / peak_equity
            if drawdown < max_drawdown:
                max_drawdown = drawdown
            
            self.equity_curve.append(equity)
        
        # Calculate metrics
        results = self._calculate_metrics(max_drawdown)
        
        return results
    
    def _calculate_metrics(self, max_drawdown):
        """Calculate performance metrics"""
        
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_return': 0.0,
                'total_return_pct': 0.0,
                'max_drawdown': max_drawdown * 100,
                'average_return': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'final_equity': self.initial_capital,
                'trades': []
            }
        
        # Basic counts
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t['pnl'] > 0)
        losing_trades = sum(1 for t in self.trades if t['pnl'] < 0)
        
        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        # Total return
        final_equity = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        total_return = final_equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Average returns
        returns = [t['return'] for t in self.trades]
        average_return = np.mean(returns) if returns else 0.0
        
        winning_returns = [t['return'] for t in self.trades if t['pnl'] > 0]
        losing_returns = [t['return'] for t in self.trades if t['pnl'] < 0]
        
        average_win = np.mean(winning_returns) if winning_returns else 0.0
        average_loss = np.mean(losing_returns) if losing_returns else 0.0
        
        # Profit factor
        total_wins = sum(t['pnl'] for t in self.trades if t['pnl'] > 0)
        total_losses = abs(sum(t['pnl'] for t in self.trades if t['pnl'] < 0))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf')
        
        # Sharpe ratio (simplified - using trade returns)
        if len(returns) > 1:
            sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252 / len(returns))
        else:
            sharpe_ratio = 0.0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'total_return': round(total_return, 2),
            'total_return_pct': round(total_return_pct, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'average_return': round(average_return, 2),
            'average_win': round(average_win, 2),
            'average_loss': round(average_loss, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else float('inf'),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'final_equity': round(final_equity, 2),
            'initial_equity': self.initial_capital,
            'trades': self.trades
        }
    
    def print_results(self, results):
        """Print formatted backtest results"""
        print("="*60)
        print(" BACKTEST RESULTS")
        print("="*60)
        print(f"\nInitial Capital: ${results['initial_equity']:,.2f}")
        print(f"Final Equity:    ${results['final_equity']:,.2f}")
        print(f"Total Return:    ${results['total_return']:,.2f} ({results['total_return_pct']:.2f}%)")
        print(f"Max Drawdown:    {results['max_drawdown']:.2f}%")
        print(f"\nTotal Trades:    {results['total_trades']}")
        print(f"Winning Trades:  {results['winning_trades']}")
        print(f"Losing Trades:   {results['losing_trades']}")
        print(f"Win Rate:        {results['win_rate']:.2f}%")
        print(f"\nAverage Return:  {results['average_return']:.2f}%")
        print(f"Average Win:     {results['average_win']:.2f}%")
        print(f"Average Loss:    {results['average_loss']:.2f}%")
        print(f"Profit Factor:   {results['profit_factor']}")
        print(f"Sharpe Ratio:    {results['sharpe_ratio']}")
        
        if results['trades']:
            print(f"\n{'='*60}")
            print(" TRADE LOG")
            print(f"{'='*60}")
            print(f"{'Entry Date':<12} {'Exit Date':<12} {'Entry $':<10} {'Exit $':<10} {'Return':<10}")
            print("-"*60)
            
            for trade in results['trades']:
                entry_date = trade['entry_date'].strftime('%Y-%m-%d')
                exit_date = trade['exit_date'].strftime('%Y-%m-%d')
                entry_price = f"${trade['entry_price']:.2f}"
                exit_price = f"${trade['exit_price']:.2f}"
                return_pct = f"{trade['return']:.2f}%"
                
                print(f"{entry_date:<12} {exit_date:<12} {entry_price:<10} {exit_price:<10} {return_pct:<10}")
        
        print("="*60)


if __name__ == "__main__":
    # Example usage
    import numpy as np
    
    # Create sample OHLCV data
    np.random.seed(42)
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    
    df = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(100) * 2),
        'high': 100 + np.cumsum(np.random.randn(100) * 2) + 2,
        'low': 100 + np.cumsum(np.random.randn(100) * 2) - 2,
        'close': 100 + np.cumsum(np.random.randn(100) * 2),
        'volume': np.random.randint(500000, 2000000, 100)
    }, index=dates)
    
    # Create simple signals for testing
    entry_signals = pd.Series(False, index=dates)
    exit_signals = pd.Series(False, index=dates)
    
    # Buy on day 10, 40, 70
    entry_signals.iloc[10] = True
    entry_signals.iloc[40] = True
    entry_signals.iloc[70] = True
    
    # Sell on day 20, 50, 80
    exit_signals.iloc[20] = True
    exit_signals.iloc[50] = True
    exit_signals.iloc[80] = True
    
    # Run backtest
    backtester = Backtester(df, initial_capital=10000)
    results = backtester.run(entry_signals, exit_signals)
    
    # Print results
    backtester.print_results(results)