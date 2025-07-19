def run_rolling_backtest(
    ticker="BTC-USD",
    start="2018-01-01",
    end="2025-12-31", # This will be overridden by current_date in __main__
    window_months=3,
    strategy_params=None
):
    strategy_params = strategy_params or {}
    all_results = []
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    current_start = start_dt

    while True:
        current_end = current_start + rd.relativedelta(months=window_months)
        if current_end > end_dt:
            current_end = end_dt # Ensure last window doesn't go past overall end
            if current_start >= current_end: # No valid period left
                break

        print(f"\nROLLING BACKTEST: {current_start.date()} to {current_end.date()}")

        # Data download using yfinance, adhering to saved preferences
        # Using the saved preference: yfinance download with auto_adjust=False and droplevel(axis=1, level=1)
        data = yf.download(ticker, start=current_start, end=current_end, auto_adjust=False, progress=False)
        
        # Apply droplevel if data is a MultiIndex, as per user's preference
        if isinstance(data.columns, pd.MultiIndex):
            data = data.droplevel(1, axis=1)

        # Check for sufficient data after droplevel for strategy warm-up
        # Get actual strategy parameters for min_bars_needed calculation if overridden
        vol_period = strategy_params.get('volume_period', VSAStrategy.params.volume_period)
        spread_period = strategy_params.get('spread_period', VSAStrategy.params.spread_period)
        trend_period = strategy_params.get('trend_period', VSAStrategy.params.trend_period)

        min_bars_needed = max(vol_period, spread_period, trend_period) + 1 
        
        if data.empty or len(data) < min_bars_needed:
            print(f"Not enough data for period {current_start.date()} to {current_end.date()} (requires at least {min_bars_needed} bars). Skipping.")
            if current_end == end_dt:
                break
            current_start = current_end # Advance to the next window
            continue

        feed = bt.feeds.PandasData(dataname=data)
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy, **strategy_params)
        cerebro.adddata(feed)
        cerebro.broker.setcash(100000)
        cerebro.broker.setcommission(commission=0.001)
        cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

        start_val = cerebro.broker.getvalue()
        cerebro.run()
        final_val = cerebro.broker.getvalue()
        ret = (final_val - start_val) / start_val * 100

        all_results.append({
            'start': current_start.date(),
            'end': current_end.date(),
            'return_pct': ret,
            'final_value': final_val,
        })

        print(f"Return: {ret:.2f}% | Final Value: {final_val:.2f}")
        
        # Move to the next window. If current_end already reached overall end_dt, then break.
        if current_end == end_dt:
            break
        current_start = current_end # For non-overlapping windows, next start is current end

    return pd.DataFrame(all_results)

def report_stats(df):
    returns = df['return_pct']
    stats = {
        'Mean Return %': np.mean(returns),
        'Median Return %': np.median(returns),
        'Std Dev %': np.std(returns),
        'Min Return %': np.min(returns),
        'Max Return %': np.max(returns),
        'Sharpe Ratio': np.mean(returns) / np.std(returns) if np.std(returns) > 0 else np.nan
    }
    print("\n=== ROLLING BACKTEST STATISTICS ===")
    for k, v in stats.items():
        print(f"{k}: {v:.2f}")
    return stats

def plot_four_charts(df, rolling_sharpe_window=4):
    """
    Generates four analytical plots for rolling backtest results.
    """
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8)) # Adjusted figsize for clarity
    
    # Calculate period numbers (0, 1, 2, 3, ...)
    periods = list(range(len(df)))
    returns = df['return_pct']
    
    # 1. Period Returns (Top Left)
    colors = ['green' if r >= 0 else 'red' for r in returns]
    ax1.bar(periods, returns, color=colors, alpha=0.7)
    ax1.set_title('Period Returns', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Period')
    ax1.set_ylabel('Return %')
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax1.grid(True, alpha=0.3)
    
    # 2. Cumulative Returns (Top Right)
    cumulative_returns = (1 + returns / 100).cumprod() * 100 - 100
    ax2.plot(periods, cumulative_returns, marker='o', linewidth=2, markersize=4, color='blue') # Smaller markers
    ax2.set_title('Cumulative Returns', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Period')
    ax2.set_ylabel('Cumulative Return %')
    ax2.grid(True, alpha=0.3)
    
    # 3. Rolling Sharpe Ratio (Bottom Left)
    rolling_sharpe = returns.rolling(window=rolling_sharpe_window).apply(
        lambda x: x.mean() / x.std() if x.std() > 0 else np.nan, raw=False # Added raw=False for lambda
    )
    # Only plot where we have valid rolling calculations
    valid_mask = ~rolling_sharpe.isna()
    valid_periods = [i for i, valid in enumerate(valid_mask) if valid]
    valid_sharpe = rolling_sharpe[valid_mask]
    
    ax3.plot(valid_periods, valid_sharpe, marker='o', linewidth=2, markersize=4, color='orange') # Smaller markers
    ax3.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax3.set_title(f'Rolling Sharpe Ratio ({rolling_sharpe_window}-period)', fontsize=14, fontweight='bold')
    ax3.set_xlabel('Period')
    ax3.set_ylabel('Sharpe Ratio')
    ax3.grid(True, alpha=0.3)
    
    # 4. Return Distribution (Bottom Right)
    bins = min(15, max(5, len(returns)//2))
    ax4.hist(returns, bins=bins, alpha=0.7, color='steelblue', edgecolor='black')
    mean_return = returns.mean()
    ax4.axvline(mean_return, color='red', linestyle='--', linewidth=2, 
                label=f'Mean: {mean_return:.2f}%')
    ax4.set_title('Return Distribution', fontsize=14, fontweight='bold')
    ax4.set_xlabel('Return %')
    ax4.set_ylabel('Frequency')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    # Using the current date for the end of the backtest for live testing.
    # The current time is Saturday, June 21, 2025 at 12:49:01 AM CEST.
    current_date = pd.to_datetime('2025-06-21').date() 
    
    # Running with default parameters (BTC-USD, 3-month windows)
    # You can uncomment and modify the parameters below to test other configurations
    df = run_rolling_backtest(
        ticker="BTC-USD",
        start="2018-01-01",
        end=current_date, # Use the current date
        window_months=3,
      
    )

    print("\n=== ROLLING BACKTEST RESULTS ===")
    print(df)

    stats = report_stats(df)
    plot_four_charts(df)