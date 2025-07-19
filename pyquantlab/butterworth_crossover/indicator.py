import backtrader as bt
from scipy import signal

class ButterworthFilter(bt.Indicator):
    lines = ('filtered',)
    params = (
        ('cutoff_freq', 0.1),  # Normalized cutoff frequency (0 to 0.5)
        ('order', 2),          # Filter order
        ('lookback', 100),     # Data points needed for initial stable filter
    )

    def __init__(self):
        self.addminperiod(self.params.lookback)
        # Design the filter (coefficients b, a)
        self.b, self.a = signal.butter(
            N=self.params.order,
            Wn=self.params.cutoff_freq,
            btype='low',       # Low-pass filter
            analog=False       # Digital filter
        )
        self.data_buffer = deque(maxlen=self.params.lookback)
        self.zi = signal.lfilter_zi(self.b, self.a) # Initial filter state

    def next(self):
        current_price = self.data.close[0]
        self.data_buffer.append(current_price)

        if len(self.data_buffer) < self.params.lookback:
            self.lines.filtered[0] = current_price # Not enough data, return raw price
            return
        
        # Apply filter using the 'zi' (initial conditions) for continuity
        filtered_point, self.zi = signal.lfilter(
            self.b, self.a, [current_price], zi=self.zi
        )
        self.lines.filtered[0] = filtered_point[0]
    
    def addminperiod(self):
        pass