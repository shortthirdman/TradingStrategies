import numpy as np
import backtrader as bt

class VSAStrategy(bt.Strategy):
    params = (
        ('volume_period', 7),       # Period for volume averages
        ('volume_threshold', 1.2),  # High volume threshold (e.g., 1.2x average)
        ('spread_period', 7),       # Period for spread averages
        ('spread_threshold', 1.2),  # Wide spread threshold (e.g., 1.2x average)
        ('trend_period', 30),       # Trend determination period for SMA
        ('climax_volume_mult', 2.0),# Climax volume multiplier (e.g., 2.0x average)
        ('test_volume_mult', 0.5),  # Test volume multiplier (e.g., 0.5x average for low volume)
        ('trail_stop_pct', 0.05),   # 5% trailing stop loss
    )
    
    def __init__(self):
        # Price data feeds
        self.high = self.data.high
        self.low = self.data.low
        self.close = self.data.close
        self.open = self.data.open
        self.volume = self.data.volume
        
        # VSA raw components: spread and close position within range
        self.spread = self.high - self.low  # True range of the bar
        # Calculate where the close is within the bar's range (0 = low, 1 = high)
        self.close_position = bt.If(self.spread != 0, (self.close - self.low) / self.spread, 0.5) 
        
        # Moving averages for comparison
        self.volume_ma = bt.indicators.SMA(self.volume, period=self.params.volume_period)
        self.spread_ma = bt.indicators.SMA(self.spread, period=self.params.spread_period)
        
        # Trend determination using a simple moving average
        self.trend_ma = bt.indicators.SMA(self.close, period=self.params.trend_period)
        
        # VSA signal tracking (for internal use)
        self.vsa_signal = 0        # Placeholder for detected signal type (e.g., bullish/bearish)
        self.signal_strength = 0   # Strength of the detected signal
        self.last_signal_bar = 0   # Bar index of the last signal, to prevent too frequent trades
        
        # Trailing stop tracking variables
        self.trail_stop_price = 0  # Current price level of the trailing stop
        self.entry_price = 0       # Price at which the current position was entered
        
        # Backtrader order tracking
        self.order = None          # Stores reference to the current entry/exit order
        self.stop_order = None     # Stores reference to the current trailing stop order

    def log(self, txt, dt=None):
        ''' Logging function for strategy actions '''
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()} - {txt}')

    def classify_volume(self):
        """Classify current bar's volume relative to its moving average"""
        # Ensure indicator has enough data and MA is not zero to prevent errors
        if np.isnan(self.volume_ma[0]) or self.volume_ma[0] == 0 or self.volume[0] == 0:
            return 'normal'
            
        volume_ratio = self.volume[0] / self.volume_ma[0]
        
        if volume_ratio >= self.params.climax_volume_mult:
            return 'climax' # Extremely high volume, potential exhaustion
        elif volume_ratio >= self.params.volume_threshold:
            return 'high'   # Higher than average volume
        elif volume_ratio <= self.params.test_volume_mult:
            return 'low'    # Very low volume, often indicates a test of supply/demand
        else:
            return 'normal' # Average volume

    def classify_spread(self):
        """Classify current bar's spread (range) relative to its moving average"""
        # Ensure indicator has enough data and MA is not zero
        if np.isnan(self.spread_ma[0]) or self.spread_ma[0] == 0 or self.spread[0] == 0:
            return 'normal'
            
        spread_ratio = self.spread[0] / self.spread_ma[0]
        
        if spread_ratio >= self.params.spread_threshold:
            return 'wide'   # Wide range bar, strong momentum or reversal
        elif spread_ratio <= (1 / self.params.spread_threshold): # Inverse threshold for narrow (e.g., 1/1.2 = ~0.83)
            return 'narrow' # Narrow range bar, indecision or lack of interest
        else:
            return 'normal' # Average range bar

    def classify_close_position(self):
        """Classify where the closing price is within the bar's range"""
        if self.spread[0] == 0: # If high == low, it's a flat bar, close is effectively middle
            return 'middle'
            
        close_pos = self.close_position[0] # Already calculated in __init__
        
        if close_pos >= 0.7:
            return 'high'   # Close near the high of the bar, strong buying
        elif close_pos <= 0.3:
            return 'low'    # Close near the low of the bar, strong selling
        else:
            return 'middle' # Close in the middle of the bar, indecision

    def get_trend_direction(self):
        """Determine current trend direction based on closing price relative to trend MA"""
        # Ensure trend MA has enough data
        if np.isnan(self.trend_ma[0]):
            return 'sideways'
            
        if self.close[0] > self.trend_ma[0]:
            return 'up'     # Close above MA, potential uptrend
        elif self.close[0] < self.trend_ma[0]:
            return 'down'   # Close below MA, potential downtrend
        else:
            return 'sideways' # Close at MA, no clear trend

    def detect_vsa_patterns(self):
        """Detect key VSA patterns based on volume, spread, close position, and trend"""
        volume_class = self.classify_volume()
        spread_class = self.classify_spread()
        close_class = self.classify_close_position()
        trend = self.get_trend_direction()
        
        # Check if current bar is an up bar (close > open) or down bar (close < open)
        is_up_bar = self.close[0] > self.open[0]
        is_down_bar = self.close[0] < self.open[0]
        
        # Pattern definitions with associated base strength score
        # (Pattern Name, Strength Score, Bullish/Bearish)
        
        # BULLISH PATTERNS
        # 1. Stopping Volume (Potential reversal from downtrend)
        if (volume_class == 'climax' and spread_class == 'wide' and trend == 'down' and
            is_down_bar and close_class in ['middle', 'high']):
            self.log(f"VSA Pattern: Stopping Volume (Bullish)", dt=self.data.datetime.date(0))
            return 'stopping_volume', 4, 'bullish'
        
        # 2. No Supply (Low volume test of support in uptrend)
        if (volume_class == 'low' and spread_class == 'narrow' and trend == 'up' and
            is_down_bar and close_class == 'high'): # Low volume down bar, closing high
            self.log(f"VSA Pattern: No Supply (Bullish)", dt=self.data.datetime.date(0))
            return 'no_supply', 3, 'bullish'

        # 3. Strength (Confirmation of buying, often after accumulation)
        if (volume_class == 'high' and spread_class == 'narrow' and trend == 'up' and
            is_up_bar and close_class == 'high'): # High volume, narrow spread, closing high
            self.log(f"VSA Pattern: Strength (Bullish)", dt=self.data.datetime.date(0))
            return 'strength', 2, 'bullish'
            
        # 4. Effort to Move Up (Low result for high effort implies absorption)
        if (volume_class == 'high' and spread_class == 'narrow' and trend == 'down' and
            is_up_bar and close_class in ['middle', 'low']): # High volume up, but closing low/middle
            self.log(f"VSA Pattern: Effort to Move Up (Bullish Reversal)", dt=self.data.datetime.date(0))
            return 'effort_up_reverse', 3, 'bullish' # Renamed for clarity vs. bearish 'effort up'
            
        # BEARISH PATTERNS
        # 5. Climax (Potential reversal from uptrend)
        if (volume_class == 'climax' and spread_class == 'wide' and trend == 'up' and
            is_up_bar and close_class in ['middle', 'low']):
            self.log(f"VSA Pattern: Climax (Bearish)", dt=self.data.datetime.date(0))
            return 'climax_sell', 4, 'bearish' # Renamed for clarity

        # 6. No Demand (Low volume test of resistance in downtrend)
        if (volume_class == 'low' and spread_class == 'narrow' and trend == 'down' and
            is_up_bar and close_class == 'low'): # Low volume up bar, closing low
            self.log(f"VSA Pattern: No Demand (Bearish)", dt=self.data.datetime.date(0))
            return 'no_demand', 3, 'bearish'
            
        # 7. Weakness (Confirmation of selling, often after distribution)
        if (volume_class == 'high' and spread_class == 'narrow' and trend == 'down' and
            is_down_bar and close_class == 'low'): # High volume, narrow spread, closing low
            self.log(f"VSA Pattern: Weakness (Bearish)", dt=self.data.datetime.date(0))
            return 'weakness', 2, 'bearish'
            
        # 8. Effort to Move Down (Low result for high effort implies buying absorption)
        if (volume_class == 'high' and spread_class == 'narrow' and trend == 'up' and
            is_down_bar and close_class in ['middle', 'high']): # High volume down, but closing high/middle
            self.log(f"VSA Pattern: Effort to Move Down (Bearish Reversal)", dt=self.data.datetime.date(0))
            return 'effort_down_reverse', 3, 'bearish' # Renamed for clarity

        # Neutral or less defined patterns
        return None, 0, 'neutral'

    def check_background_context(self):
        """
        Analyzes recent past bars to provide context for current VSA signals.
        This is a simplified example. A full VSA context analysis is complex.
        """
        context_score = 0
        
        # Look at the last few bars (e.g., 3-5 bars)
        for i in range(1, min(len(self.data), 6)): # Check up to 5 prior bars
            # Example: Check for high volume on down bars in an uptrend (potential weakness)
            # or low volume on up bars in a downtrend (potential lack of demand)
            
            # Simplified check for general activity/trend alignment
            prev_volume_ma = bt.indicators.SMA(self.volume, period=self.params.volume_period)(ago=-i)
            prev_spread_ma = bt.indicators.SMA(self.spread, period=self.params.spread_period)(ago=-i)
            prev_trend_ma = bt.indicators.SMA(self.close, period=self.params.trend_period)(ago=-i)

            if not np.isnan(prev_volume_ma) and prev_volume_ma > 0 and self.volume[-i] / prev_volume_ma > 1.5:
                 context_score += 0.5 # High volume in recent past
            
            if not np.isnan(prev_trend_ma):
                if self.close[-i] > prev_trend_ma and self.close[0] > self.trend_ma[0]: # Consistent uptrend
                    context_score += 0.5
                elif self.close[-i] < prev_trend_ma and self.close[0] < self.trend_ma[0]: # Consistent downtrend
                    context_score += 0.5

        return context_score

    def notify_order(self, order):
        # Log completed orders
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size:.2f}')
                # If a new long position is opened, set initial trailing stop
                if self.position.size > 0: # Check if we actually hold a position now
                    self.entry_price = order.executed.price
                    self.trail_stop_price = self.entry_price * (1 - self.params.trail_stop_pct)
                    self.stop_order = self.sell(exectype=bt.Order.Stop, price=self.trail_stop_price, size=self.position.size)
                    self.log(f'Long Trailing Stop set at {self.trail_stop_price:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Size: {order.executed.size:.2f}')
                # If a new short position is opened, set initial trailing stop
                if self.position.size < 0: # Check if we actually hold a short position now
                    self.entry_price = order.executed.price
                    self.trail_stop_price = self.entry_price * (1 + self.params.trail_stop_pct)
                    self.stop_order = self.buy(exectype=bt.Order.Stop, price=self.trail_stop_price, size=abs(self.position.size))
                    self.log(f'Short Trailing Stop set at {self.trail_stop_price:.2f}')
            
            # Clear the entry order reference after completion
            if self.order and order.ref == self.order.ref:
                self.order = None
            
        # Handle canceled/rejected orders
        elif order.status in [order.Canceled, order.Rejected, order.Margin]:
            self.log(f'Order {order.getstatusname()} for {order.size} shares.')
            # Clear the entry order reference if it failed
            if self.order and order.ref == self.order.ref:
                self.order = None
            # If a stop order failed, log a warning and clear its reference
            if self.stop_order and order.ref == self.stop_order.ref:
                self.log("WARNING: Trailing Stop Order failed!", doprint=True)
                self.stop_order = None
                # Consider what to do if trailing stop fails - for simplicity, we let next bar handle it

        # Special handling for stop orders filling (when a position is exited)
        if order.status == order.Completed and self.stop_order and order.ref == self.stop_order.ref:
            self.log(f'Trailing Stop Hit! Price: {order.executed.price:.2f}')
            self.stop_order = None
            self.trail_stop_price = 0 # Reset trailing stop tracking
            self.entry_price = 0      # Reset entry price

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log(f'TRADE P/L: GROSS {trade.pnl:.2f}, NET {trade.pnlcomm:.2f}')


    def next(self):
        # Prevent new orders if an entry order is already pending
        if self.order is not None:
            return
        
        # Ensure sufficient data for all indicators to be calculated
        # The longest period is trend_period (30) or volume/spread period (7)
        min_bars_needed = max(self.params.trend_period, self.params.volume_period, self.params.spread_period)
        if len(self.data) < min_bars_needed + 1: # +1 because indicators operate on current bar and look back
            return

        current_price = self.close[0]

        # --- Trailing Stop Management ---
        if self.position.size > 0:  # Long position
            # Update current highest price
            if current_price > self.entry_price and self.trail_stop_price > 0: # Ensure price is above entry for profit and stop is active
                new_trail_stop = current_price * (1 - self.params.trail_stop_pct)
                if new_trail_stop > self.trail_stop_price: # Move stop up only
                    self.log(f'Updating long trailing stop from {self.trail_stop_price:.2f} to {new_trail_stop:.2f}')
                    if self.stop_order and self.stop_order.alive(): # Cancel old stop order if it exists and is still active
                        self.cancel(self.stop_order)
                    self.trail_stop_price = new_trail_stop
                    self.stop_order = self.sell(exectype=bt.Order.Stop, price=self.trail_stop_price, size=self.position.size)
            # If price falls below the current trailing stop, let the stop order fire (managed in notify_order)

        elif self.position.size < 0: # Short position
            # Update current lowest price
            if current_price < self.entry_price and self.trail_stop_price > 0: # Ensure price is below entry for profit and stop is active
                new_trail_stop = current_price * (1 + self.params.trail_stop_pct)
                if new_trail_stop < self.trail_stop_price: # Move stop down only
                    self.log(f'Updating short trailing stop from {self.trail_stop_price:.2f} to {new_trail_stop:.2f}')
                    if self.stop_order and self.stop_order.alive(): # Cancel old stop order if it exists and is still active
                        self.cancel(self.stop_order)
                    self.trail_stop_price = new_trail_stop
                    self.stop_order = self.buy(exectype=bt.Order.Stop, price=self.trail_stop_price, size=abs(self.position.size))
            # If price rises above the current trailing stop, let the stop order fire (managed in notify_order)

        # --- VSA Signal Detection and Trading Logic ---
        
        # Get VSA pattern and its properties for the current bar
        pattern, strength, direction = self.detect_vsa_patterns()
        
        # If no significant pattern or strength is too low, return
        if pattern is None or strength < 2: # Only consider patterns with a base strength of 2 or more
            return

        # Get background context score
        context_score = self.check_background_context()
        total_strength = strength + context_score
        
        # Minimum total strength threshold for opening new trades
        if total_strength < 3: # Require a combined strength for entry
            return
            
        # Prevent trading too frequently based on consecutive signals (e.g., within 5 bars)
        if len(self.data) - self.last_signal_bar < 5:
            return

        # Handle existing positions based on new signals
        if self.position:
            if self.position.size > 0 and direction == 'bearish': # Long position, but bearish VSA signal
                self.log(f'BEARISH VSA Signal ({pattern}) while LONG. Closing position.')
                if self.stop_order is not None and self.stop_order.alive(): # Cancel any pending stop order
                    self.cancel(self.stop_order)
                self.order = self.close() # Close the long position
                self.last_signal_bar = len(self.data)
                self.trail_stop_price = 0 # Reset trailing stop tracking
                self.entry_price = 0
            elif self.position.size < 0 and direction == 'bullish': # Short position, but bullish VSA signal
                self.log(f'BULLISH VSA Signal ({pattern}) while SHORT. Closing position.')
                if self.stop_order is not None and self.stop_order.alive(): # Cancel any pending stop order
                    self.cancel(self.stop_order)
                self.order = self.close() # Close the short position
                self.last_signal_bar = len(self.data)
                self.trail_stop_price = 0 # Reset trailing stop tracking
                self.entry_price = 0
        
        # Open new positions if currently flat
        else:
            # BULLISH SIGNALS for NEW LONG
            if direction == 'bullish':
                # Further refine entry based on higher confidence signals or overall strength
                if total_strength >= 4 or pattern in ['stopping_volume', 'no_supply']: # Prioritize stronger/key reversal patterns
                    self.log(f'Executing BUY based on VSA pattern: {pattern} (Strength: {total_strength:.1f}) at Close={current_price:.2f}')
                    self.order = self.buy() # Execute buy order (sizer will determine amount)
                    self.last_signal_bar = len(self.data)
            
            # BEARISH SIGNALS for NEW SHORT
            elif direction == 'bearish':
                # Further refine entry based on higher confidence signals or overall strength
                if total_strength >= 4 or pattern in ['climax_sell', 'weakness', 'no_demand']: # Prioritize stronger/key reversal patterns
                    self.log(f'Executing SELL based on VSA pattern: {pattern} (Strength: {total_strength:.1f}) at Close={current_price:.2f}')
                    self.order = self.sell() # Execute sell (short) order
                    self.last_signal_bar = len(self.data)