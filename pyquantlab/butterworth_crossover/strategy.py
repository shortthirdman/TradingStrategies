import backtrader as bt
import numpy as np

class ButterworthCrossoverStrategy(bt.Strategy):
    params = (
        ('fast_cutoff', 0.15),
        ('slow_cutoff', 0.05),
        ('filter_order', 2),
        ('lookback', 50),
        ('trailing_stop_pct', 0.04),
        ('stop_loss_pct', 0.08),
        ('trend_threshold', 0.001), # Minimum relative difference for entry
        ('printlog', False),
    )

    def __init__(self):
        # Initialize fast and slow Butterworth filters
        self.fast_filter = ButterworthFilter(self.data.close, cutoff_freq=self.params.fast_cutoff, order=self.params.filter_order, lookback=self.params.lookback)
        self.slow_filter = ButterworthFilter(self.data.close, cutoff_freq=self.params.slow_cutoff, order=self.params.filter_order, lookback=self.params.lookback)
        
        # Crossover indicator for signals
        self.crossover = bt.indicators.CrossOver(self.fast_filter, self.slow_filter)
        self.filter_diff = self.fast_filter - self.slow_filter # For trend strength

        self.order = None
        self.trailing_stop_price = None
        self.entry_price = None
        self.last_signal = 0 # To prevent re-entry on same signal

    def next(self):
        if self.order:
            return # Only one order at a time
        current_price = self.data.close[0]
        fast_val = self.fast_filter[0]
        slow_val = self.slow_filter[0]

        # Ensure filters have enough data to be valid
        if len(self) < self.params.lookback * 2 or np.isnan(fast_val) or np.isnan(slow_val):
            return

        # Entry Logic
        if not self.position:
            filter_diff_ratio = (fast_val - slow_val) / abs(slow_val) # Relative difference
            
            # Long signal: Fast filter crosses above slow with sufficient trend strength
            if self.crossover[0] > 0 and filter_diff_ratio > self.params.trend_threshold and self.last_signal != 1:
                self.log(f'BUY CREATE: {current_price:.2f}')
                self.order = self.buy()
                self.last_signal = 1
            # Short signal: Fast filter crosses below slow with sufficient trend strength
            elif self.crossover[0] < 0 and filter_diff_ratio < -self.params.trend_threshold and self.last_signal != -1:
                self.log(f'SELL CREATE: {current_price:.2f}')
                self.order = self.sell()
                self.last_signal = -1
        
        # Exit and Stop-Loss/Trailing-Stop Logic (simplified for conciseness)
        else: # If in a position
            # ... (Full code includes logic for updating trailing_stop_price, and checking
            #     exit conditions based on crossover reversal, trailing stop, and fixed stop loss.)
            pass