import backtrader as bt
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, time

class VWAPAnchoredBreakoutStrategy(bt.Strategy):
    '''
    Volume Weighted Average Price (VWAP) Anchored Breakout Strategy
    '''
    # Parameters for the strategy
    params = (
        # VWAP Parameters
        ('vwap_session_length', 7),    # Session length for VWAP calculation
        ('vwap_weekly_length', 28),    # Weekly VWAP length
        
        # Breakout Parameters
        ('breakout_lookback', 7),      # Lookback period for prior high/low
        ('adx_threshold', 25),         # ADX > 20 for trend confirmation
        ('adx_period', 7),             # ADX calculation period
        
        # Volume and ATR Confirmation
        ('volume_multiplier', 1.1),    # Volume > 1.5x average
        ('volume_period', 7),          # Volume average period
        ('atr_period', 14),            # ATR period
        ('atr_expansion_threshold', 1.1), # ATR expansion threshold
        ('atr_expansion_period', 7),   # Period to compare ATR expansion
        
        # Trailing Stop Parameters
        ('trailing_stop_atr_multiplier', 5.0), # Trailing stop distance
        ('initial_stop_atr_multiplier', 1.),  # Initial stop loss
        
        # Risk Management
        ('position_size_pct', 0.95),   # Position size percentage
        ('printlog', True),
    )

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        self.order = None # To keep track of pending orders
        
        # Technical Indicators
        self.atr = bt.indicators.ATR(period=self.params.atr_period)
        self.adx = bt.indicators.ADx(period=self.params.adx_period) # Note: Backtrader's ADX is ADX by default. Using ADx to be explicit.
        
        # VWAP Calculations
        # Session VWAP (shorter term)
        typical_price = (self.datahigh + self.datalow + self.dataclose) / 3
        self.vwap_session = bt.indicators.WeightedAverage(
            typical_price, self.datavolume, 
            period=self.params.vwap_session_length
        )
        
        # Weekly VWAP (longer term)
        self.vwap_weekly = bt.indicators.WeightedAverage(
            typical_price, self.datavolume, 
            period=self.params.vwap_weekly_length
        )
        
        # Volume indicators
        self.volume_sma = bt.indicators.SMA(self.datavolume, period=self.params.volume_period)
        
        # ATR expansion detection
        self.atr_sma = bt.indicators.SMA(self.atr, period=self.params.atr_expansion_period)
        
        # Prior session high/low tracking
        self.prior_high = bt.indicators.Highest(self.datahigh, period=self.params.breakout_lookback)
        self.prior_low = bt.indicators.Lowest(self.datalow, period=self.params.breakout_lookback)
        
        # Tracking variables for current trade
        self.entry_price = None
        self.stop_price = None
        self.trail_price = None
        self.position_type = None  # 1 for long, -1 for short
        self.breakout_confirmed = False
	
	def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()} - {txt}')
	
	def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return # Order submitted/accepted - nothing to do yet

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, Cost: {order.executed.value:.2f}')

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None # Clear pending order
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return # Trade is not yet closed

        self.log(f'TRADE CLOSED - P&L: {trade.pnlcomm:.2f}')
	
	def check_vwap_alignment(self, breakout_direction):
        """Check if current price vs VWAP supports the breakout direction"""
        if len(self.vwap_session) < 1 or len(self.vwap_weekly) < 1:
            return False
            
        current_price = self.dataclose[0]
        session_vwap = self.vwap_session[0]
        weekly_vwap = self.vwap_weekly[0]
        
        if breakout_direction == "LONG":
            # For long breakouts, price should be above both VWAPs (or at least session VWAP)
            return current_price > session_vwap # A stricter check could be current_price > weekly_vwap as well
        elif breakout_direction == "SHORT":
            # For short breakouts, price should be below both VWAPs (or at least session VWAP)
            return current_price < session_vwap # A stricter check could be current_price < weekly_vwap as well
            
        return False

    def check_volume_confirmation(self):
        """Check if volume > 1.1x average"""
        if len(self.datavolume) < 1 or len(self.volume_sma) < 1:
            return False
            
        current_volume = self.datavolume[0]
        avg_volume = self.volume_sma[0]
        
        return current_volume > (avg_volume * self.params.volume_multiplier)

    def check_atr_expansion(self):
        """Check if ATR is expanding (current ATR > recent average)"""
        if len(self.atr) < 1 or len(self.atr_sma) < 1:
            return False
            
        current_atr = self.atr[0]
        avg_atr = self.atr_sma[0]
        
        return current_atr > (avg_atr * self.params.atr_expansion_threshold)

    def check_breakout_conditions(self):
        """Check for breakout setup conditions"""
        if len(self.dataclose) < self.params.breakout_lookback:
            return False, None
            
        current_price = self.dataclose[0]
        current_high = self.datahigh[0]
        current_low = self.datalow[0]
        
        # Get prior session high/low (from yesterday, not including today)
        prior_session_high = self.prior_high[-1]  # Previous bar's highest
        prior_session_low = self.prior_low[-1]    # Previous bar's lowest
        
        breakout_direction = None
        
        # Check for breakout of prior high
        if current_high > prior_session_high:
            breakout_direction = "LONG"
            self.log(f'HIGH BREAKOUT DETECTED: Current High {current_high:.2f} > Prior High {prior_session_high:.2f}')
            
        # Check for breakout of prior low
        elif current_low < prior_session_low:
            breakout_direction = "SHORT"
            self.log(f'LOW BREAKOUT DETECTED: Current Low {current_low:.2f} < Prior Low {prior_session_low:.2f}')
            
        if breakout_direction is None:
            return False, None
            
        # Check VWAP alignment
        if not self.check_vwap_alignment(breakout_direction):
            self.log(f'VWAP ALIGNMENT FAILED for {breakout_direction}')
            return False, None
            
        # Check ADX > threshold
        if len(self.adx) < 1 or self.adx[0] <= self.params.adx_threshold:
            self.log(f'ADX TOO LOW: {self.adx[0]:.1f} <= {self.params.adx_threshold}')
            return False, None
            
        # Check volume confirmation
        if not self.check_volume_confirmation():
            self.log(f'VOLUME CONFIRMATION FAILED: {self.datavolume[0]} vs {self.volume_sma[0] * self.params.volume_multiplier:.0f}')
            return False, None
            
        # Check ATR expansion
        if not self.check_atr_expansion():
            self.log(f'ATR EXPANSION FAILED: {self.atr[0]:.4f} vs {self.atr_sma[0] * self.params.atr_expansion_threshold:.4f}')
            return False, None
            
        return True, breakout_direction
    
    def update_trailing_stop(self):
        """Update trailing stop based on ATR"""
        if not self.position or self.trail_price is None:
            return
            
        current_price = self.dataclose[0]
        atr_value = self.atr[0]
        trail_distance = self.params.trailing_stop_atr_multiplier * atr_value
        
        if self.position_type == 1:  # Long position
            new_trail = current_price - trail_distance
            if new_trail > self.trail_price: # Move stop up if price moves favorably
                self.trail_price = new_trail
                self.log(f'TRAIL UPDATED (Long): New trail stop at {self.trail_price:.2f}')
                
        elif self.position_type == -1:  # Short position
            new_trail = current_price + trail_distance
            if new_trail < self.trail_price: # Move stop down if price moves favorably
                self.trail_price = new_trail
                self.log(f'TRAIL UPDATED (Short): New trail stop at {self.trail_price:.2f}')

    def check_exit_conditions(self):
        """Check for exit conditions"""
        if not self.position:
            return False, None
            
        current_price = self.dataclose[0]
        
        # Check initial stop loss
        if self.stop_price is not None:
            if self.position_type == 1 and current_price <= self.stop_price:
                return True, "STOP_LOSS"
            elif self.position_type == -1 and current_price >= self.stop_price:
                return True, "STOP_LOSS"
                
        # Check trailing stop
        if self.trail_price is not None:
            if self.position_type == 1 and current_price <= self.trail_price:
                return True, "TRAILING_STOP"
            elif self.position_type == -1 and current_price >= self.trail_price:
                return True, "TRAILING_STOP"
                
        # Check VWAP mean reversion (optional exit condition)
        if len(self.vwap_session) >= 1:
            session_vwap = self.vwap_session[0]
            if self.position_type == 1 and current_price < session_vwap: # Price falls below session VWAP for long
                return True, "VWAP_REVERSION"
            elif self.position_type == -1 and current_price > session_vwap: # Price rises above session VWAP for short
                return True, "VWAP_REVERSION"
                
        return False, None

    def calculate_position_size(self):
        """Position sizing handled by PercentSizer"""
        return None  # Not used - PercentSizer handles this
    
    def next(self):
        if self.order:
            return # A pending order exists, do nothing

        # Skip if not enough data for all indicators to calculate
        required_data = max(
            self.params.breakout_lookback,
            self.params.vwap_session_length,
            self.params.adx_period,
            self.params.atr_period,
            self.params.volume_period, # Ensure volume_period is included here for correct indexing
            self.params.atr_expansion_period # Ensure atr_expansion_period is included here for correct indexing
        )
        # Added a check for sufficient bars available for all indicators to be calculated
        if len(self.dataclose) < required_data + max(
            self.params.vwap_session_length,
            self.params.vwap_weekly_length,
            self.params.adx_period,
            self.params.atr_period,
            self.params.volume_period,
            self.params.atr_expansion_period,
            self.params.breakout_lookback # Ensure this is also included for prior_high/low
        ):
            return

        current_price = self.dataclose[0]

        # 1. If in position, manage it (update stop, check exits)
        if self.position:
            self.update_trailing_stop()
            
            should_exit, exit_reason = self.check_exit_conditions()
            if should_exit:
                self.log(f'EXIT SIGNAL ({exit_reason}): Closing position at {current_price:.2f}')
                self.order = self.close()
                # Reset tracking variables
                self.entry_price = None
                self.stop_price = None
                self.trail_price = None
                self.position_type = None
                self.breakout_confirmed = False
            return # Do not look for new entries if already in position

        # 2. If not in position, look for entry signals
        if not self.position:
            breakout_valid, direction = self.check_breakout_conditions()
            
            if breakout_valid and direction:
                atr_value = self.atr[0]
                
                if direction == "LONG":
                    # Enter long position
                    self.log(f'VWAP BREAKOUT LONG SETUP:')
                    self.log(f'  Price: {current_price:.2f}, Session VWAP: {self.vwap_session[0]:.2f}')
                    self.log(f'  ADX: {self.adx[0]:.1f}, Volume: {self.datavolume[0]:.0f} (Avg: {self.volume_sma[0]:.0f})')
                    self.log(f'  ATR: {self.atr[0]:.4f} (Avg: {self.atr_sma[0]:.4f})')
                    
                    # Calculate stops
                    self.stop_price = current_price - (self.params.initial_stop_atr_multiplier * atr_value)
                    self.trail_price = current_price - (self.params.trailing_stop_atr_multiplier * atr_value)
                    
                    self.log(f'LONG ENTRY: Stop={self.stop_price:.2f}, Trail={self.trail_price:.2f}')
                    self.order = self.buy()
                    self.entry_price = current_price
                    self.position_type = 1
                    self.breakout_confirmed = True
                    
                elif direction == "SHORT":
                    # Enter short position
                    self.log(f'VWAP BREAKOUT SHORT SETUP:')
                    self.log(f'  Price: {current_price:.2f}, Session VWAP: {self.vwap_session[0]:.2f}')
                    self.log(f'  ADX: {self.adx[0]:.1f}, Volume: {self.datavolume[0]:.0f} (Avg: {self.volume_sma[0]:.0f})')
                    self.log(f'  ATR: {self.atr[0]:.4f} (Avg: {self.atr_sma[0]:.4f})')
                    
                    # Calculate stops
                    self.stop_price = current_price + (self.params.initial_stop_atr_multiplier * atr_value)
                    self.trail_price = current_price + (self.params.trailing_stop_atr_multiplier * atr_value)
                    
                    self.log(f'SHORT ENTRY: Stop={self.stop_price:.2f}, Trail={self.trail_price:.2f}')
                    self.order = self.sell()
                    self.entry_price = current_price
                    self.position_type = -1
                    self.breakout_confirmed = True