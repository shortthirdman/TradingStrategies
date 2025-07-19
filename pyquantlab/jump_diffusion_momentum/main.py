def run_jump_diffusion_strategy():
    print("Downloading data for ETH-USD...")
    data = yf.download('ETH-USD', period='3y', auto_adjust=False).droplevel(1, axis=1) # Applying saved instruction
    
    cerebro = bt.Cerebro()
    cerebro.addstrategy(JumpDiffusionMomentumStrategy, ...) # Add strategy with parameters
    cerebro.adddata(bt.feeds.PandasData(dataname=data))
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)
    
    # Add various analyzers for comprehensive metrics
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')
    
    starting_value = cerebro.broker.getvalue()
    print(f'Starting Value: ${starting_value:,.2f}')
    results = cerebro.run()
    final_value = cerebro.broker.getvalue()
    
    # ... (Print detailed performance summary including total return, trade stats,
    #      risk metrics, and Buy & Hold comparison.)
    
    # Plot results
    plt.rcParams['figure.figsize'] = [12, 8]
    cerebro.plot(style='line', iplot=False, figsize=(12, 6))[0][0]
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    run_jump_diffusion_strategy()