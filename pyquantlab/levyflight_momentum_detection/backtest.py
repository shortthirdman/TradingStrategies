class LevyWalkForwardBacktest:
	"""Orchestrates the walk-forward backtesting process."""
	# ... (__init__, get_data) ...
    
    def run_backtest(self, start_date=None, end_date=None):
        # ... (date handling) ...
        while current_date < end_date - timedelta(days=self.config.test_period):
            # Define train and test periods
            train_start = current_date
            train_end = current_date + timedelta(days=self.config.train_period)
            test_start = train_end
            test_end = train_end + timedelta(days=self.config.test_period)
            # ... (break if test_end > end_date) ...
            
            train_data = self.get_data(train_start, train_end) # Prices for training (parameter estimation)
            test_data = self.get_data(test_start, test_end)   # Prices for testing (trading)
            # ... (data validation) ...
            
            result = self.run_strategy_period(train_data, test_data, iteration)
            # ... (store result, increment current_date) ...
        return self.compile_results()

    def run_strategy_period(self, train_data, test_data, iteration):
        try:
            strategy = LevyMomentumStrategy(self.config)
            
            # Generate signals: Use part of train_data for history/warm-up for signals on test_data
            # This ensures the signal generation has enough historical context for the start of test_data
            combined_data = pd.concat([train_data.tail(self.config.levy_window), test_data])
            signals_on_combined = strategy.generate_signals(combined_data)
            # Extract signals relevant only to the test_data period
            test_signals = signals_on_combined.tail(len(test_data)) 
            
            trades, daily_returns, final_capital = strategy.execute_trades(test_data, test_signals)
            # ... (calculate metrics for this period and return) ...
        # ... (error handling) ...

    def compile_results(self):
        # ... (aggregates results from all walk-forward periods) ...
        
    def plot_results(self):
        # ... (plots various performance charts based on compiled results) ...