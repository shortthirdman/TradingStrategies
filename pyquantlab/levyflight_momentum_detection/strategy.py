class LevyMomentumStrategy:
	"""Brings together the analysis from LevyFlightAnalyzer to make trading decisions."""
	def generate_signals(self, prices):
        # ... (initialization, pct_change) ...
        signals = np.zeros(len(prices))
        # ... (levy_data dictionary for storing analysis outputs) ...
        
        for i in range(self.config.levy_window, len(returns)): # Rolling window
            window_returns = returns.iloc[i-self.config.levy_window:i].values
            
            alpha, beta, gamma, delta = self.analyzer.estimate_levy_parameters(window_returns)
            jumps, jump_magnitudes = self.analyzer.detect_jumps(window_returns, alpha, gamma)
            regime = self.analyzer.identify_regime(window_returns, jumps)
            jump_momentum, diffusion_momentum = self.analyzer.calculate_levy_momentum(
                window_returns, jumps, jump_magnitudes, regime
            )
            
            # Combine signals based on regime
            if regime == 'jump':
                signal = (jump_momentum * self.config.jump_momentum_weight + 
                          diffusion_momentum * self.config.diffusion_momentum_weight)
            else: # diffusion regime
                signal = (diffusion_momentum * self.config.diffusion_momentum_weight + 
                          jump_momentum * self.config.jump_momentum_weight * 0.5) # Jumps have less weight in diffusion
            
            # Apply trend filter (boost signal if aligned with EMA trend)
            trend_prices = prices.iloc[max(0, i-self.config.trend_ema_span):i+1]
            if len(trend_prices) > 5:
                trend_direction = 1 if trend_prices.iloc[-1] > trend_prices.ewm(span=self.config.trend_ema_span).mean().iloc[-1] else -1
                signal *= (1 + 0.3 * trend_direction) 
            
            # Normalize signal by volatility using tanh (to bound between -1 and 1)
            volatility = np.std(window_returns[-self.config.volatility_window:])
            signal = np.tanh(signal / (volatility + 1e-6)) 
            
            signals[i] = signal # Store signal for the current point in time 'i' in the returns array
                                # Note: returns array is 1 shorter than prices array.
                                # This signal corresponds to prices.index[i+1]
        
        # Adjust signals index to align with prices
        # The loop goes up to len(returns)-1. `returns` starts from prices.index[1].
        # So, the last signal signals[len(returns)-1] is for returns.index[len(returns)-1], which is prices.index[len(prices)-1].
        # The signals array should be shifted to align with the price series for trading.
        # Current code creates pd.Series(signals, index=prices.index) -> this makes signals of length prices,
        # but the loop for calculation only fills up to len(returns) which is len(prices)-1.
        # A more robust way to align:
        final_signals = pd.Series(0.0, index=prices.index)
        if len(returns) > 0: # Ensure returns is not empty
             final_signals.iloc[self.config.levy_window+1 : len(returns)+1] = signals[self.config.levy_window : len(returns)]

        # Store analysis data
        if len(levy_data['alpha']) > 0:
            analysis_index_start = self.config.levy_window + 1 # +1 because returns are used
            analysis_index_end = analysis_index_start + len(levy_data['alpha'])
            self.levy_analysis = pd.DataFrame(levy_data, index=prices.index[analysis_index_start:analysis_index_end])

        return final_signals # Return pd.Series aligned with price index
	
	def execute_trades(self, prices, signals, verbose=False):
        # ... (initialization of capital, positions list, trades list, daily_returns list) ...
        
        for i, (date, price) in enumerate(prices.items()):
            # ... (skip first day, calculate daily_return holder, update position_days) ...
            
            # Risk management checks (Stop Loss, Take Profit, Max Hold)
            if self.position != 0 and self.entry_price > 0:
                pnl_pct = (price - self.entry_price) / self.entry_price * self.position
                if self.config.stop_loss and pnl_pct < -self.config.stop_loss:
                    # ... (execute stop loss, update capital with transaction cost) ...
                elif self.config.take_profit and pnl_pct > self.config.take_profit:
                    # ... (execute take profit) ...
                elif self.position_days >= self.config.max_position_hold:
                    # ... (execute max hold exit) ...

            # Trading signals
            if i < len(signals):
                signal_value = signals.iloc[i] # Use signal for current day i
                
                if signal_value > self.config.signal_threshold and self.position <= 0: # Buy
                    # ... (handle existing short, enter long, record trade, apply transaction cost) ...
                elif signal_value < -self.config.signal_threshold and self.position >= 0: # Sell
                    # ... (handle existing long, enter short, record trade, apply transaction cost) ...
            
            # Calculate daily P&L based on holding position
            # ... (calculate P&L if self.position is 1 or -1) ...
            daily_returns.append(daily_return_for_day) # Store actual return for the day based on position
            # Capital update should be based on actual P&L, not just raw daily_return if no position.
            # The current script's capital update: capital *= (1 + daily_return) where daily_return is portfolio return.
        
        return trades, daily_returns_series, capital # daily_returns should be a series