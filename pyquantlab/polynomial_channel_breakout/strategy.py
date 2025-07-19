import backtrader as bt
import backtrader.indicators as btind # Used for ATR
import numpy as np
# Import PolynomialChannelIndicator here or ensure it's defined above
from pyquantlab.polynomial_channel_breakout import PolynomialChannelIndicator

class PolynomialChannelBreakoutStrategy(bt.Strategy):
    params = (
        ('degree', 3),             # Polynomial degree for the channel
        ('channel_width', 2.0),    # Channel width in standard deviations
        ('lookback', 30),          # Lookback period for polynomial regression
        ('trail_atr_mult', 3.0),   # ATR multiple for trailing stop
        ('atr_period', 14),        # ATR period for trailing stop
        ('use_regression_exit', False), # Option to exit on regression line cross
        ('printlog', True),        # Enable/disable logging
    )
    
    def __init__(self):
        self.dataclose = self.datas[0].close
        
        # Instantiate our custom Polynomial Channel Indicator
        self.poly_channel = PolynomialChannelIndicator(
            self.datas[0], # Pass the data feed to the indicator
            degree=self.params.degree,
            channel_width=self.params.channel_width,
            lookback=self.params.lookback
        )
        
        # ATR for trailing stops
        self.atr = btind.ATR(period=self.params.atr_period)
        
        # Trailing stop variables
        self.trail_stop = None       # The current price level of the trailing stop
        self.entry_price = None      # Price at which the current position was entered
        self.position_type = 0       # 0: no position, 1: long, -1: short
        self.order = None            # To track active entry/exit orders
        
        # Counters for logging strategy activity
        self.signal_count = 0
        self.long_signals = 0
        self.short_signals = 0
        self.exit_signals = 0        # Exits from regression line
        self.trail_exits = 0         # Exits from trailing stop hit
            
    def log(self, txt, dt=None):
        """Logging function for strategy actions."""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}: {txt}')
            
    def notify_order(self, order):
        """Handles order notifications and sets initial trailing stop."""
        if order.status in [order.Submitted, order.Accepted]:
            return # Order is pending, nothing to do yet
            
        if order.status in [order.Completed]:
            if order.isbuy(): # A buy order has completed (either entry long or cover short)
                self.log(f'BUY EXECUTED: Price: {order.executed.price:.2f}, '
                         f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                # If we are now in a long position, set initial trailing stop
                if self.position.size > 0:
                    self.position_type = 1
                    self.entry_price = order.executed.price
                    # Calculate initial trailing stop
                    self.trail_stop = self.entry_price - (self.atr[0] * self.params.trail_atr_mult)
                    self.log(f'INITIAL LONG STOP set at: {self.trail_stop:.2f}')
                    
            elif order.issell(): # A sell order has completed (either entry short or exit long)
                self.log(f'SELL EXECUTED: Price: {order.executed.price:.2f}, '
                         f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                # If we are now in a short position, set initial trailing stop
                if self.position.size < 0: # This means it was an opening short position
                    self.position_type = -1
                    self.entry_price = order.executed.price
                    # Calculate initial trailing stop
                    self.trail_stop = self.entry_price + (self.atr[0] * self.params.trail_atr_mult)
                    self.log(f'INITIAL SHORT STOP set at: {self.trail_stop:.2f}')
                else: # This means it was a closing order for a long position
                    self.position_type = 0 # Position closed
                    self.trail_stop = None # Reset trailing stop tracking
                    self.entry_price = None
                    
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'Order Failed: Status {order.getstatusname()}')
            # Reset order reference if it failed
            
        self.order = None # Clear general order reference after processing

    def notify_trade(self, trade):
        """Handle trade notifications (when a position is fully closed)."""
        if not trade.isclosed:
            return # Only interested in closed trades
            
        self.log(f'TRADE CLOSED: Gross P&L: {trade.pnl:.2f}, Net P&L: {trade.pnlcomm:.2f}')
        # Reset position type and trailing stop after trade closure
        self.position_type = 0
        self.trail_stop = None
        self.entry_price = None
            
    def update_trailing_stop(self, current_price):
        """Dynamically updates the ATR-based trailing stop."""
        if self.trail_stop is None or self.position_type == 0:
            return # No active position or stop
            
        # Ensure ATR has a valid value
        if np.isnan(self.atr[0]):
            return
            
        stop_distance = self.atr[0] * self.params.trail_atr_mult
            
        if self.position_type == 1: # Long position
            new_stop = current_price - stop_distance
            # Trail stop up with price, never down (only raise the stop)
            if new_stop > self.trail_stop:
                old_stop = self.trail_stop
                self.trail_stop = new_stop
                # Log only if the stop moved significantly
                if abs(new_stop - old_stop) / old_stop > 0.005: # > 0.5% move
                    self.log(f'LONG STOP UPDATED: {old_stop:.2f} -> {new_stop:.2f}')
                    
        elif self.position_type == -1: # Short position
            new_stop = current_price + stop_distance
            # Trail stop down with price, never up (only lower the stop)
            if new_stop < self.trail_stop:
                old_stop = self.trail_stop
                self.trail_stop = new_stop
                # Log only if the stop moved significantly
                if abs(new_stop - old_stop) / old_stop > 0.005: # > 0.5% move
                    self.log(f'SHORT STOP UPDATED: {old_stop:.2f} -> {new_stop:.2f}')
            
    def next(self):
        """Main strategy logic executed on each bar."""
        
        # 1. Skip if indicators not ready or pending order
        # Ensure enough data for PolynomialChannelIndicator and ATR
        min_indicator_period = max(self.params.lookback, self.params.atr_period)
        if len(self) < min_indicator_period + 1: # +1 for current bar's close
            return
            
        if self.order: # Prevent new orders if one is already pending
            return
            
        # Check for NaN values from indicators
        if (np.isnan(self.poly_channel.upper_channel[0]) or 
            np.isnan(self.poly_channel.lower_channel[0]) or 
            np.isnan(self.poly_channel.regression_line[0]) or
            np.isnan(self.atr[0])):
            self.log("Indicators not ready (NaN values). Waiting for more data.")
            return
            
        current_price = self.dataclose[0]
        # Get previous prices and indicator values for crossover checks
        prev_price = self.dataclose[-1]
        upper_channel = self.poly_channel.upper_channel[0]
        lower_channel = self.poly_channel.lower_channel[0]
        regression_line = self.poly_channel.regression_line[0]
        
        prev_upper = self.poly_channel.upper_channel[-1]
        prev_lower = self.poly_channel.lower_channel[-1]
        prev_regression = self.poly_channel.regression_line[-1]
        
        # 2. Handle existing positions (Trailing Stop & Optional Regression Exit)
        if self.position:
            # Update trailing stop (this just updates the price, doesn't place order)
            self.update_trailing_stop(current_price)
            
            # Check if trailing stop has been hit (current price crosses the trail_stop)
            # For backtrader, this logic is usually handled by the actual stop order
            # but here we manage it manually for clear logging and control.
            if self.position_type == 1: # Long position
                if current_price <= self.trail_stop:
                    self.trail_exits += 1
                    self.log(f'LONG TRAILING STOP HIT: Price {current_price:.2f} <= Stop {self.trail_stop:.2f}')
                    self.order = self.close() # Close the position
                    return # Exit after placing close order
                    
            elif self.position_type == -1: # Short position
                if current_price >= self.trail_stop:
                    self.trail_exits += 1
                    self.log(f'SHORT TRAILING STOP HIT: Price {current_price:.2f} >= Stop {self.trail_stop:.2f}')
                    self.order = self.close() # Close the position
                    return # Exit after placing close order
                    
            # Optional: Exit if price crosses the regression line
            if self.params.use_regression_exit:
                # Exit long if price breaks below regression line
                if (self.position_type == 1 and 
                    current_price < regression_line and 
                    prev_price >= prev_regression): # Crossover check
                    
                    self.exit_signals += 1
                    self.log(f'LONG REGRESSION EXIT: Price {current_price:.2f} < Regression {regression_line:.2f}')
                    self.order = self.close()
                    return
                    
                # Exit short if price breaks above regression line
                elif (self.position_type == -1 and 
                      current_price > regression_line and 
                      prev_price <= prev_regression): # Crossover check
                    
                    self.exit_signals += 1
                    self.log(f'SHORT REGRESSION EXIT: Price {current_price:.2f} > Regression {regression_line:.2f}')
                    self.order = self.close()
                    return
        
        # 3. Entry Logic - only if currently no position
        else:
            # Long signal: Current price breaks above upper channel, and prev price was below or at upper channel
            if (current_price > upper_channel and 
                prev_price <= prev_upper):
                
                self.signal_count += 1
                self.long_signals += 1
                self.log(f'LONG ENTRY SIGNAL #{self.signal_count}: Price {current_price:.2f} > Upper Channel {upper_channel:.2f}')
                self.order = self.buy() # Place buy order
                    
            # Short signal: Current price breaks below lower channel, and prev price was above or at lower channel
            elif (current_price < lower_channel and 
                  prev_price >= prev_lower):
                
                self.signal_count += 1
                self.short_signals += 1
                self.log(f'SHORT ENTRY SIGNAL #{self.signal_count}: Price {current_price:.2f} < Lower Channel {lower_channel:.2f}')
                self.order = self.sell() # Place sell (short) order
                
    def stop(self):
        """Called at the very end of the backtest to provide a summary."""
        self.log(f'\n=== STRATEGY SUMMARY ===')
        self.log(f'Total Entry Signals Generated: {self.signal_count}')
        self.log(f'Total Long Entry Signals: {self.long_signals}')
        self.log(f'Total Short Entry Signals: {self.short_signals}')
        self.log(f'Total Trailing Stop Exits: {self.trail_exits}')
        if self.params.use_regression_exit:
            self.log(f'Total Regression Line Exits: {self.exit_signals}')
        self.log(f'Final Portfolio Value: ${self.broker.getvalue():,.2f}')