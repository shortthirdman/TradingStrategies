
def run_rolling_backtest(
    ticker="BTC-USD",
    start="2018-01-01",
    end="2025-12-31",
    window_months=3,
    strategy_params=None
):
    """
    Runs a backtest on sequential, non-overlapping time windows.
    """
    strategy_params = strategy_params or {}
    all_results = []
    start_dt = pd.to_datetime(start)
    end_dt = pd.to_datetime(end)
    current_start = start_dt

    while True:
        # Define the end of the current window
        current_end = current_start + rd.relativedelta(months=window_months)
        if current_end > end_dt:
            break

        print(f"\nROLLING BACKTEST: {current_start.date()} to {current_end.date()}")

        # Download data for the current window
        data = yf.download(ticker, start=current_start, end=current_end, progress=False)
        if data.empty or len(data) < 90: # Ensure sufficient data
            print("Not enough data.")
            current_start += rd.relativedelta(months=window_months)
            continue

        if isinstance(data.columns, pd.MultiIndex):
            data = data.droplevel(1, 1)

        # Set up and run a standard backtrader backtest for the window
        feed = bt.feeds.PandasData(dataname=data)
        cerebro = bt.Cerebro()
        cerebro.addstrategy(AdaptiveKalmanFilterStrategy, **strategy_params)
        cerebro.adddata(feed)
        cerebro.broker.setcash(100000)
        cerebro.broker.setcommission(commission=0.001)
        cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

        start_val = cerebro.broker.getvalue()
        cerebro.run()
        final_val = cerebro.broker.getvalue()
        ret = (final_val - start_val) / start_val * 100

        # Store the result of this window's backtest
        all_results.append({
            'start': current_start.date(),
            'end': current_end.date(),
            'return_pct': ret,
        })

        print(f"Return: {ret:.2f}% | Final Value: {final_val:.2f}")
        
        # Move the window forward
        current_start += rd.relativedelta(months=window_months)

    return pd.DataFrame(all_results)

def report_stats(df):
    """
    Calculates and prints key performance statistics from the rolling results.
    """
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


def plot_return_distribution(df):
    """
    Creates a histogram to visualize the distribution of returns.
    """
    sns.set(style="whitegrid")
    plt.figure(figsize=(10, 5))
    sns.histplot(df['return_pct'], bins=20, kde=True, color='dodgerblue')
    plt.axvline(df['return_pct'].mean(), color='black', linestyle='--', label='Mean')
    plt.title('Rolling Backtest Return Distribution')
    plt.xlabel('Return %')
    plt.ylabel('Frequency')
    plt.legend()
    plt.tight_layout()
    plt.show()
    
if __name__ == '__main__':
    # Run the rolling backtest with default settings
    # (3-month windows for BTC-USD from 2018 to present)
    df = run_rolling_backtest()

    # Print the results table
    print("\n=== ROLLING BACKTEST RESULTS ===")
    print(df)

    # Calculate and print summary statistics
    stats = report_stats(df)
    
    # Visualize the return distribution
    plot_return_distribution(df)