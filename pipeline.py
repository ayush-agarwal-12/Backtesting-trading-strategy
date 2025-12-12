"""
End-to-End Pipeline Orchestrator
Integrates all components: NL -> JSON -> DSL -> AST -> Code -> Backtest

Architecture Decision: Multi-stage pipeline
-------------------------------------------
Could do NL -> Code directly, but stages provide:
1. Debugging: See intermediate representations
2. Modularity: Test each stage independently  
3. Transparency: Users can see and modify DSL
4. Flexibility: Skip stages (e.g., start from DSL)

Trade-off: More complexity, but better maintainability
"""

import json
import pandas as pd
from nl_parser import NLParser
from dsl_converter import JSONToDSL
from dsl_parser import DSLParser
from code_generator import CodeGenerator
from backtest import Backtester
import yfinance as yf


class TradingStrategyPipeline:
    """End-to-end pipeline for trading strategy execution"""
    
    def __init__(self, groq_api_key=None):
        """
        Initialize pipeline components
        
        Args:
            groq_api_key: Groq API key (optional, will use env var if not provided)
        """
        self.nl_parser = NLParser(api_key=groq_api_key)
        self.json_to_dsl = JSONToDSL()
        self.dsl_parser = DSLParser()
        self.code_generator = CodeGenerator()
    
    def _normalize_dataframe(self, df):
        """
        Normalize DataFrame column names to lowercase
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with lowercase column names
        """
        df = df.copy()
        
        # Mapping of possible column names to standard lowercase names
        column_mapping = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close',
            'Dividends': 'dividends',
            'Stock Splits': 'stock_splits'
        }
        
        # Rename columns that exist in the mapping
        df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)
        
        # Also lowercase any remaining columns
        df.columns = [col.lower() if isinstance(col, str) else col for col in df.columns]
        
        return df
    
    def run(self, natural_language_input, df, initial_capital=10000, verbose=True):
        """
        Run complete pipeline from natural language to backtest results
        
        Args:
            natural_language_input: String with trading rules in natural language
            df: DataFrame with OHLCV data
            initial_capital: Starting capital for backtest
            verbose: Print intermediate steps
            
        Returns:
            dict: Complete results including all intermediate representations
        """
        # Normalize DataFrame columns
        df = self._normalize_dataframe(df)
        
        results = {
            'nl_input': natural_language_input,
            'json_ir': None,
            'dsl_text': None,
            'ast': None,
            'backtest_results': None
        }
        
        try:
            # Step 1: Natural Language → JSON
            if verbose:
                print("="*70)
                print("STEP 1: Natural Language → JSON")
                print("="*70)
                print(f"Input: {natural_language_input}\n")
            
            json_ir = self.nl_parser.parse(natural_language_input)
            results['json_ir'] = json_ir
            
            if verbose:
                print("Generated JSON:")
                print(json.dumps(json_ir, indent=2))
                print()
            
            # Step 2: JSON → DSL
            if verbose:
                print("="*70)
                print("STEP 2: JSON → DSL Text")
                print("="*70)
            
            dsl_text = self.json_to_dsl.convert(json_ir)
            results['dsl_text'] = dsl_text
            
            if verbose:
                print("Generated DSL:")
                print(dsl_text)
                print()
            
            # Step 3: DSL → AST
            if verbose:
                print("="*70)
                print("STEP 3: DSL → Abstract Syntax Tree (AST)")
                print("="*70)
            
            ast = self.dsl_parser.parse(dsl_text)
            results['ast'] = ast
            
            if verbose:
                print("Generated AST:")
                print(json.dumps(ast, indent=2))
                print()
            
            # Step 4: AST → Python Code
            if verbose:
                print("="*70)
                print("STEP 4: AST → Python Code Generation")
                print("="*70)
            
            strategy_function = self.code_generator.generate(ast)
            
            if verbose:
                print("Strategy function generated successfully")
                print(f"Indicators to compute: {list(self.code_generator.indicator_cache.keys())}")
                print()
            
            # Step 5: Execute Strategy
            if verbose:
                print("="*70)
                print("STEP 5: Execute Strategy on Data")
                print("="*70)
                print(f"Data shape: {df.shape}")
                print(f"Date range: {df.index[0]} to {df.index[-1]}")
                print(f"Columns: {list(df.columns)}")
                print()
            
            entry_signals, exit_signals = strategy_function(df)
            
            if verbose:
                print(f"Entry signals generated: {entry_signals.sum()} entries")
                print(f"Exit signals generated: {exit_signals.sum()} exits")
                print()
            
            # Step 6: Run Backtest
            if verbose:
                print("="*70)
                print("STEP 6: Run Backtest Simulation")
                print("="*70)
            
            backtester = Backtester(df, initial_capital=initial_capital)
            backtest_results = backtester.run(entry_signals, exit_signals)
            results['backtest_results'] = backtest_results
            
            if verbose:
                print()
                backtester.print_results(backtest_results)
            
            return results
            
        except Exception as e:
            print(f"\n Pipeline failed: {str(e)}")
            raise
    
    def run_from_dsl(self, dsl_text, df, initial_capital=10000, verbose=True,
                    chart_prefix='strategy'):
        """
        Run pipeline starting from DSL (skip NL parsing)
        
        Args:
            dsl_text: DSL text string
            df: DataFrame with OHLCV data
            initial_capital: Starting capital
            verbose: Print steps
            chart_prefix: Prefix for saved chart filename
            
        Returns:
            dict: Results
            
        Use case: When you want deterministic results
        ----------------------------------------------
        NL parsing via LLM has slight non-determinism. For reproducible
        backtests, start from DSL directly.
        
        Also useful for:
        - Unit testing (DSL is easier to construct than NL)
        - Programmatic strategy generation
        - When you already have DSL from another source
        
        Visualization:
        --------------
        Always generates and saves equity curve chart automatically.
        """
        # Normalize DataFrame columns
        df = self._normalize_dataframe(df)
        
        results = {
            'dsl_text': dsl_text,
            'ast': None,
            'backtest_results': None
        }
        
        try:
            # Parse DSL
            if verbose:
                print("="*70)
                print("Parsing DSL")
                print("="*70)
                print(dsl_text)
                print()
            
            ast = self.dsl_parser.parse(dsl_text)
            results['ast'] = ast
            
            # Generate code
            if verbose:
                print("="*70)
                print("Generating Code")
                print("="*70)
            
            strategy_function = self.code_generator.generate(ast)
            
            if verbose:
                print(f"Indicators: {list(self.code_generator.indicator_cache.keys())}")
                print()
            
            # Execute
            entry_signals, exit_signals = strategy_function(df)
            
            if verbose:
                print(f"Entries: {entry_signals.sum()}, Exits: {exit_signals.sum()}")
                print()
            
            # Backtest
            backtester = Backtester(df, initial_capital=initial_capital)
            backtest_results = backtester.run(entry_signals, exit_signals)
            results['backtest_results'] = backtest_results
            
            if verbose:
                backtester.print_results(backtest_results)
            
            return results
            
        except Exception as e:
            print(f"\n Pipeline failed: {str(e)}")
            raise


def load_sample_data(start_date="2015-01-01", end_date="2025-01-01"):
    """
    Load OHLCV data from yfinance with fixed date range for determinism
    
    Args:
        start_date: Start date for historical data
        end_date: End date for historical data
        
    Returns:
        DataFrame with OHLCV data
        
    Determinism consideration:
    --------------------------
    Using period="max" fetches data up to "today", which changes daily.
    Fixed date range ensures reproducible backtests.
    
    Why yfinance:
    - Free, no API key required
    - Good data quality for major stocks
    - Easy to use for examples
    
    Production consideration:
    For real trading, use professional data provider:
    - Alpha Vantage, Polygon.io, etc.
    - Better data quality
    - More reliable
    - Survivorship bias adjustment
    """
    df = yf.Ticker("AAPL").history(start=start_date, end=end_date)
    return df


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize pipeline
    print("Initializing Trading Strategy Pipeline...")
    print()
    
    # Check for API key
    if not os.getenv('GROQ_API_KEY'):
        print("GROQ_API_KEY not found in environment variables")
        print("Please set it with: export GROQ_API_KEY='your-key-here'")
        print()
    
    try:
        pipeline = TradingStrategyPipeline()
        
        # Load data
        print("Loading sample data...")
        df = load_sample_data()
        print(f"Loaded {len(df)} days of OHLCV data")
        print(f"Original columns: {list(df.columns)}")
        print()
        
        # Example 1
        nl_input1 = "Enter when price crosses above yesterday's high. Exit when RSI(14) is below 30."
        # Some other examples to try out
        # Enter when price crosses above yesterday's high. Exit when RSI(14) is below 30.
        # Enter when price breaks above the 20-day high.Exit when price breaks below the 10-day low.

        print("\n")
        print("EXAMPLE 1")
        print("\n")
        
        results1 = pipeline.run(nl_input1, df, initial_capital=10000, verbose=True)
        
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()