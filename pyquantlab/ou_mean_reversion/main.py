import backtrader as bt
import yfinance as yf

def run_ou_strategy(ticker='EURUSD=X', start_date='2020-01-01', end_date='2024-12-31', 
                    cash=10000, lookback=60, sma_period=30, entry_threshold=1.5, exit_threshold=0.5):
    """
    Run the OU Mean Reversion strategy
    """
    
    print(f"=== OU Mean Reversion Strategy ===")
    print(f"Ticker: {ticker}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Lookback: {lookback} days")
    print(f"Entry Threshold: ±{entry_threshold}")
    print(f"Exit Threshold: ±{exit_threshold}")
    print(f"Initial Cash: ${cash:,.2f}")
    print("=" * 50)
    
    # Download data
    print("Downloading data...")
    data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False).droplevel(1, 1)
    
    if data.empty:
        print(f"No data found for {ticker}")
        return None
    
    # Convert to Backtrader format
    bt_data = bt.feeds.PandasData(dataname=data)
    
    # Create Cerebro engine
    cerebro = bt.Cerebro()
    
    # Add strategy
    cerebro.addstrategy(OUMeanReversionStrategy,
                        lookback=lookback,
                        sma_period=sma_period,
                        entry_threshold=entry_threshold,
                        exit_threshold=exit_threshold,
                        printlog=False)  # Set to True for detailed logs
    
    # Add data
    cerebro.adddata(bt_data)
    
    # Set cash
    cerebro.broker.setcash(cash)
    
    # Add commission (0.1% per trade)
    cerebro.broker.setcommission(commission=0.001)
    
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run strategy
    print("Running strategy...")
    results = cerebro.run()
    strat = results[0]
    
    # Print results
    print("\n=== PERFORMANCE SUMMARY ===")
    
    final_value = cerebro.broker.getvalue()
    total_return = (final_value - cash) / cash * 100
    print(f"Initial Portfolio Value: ${cash:,.2f}")
    print(f"Final Portfolio Value: ${final_value:,.2f}")
    print(f"Total Return: {total_return:.2f}%")
    
    # Get analyzer results
    returns_analysis = strat.analyzers.returns.get_analysis()
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    trades_analysis = strat.analyzers.trades.get_analysis()
    
    print(f"\nAnnualized Return: {returns_analysis.get('rnorm100', 0):.2f}%")
    print(f"Sharpe Ratio: {sharpe_analysis.get('sharperatio', 0):.2f}")
    print(f"Max Drawdown: {drawdown_analysis.get('max', {}).get('drawdown', 0):.2f}%")
    
    if 'total' in trades_analysis:
        total_trades = trades_analysis['total']['total']
        won_trades = trades_analysis['won']['total'] if 'won' in trades_analysis else 0
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        print(f"Total Trades: {total_trades}")
        print(f"Win Rate: {win_rate:.1f}%")
    
    # Plot results
    print("\nGenerating plots...")
    plt.rcParams['figure.figsize'] = [10, 6]
    cerebro.plot(style='candlestick', barup='green', bardown='red', iplot=False)
    
    return cerebro, results


# Example usage
if __name__ == '__main__':
    # Run the strategy
    cerebro, results = run_ou_strategy(
        ticker='ETH-USD',
        start_date='2020-01-01', 
        end_date='2024-12-31',
        cash=10000,
        lookback=30,
        sma_period=30, 
        entry_threshold=1.2,
        exit_threshold=0.8
    )
    
    # You can also test with other assets like stocks or crypto
    cerebro, results = run_ou_strategy(ticker='AAPL', start_date='2020-01-01', end_date='2024-12-31')
    cerebro, results = run_ou_strategy(ticker='BTC-USD', start_date='2020-01-01', end_date='2024-12-31')