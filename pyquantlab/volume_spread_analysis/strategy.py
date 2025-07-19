import backtrader as bt
import numpy as np

class VSAStrategy(bt.Strategy):
    params = (
        ('volume_period', 7),        # Period for volume averages
        ('volume_threshold', 1.2),   # High volume threshold (1.2x average)
        ('spread_period', 7),        # Period for spread averages
        ('spread_threshold', 1.2),   # Wide spread threshold (1.2x average)
        ('trend_period', 30),        # Trend determination period
        ('climax_volume_mult', 2.0), # Climax volume multiplier
        ('test_volume_mult', 0.5),   # Test volume multiplier (low volume)
        ('trail_stop_pct', 0.05),    # Trailing stop loss percentage
    )
    
    def __init__(self):
        # Price data references
        self.high = self.data.high
        self.low = self.data.low
        self.close = self.data.close
        self.open = self.data.open
        self.volume = self.data.volume
        
        # VSA components calculations
        self.spread = self.high - self.low  # Calculate the bar's range

        # Calculate where the close sits within the range (0=low, 1=high)
        self.close_position = (self.close - self.low) / (self.high - self.low)
        
        # Moving averages for comparison
        self.volume_ma = bt.indicators.SMA(self.volume, period=self.params.volume_period)
        self.spread_ma = bt.indicators.SMA(self.spread, period=self.params.spread_period)
        
        # Trend determination using a simple SMA
        self.trend_ma = bt.indicators.SMA(self.close, period=self.params.trend_period)
        
        # Internal variables to track VSA signal state
        self.vsa_signal = 0
        self.signal_strength = 0
        self.last_signal_bar = 0
        
        # Trailing stop tracking variables
        self.trail_stop_price = 0
        self.entry_price = 0
        
        # backtrader's order tracking variables
        self.order = None
        self.stop_order = None

    def classify_volume(self):
        """Classify current volume as high, normal, or low relative to its average."""
        if np.isnan(self.volume_ma[0]) or self.volume_ma[0] == 0:
            return 'normal' # Default if MA isn't ready
        
        volume_ratio = self.volume[0] / self.volume_ma[0]
        
        if volume_ratio >= self.params.climax_volume_mult:
            return 'climax' # Very high volume
        elif volume_ratio >= self.params.volume_threshold:
            return 'high'   # Above average
        elif volume_ratio <= self.params.test_volume_mult:
            return 'low'    # Below average
        else:
            return 'normal'

    def classify_spread(self):
        """Classify current bar's spread (range) as wide, normal, or narrow relative to its average."""
        if np.isnan(self.spread_ma[0]) or self.spread_ma[0] == 0:
            return 'normal' # Default if MA isn't ready
        
        spread_ratio = self.spread[0] / self.spread_ma[0]
        
        if spread_ratio >= self.params.spread_threshold:
            return 'wide'   # Large range
        # This condition classifies a "narrow" spread. If spread_threshold is 1.2,
        # then (2 - 1.2) = 0.8. So, a spread less than 80% of average is "narrow."
        elif spread_ratio <= (2 - self.params.spread_threshold):
            return 'narrow' # Small range
        else:
            return 'normal'

    def classify_close_position(self):
        """Classify where the close is within the bar's range (low, middle, high)."""
        if self.spread[0] == 0: # If the bar has no range (e.g., open=high=low=close)
            return 'middle'
        
        close_pos = self.close_position[0] # Value between 0 (low) and 1 (high)
        
        if close_pos >= 0.7:
            return 'high'   # Close is in the top 30%
        elif close_pos <= 0.3:
            return 'low'    # Close is in the bottom 30%
        else:
            return 'middle' # Close is in the middle 40%

    def get_trend_direction(self):
        """Determines the current trend direction based on a simple moving average."""
        if self.close[0] > self.trend_ma[0]:
            return 'up'
        elif self.close[0] < self.trend_ma[0]:
            return 'down'
        else:
            return 'sideways'