
class VSAPatternRecognition:
	""" """
	 def detect_vsa_patterns(self):
        """Detect key VSA patterns"""
        volume_class = self.classify_volume()
        spread_class = self.classify_spread()
        close_class = self.classify_close_position()
        trend = self.get_trend_direction()
        
        # Track if this is a down bar or up bar
        is_down_bar = self.close[0] < self.open[0]
        is_up_bar = self.close[0] > self.open[0]
        
        # VSA Pattern Detection
        
        # 1. NO DEMAND (Bullish) - High volume, wide spread, closing down but in uptrend
        if (volume_class in ['high', 'climax'] and spread_class == 'wide' and 
            close_class == 'low' and is_down_bar and trend == 'up'):
            return 'no_demand', 3
        
        # 2. NO SUPPLY (Bullish) - High volume, wide spread, closing up after decline
        if (volume_class in ['high', 'climax'] and spread_class == 'wide' and 
            close_class == 'high' and is_up_bar and trend == 'down'):
            return 'no_supply', 3
        
        # 3. STOPPING VOLUME (Bullish) - Very high volume after decline
        if (volume_class == 'climax' and trend == 'down' and 
            is_down_bar and close_class in ['middle', 'high']):
            return 'stopping_volume', 4
        
        # 4. CLIMAX (Bearish) - Very high volume, wide spread, closing up in uptrend
        if (volume_class == 'climax' and spread_class == 'wide' and 
            close_class == 'high' and is_up_bar and trend == 'up'):
            return 'climax', 4
        
        # 5. WEAKNESS (Bearish) - High volume, narrow spread, closing down
        if (volume_class == 'high' and spread_class == 'narrow' and 
            close_class == 'low' and is_down_bar):
            return 'weakness', 2
        
        # 6. STRENGTH (Bullish) - High volume, narrow spread, closing up
        if (volume_class == 'high' and spread_class == 'narrow' and 
            close_class == 'high' and is_up_bar):
            return 'strength', 2
        
        # 7. TEST (Context dependent) - Low volume retest of previous levels
        if volume_class == 'low':
            # Test of support (Bullish if holds)
            if (trend == 'down' and close_class in ['middle', 'high'] and 
                not is_down_bar):
                return 'test_support', 2
            # Test of resistance (Bearish if rejected)
            elif (trend == 'up' and close_class in ['middle', 'low'] and 
                  not is_up_bar):
                return 'test_resistance', 2
        
        # 8. EFFORT TO MOVE UP (Bearish) - High volume but narrow spread up
        if (volume_class == 'high' and spread_class == 'narrow' and 
            is_up_bar and trend == 'up'):
            return 'effort_up', 1
        
        # 9. EFFORT TO MOVE DOWN (Bullish) - High volume but narrow spread down
        if (volume_class == 'high' and spread_class == 'narrow' and 
            is_down_bar and trend == 'down'):
            return 'effort_down', 1
        
        return None, 0
	
	def check_background_context(self):
        """Check previous bars for context"""
        # Look at previous 3 bars for context
        context_score = 0
        
        for i in range(1, 4):
            if len(self.data) <= i:
                continue
            
            prev_volume = self.volume[-i]
            prev_spread = self.spread[-i]
            prev_close_pos = self.close_position[-i]
            
            # Add context scoring logic here
            # This is simplified - in practice, you'd analyze the story
            if prev_volume > self.volume_ma[-i]:
                context_score += 1
        
        return context_score

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy() and self.position.size > 0:
                # Long position opened - set initial trailing stop
                self.entry_price = order.executed.price
                self.trail_stop_price = order.executed.price * (1 - self.params.trail_stop_pct)
                self.stop_order = self.sell(exectype=bt.Order.Stop, price=self.trail_stop_price)
            elif order.issell() and self.position.size < 0:
                # Short position opened - set initial trailing stop
                self.entry_price = order.executed.price
                self.trail_stop_price = order.executed.price * (1 + self.params.trail_stop_pct)
                self.stop_order = self.buy(exectype=bt.Order.Stop, price=self.trail_stop_price)
        
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            if hasattr(order, 'ref') and hasattr(self.order, 'ref') and order.ref == self.order.ref:
                self.order = None
            elif order is self.order:
                self.order = None
            
            if hasattr(order, 'ref') and hasattr(self.stop_order, 'ref') and order.ref == self.stop_order.ref:
                self.stop_order = None
                # Reset trailing stop tracking when stop order is filled
                if order.status == order.Completed:
                    self.trail_stop_price = 0
                    self.entry_price = 0
            elif order is self.stop_order:
                self.stop_order = None
                # Reset trailing stop tracking when stop order is filled
                if order.status == order.Completed:
                    self.trail_stop_price = 0
                    self.entry_price = 0
	
	def next(self):
        if self.order is not None:
            return
        
        # Update trailing stop if we have a position
        if self.position and self.trail_stop_price > 0:
            current_price = self.close[0]
            
            if self.position.size > 0:  # Long position
                # Calculate new trailing stop (move up only)
                new_trail_stop = current_price * (1 - self.params.trail_stop_pct)
                
                if new_trail_stop > self.trail_stop_price:
                    # Cancel old stop order
                    if self.stop_order is not None:
                        self.cancel(self.stop_order)
                        self.stop_order = None
                    
                    # Update trailing stop price
                    self.trail_stop_price = new_trail_stop
                    
                    # Place new stop order
                    self.stop_order = self.sell(exectype=bt.Order.Stop, price=self.trail_stop_price)
            
            elif self.position.size < 0:  # Short position
                # Calculate new trailing stop (move down only)
                new_trail_stop = current_price * (1 + self.params.trail_stop_pct)
                
                if new_trail_stop < self.trail_stop_price:
                    # Cancel old stop order
                    if self.stop_order is not None:
                        self.cancel(self.stop_order)
                        self.stop_order = None
                    
                    # Update trailing stop price
                    self.trail_stop_price = new_trail_stop
                    
                    # Place new stop order
                    self.stop_order = self.buy(exectype=bt.Order.Stop, price=self.trail_stop_price)
        
        # Skip if not enough data for indicators to warm up
        if len(self.data) < max(self.params.volume_period, self.params.spread_period):
            return
        
        # Detect VSA patterns
        pattern, strength = self.detect_vsa_patterns()
        
        if pattern is None or strength < 2:
            return
        
        # Get background context
        context = self.check_background_context()
        total_strength = strength + context
        
        # Minimum strength threshold for trading
        if total_strength < 3:
            return
        
        # Prevent multiple signals too close together
        if len(self.data) - self.last_signal_bar < 5:
            return
        
        # Trading logic based on VSA patterns
        
        # BULLISH SIGNALS
        if pattern in ['no_demand', 'no_supply', 'stopping_volume', 'strength', 
                       'test_support', 'effort_down']:
            
            if self.position.size < 0:  # Close short position
                if self.stop_order is not None:
                    self.cancel(self.stop_order)
                self.order = self.close()
                self.last_signal_bar = len(self.data)
                # Reset trailing stop tracking
                self.trail_stop_price = 0
                self.entry_price = 0
            elif not self.position:  # Open long position
                # Only take high-confidence signals
                if total_strength >= 4 or pattern in ['stopping_volume', 'no_supply']:
                    self.order = self.buy()
                    self.last_signal_bar = len(self.data)
        
        # BEARISH SIGNALS
        elif pattern in ['climax', 'weakness', 'test_resistance', 'effort_up']:
            
            if self.position.size > 0:  # Close long position
                if self.stop_order is not None:
                    self.cancel(self.stop_order)
                self.order = self.close()
                self.last_signal_bar = len(self.data)
                # Reset trailing stop tracking
                self.trail_stop_price = 0
                self.entry_price = 0
            elif not self.position:  # Open short position
                # Only take high-confidence signals
                if total_strength >= 4 or pattern in ['climax', 'weakness']:
                    self.order = self.sell()
                    self.last_signal_bar = len(self.data)