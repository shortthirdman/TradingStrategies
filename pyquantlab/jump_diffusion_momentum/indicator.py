import bac

class JumpDiffusionDetector(bt.Indicator):
    lines = ('jump_signal', 'jump_magnitude', 'diffusion_trend')
    params = (('lookback', 20), ('jump_threshold', 2.5), ('min_jump_size', 0.02), ('decay_factor', 0.9),)

    def __init__(self):
        self.returns = bt.indicators.PctChange(self.data.close, period=1)
        self.vol_estimator = bt.indicators.StandardDeviation(self.returns, period=self.params.lookback)
        self.change_buffer = deque(maxlen=self.params.lookback)

    def next(self):
        current_return = self.returns[0]
        current_vol = self.vol_estimator[0]
        # ... (Z-score calculation, jump detection, jump_signal and jump_magnitude assignment)
        # Diffusion trend: smoothed recent returns
        self.change_buffer.append(current_return)
        if len(self.change_buffer) >= 5:
            recent_trend = np.mean(list(self.change_buffer)[-5:])
            self.lines.diffusion_trend[0] = np.tanh(recent_trend / current_vol) # Normalized diffusion trend


class MomentumAfterJump(bt.Indicator):
    lines = ('momentum_strength', 'momentum_direction')
    params = (('momentum_period', 5), ('momentum_threshold', 0.6),)

    def __init__(self):
        self.returns = bt.indicators.PctChange(self.data.close, period=1)
        self.momentum_buffer = deque(maxlen=self.params.momentum_period)

    def next(self):
        self.momentum_buffer.append(self.returns[0] if not np.isnan(self.returns[0]) else 0)
        if len(self.momentum_buffer) >= self.params.momentum_period:
            returns_array = np.array(list(self.momentum_buffer))
            positive_returns = np.sum(returns_array > 0)
            negative_returns = np.sum(returns_array < 0)
            total_returns = len(returns_array)

            if total_returns > 0:
                strength = max(positive_returns, negative_returns) / total_returns
                direction = 1 if positive_returns > negative_returns else -1
                self.lines.momentum_strength[0] = strength
                self.lines.momentum_direction[0] = direction if strength >= self.params.momentum_threshold else 0


class TrendVolatilityFilter(bt.Indicator):
    lines = ('adx_rising', 'atr_rising', 'adx_strength', 'atr_strength', 'adx_rising_count', 'atr_rising_count')
    params = (('adx_period', 7), ('atr_period', 7), ('min_adx_level', 25), ('rising_lookback', 7), ('min_rising_periods', 5),)

    def __init__(self):
        self.adx = bt.indicators.DirectionalMovementIndex(period=self.params.adx_period)
        self.atr = bt.indicators.AverageTrueRange(period=self.params.atr_period)
        self.adx_buffer = deque(maxlen=self.params.rising_lookback + 1)
        self.atr_buffer = deque(maxlen=self.params.rising_lookback + 1)

    def next(self):
        current_adx = self.adx[0]
        current_atr = self.atr[0]
        self.adx_buffer.append(current_adx)
        self.atr_buffer.append(current_atr)

        # Count rising periods
        adx_rising_count = sum(1 for i in range(1, len(self.adx_buffer)) if self.adx_buffer[i] > self.adx_buffer[i-1])
        atr_rising_count = sum(1 for i in range(1, len(self.atr_buffer)) if self.atr_buffer[i] > self.atr_buffer[i-1])

        # Check for sustained rising and min ADX level
        adx_sustained_rising = (adx_rising_count >= self.params.min_rising_periods and current_adx >= self.params.min_adx_level and current_adx > self.adx_buffer[0])
        atr_sustained_rising = (atr_rising_count >= self.params.min_rising_periods and current_atr > self.atr_buffer[0])

        self.lines.adx_rising[0] = 1 if adx_sustained_rising else 0
        self.lines.atr_rising[0] = 1 if atr_sustained_rising else 0