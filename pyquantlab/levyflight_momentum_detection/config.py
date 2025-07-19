class LevyFlightConfig:
    """Configuration class for Levy Flight Momentum Detection"""
    def __init__(self):
        # Levy Flight Parameters
        self.levy_window = 50  # Window for Levy parameter estimation
        self.alpha_bounds = (1.1, 2.0)  # Stability parameter bounds (1 < α ≤ 2)
        self.beta_bounds = (-1.0, 1.0)  # Skewness parameter bounds
        self.jump_threshold = 2.0  # Standard deviations for jump detection
        self.diffusion_threshold = 0.5  # Threshold for diffusive vs jump regime
        
        # Momentum Detection Parameters
        self.momentum_lookback = 20  # Lookback for momentum calculation
        self.jump_momentum_weight = 2.0  # Weight for jump-driven momentum
        self.diffusion_momentum_weight = 1.0  # Weight for diffusion momentum
        self.regime_persistence = 0.8  # Regime switching persistence
        
        # Signal Processing
        self.jump_signal_decay = 0.9  # Exponential decay for jump signals
        self.trend_ema_span = 12  # EMA span for trend extraction
        self.volatility_window = 20  # Window for volatility estimation
        self.signal_threshold = 0.02  # Trading signal threshold
        
        # Risk Management
        self.position_sizing = 1.0
        self.stop_loss = 0.04  # 4% stop loss
        self.take_profit = 0.08  # 8% take profit
        self.max_position_hold = 10  # Max days to hold position
        
        # Backtest Parameters
        self.train_period = 90
        self.test_period = 30
        self.transaction_cost = 0.0015
        self.initial_capital = 10000
        
    def display_parameters(self):
        # ... (displays parameters neatly) ...
		pass