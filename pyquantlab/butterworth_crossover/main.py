def run_butterworth_strategy():
    print("Downloading BTC-USD data...")
    # Using saved instruction: yfinance download with auto_adjust=False and droplevel(axis=1, level=1).
    data = yf.download('BTC-USD', period='3y', auto_adjust=False).droplevel(1, axis=1)
    
    cerebro = bt.Cerebro()
    cerebro.addstrategy(ButterworthCrossoverStrategy,
                        fast_cutoff=0.1, slow_cutoff=0.02, filter_order=3, lookback=30,
                        trailing_stop_pct=0.05, stop_loss_pct=0.1, trend_threshold=0.001, printlog=True)
    cerebro.adddata(bt.feeds.PandasData(dataname=data))
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
    
    # Add analyzers for performance evaluation
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')
    results = cerebro.run()
    strat = results[0]
    print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')
    # ... (code to print detailed analysis results and plot)