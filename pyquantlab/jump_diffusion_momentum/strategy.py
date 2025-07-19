class JumpDiffusionMomentumStrategy(bt.Strategy):
    params = (
        ('jump_threshold', 2.0), ('min_jump_size', 0.05), # Jump detection sensitivity
        ('momentum_threshold', 0.7), # Strength required for momentum confirmation
        ('diffusion_weight', 0.5),   # How much diffusion trend matters
        ('hold_periods', 7),         # Minimum time to hold position
        ('min_adx_level', 20),       # Minimum ADX for trade
        ('require_adx_rising', True), ('require_atr_rising', True), # Filter conditions
        ('trailing_stop_pct', 0.05), ('stop_loss_pct', 0.1), # Risk Management
        ('printlog', False),
    )

    def __init__(self):
        self.jump_detector = JumpDiffusionDetector(...) # Initialize with params
        self.momentum_detector = MomentumAfterJump(...) # Initialize with params
        self.trend_vol_filter = TrendVolatilityFilter(...) # Initialize with params

    def next(self):
        # ... (Fetch indicator values and check for data validity)

        # Entry signals (if no position)
        if not self.position:
            # Filter condition: ADX & ATR must show sustained rising trend/volatility
            trend_vol_filters_passed = ( (not self.params.require_adx_rising) or bool(self.trend_vol_filter.adx_rising[0])) and \
                                       ( (not self.params.require_atr_rising) or bool(self.trend_vol_filter.atr_rising[0]))

            # Long entry logic: Strong positive jump + momentum/diffusion + filter confirmation
            if (self.jump_detector.jump_signal[0] > 0.8 and # A clear positive jump
                (self.momentum_detector.momentum_direction[0] > 0 or self.jump_detector.diffusion_trend[0] * self.params.diffusion_weight > 0.1) and # Confirmed by momentum or diffusion
                trend_vol_filters_passed): # Filter conditions met
                self.order = self.buy()

            # Short entry logic: Strong negative jump + momentum/diffusion + filter confirmation
            elif (self.jump_detector.jump_signal[0] < -0.8 and # A clear negative jump
                  (self.momentum_detector.momentum_direction[0] < 0 or self.jump_detector.diffusion_trend[0] * self.params.diffusion_weight < -0.1) and # Confirmed by momentum or diffusion
                  trend_vol_filters_passed): # Filter conditions met
                self.order = self.sell()
        
        # ... (Position management, trailing stop, and fixed stop-loss logic)