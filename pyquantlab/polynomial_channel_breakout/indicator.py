import backtrader as bt
import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
import warnings

# Suppress sklearn warnings if they occur during fitting
warnings.filterwarnings('ignore')

class PolynomialChannelIndicator(bt.Indicator):
    lines = ('upper_channel', 'lower_channel', 'regression_line')
    
    params = (
        ('degree', 3),           # Polynomial degree
        ('channel_width', 2.0),  # Channel width in standard deviations
        ('lookback', 50),        # Lookback period for regression
    )
    
    plotinfo = dict(
        plot=True,
        subplot=False, # Plot on the main price chart
        plotlinelabels=True
    )
    
    plotlines = dict(
        upper_channel=dict(color='red', ls='--', alpha=0.7),
        lower_channel=dict(color='green', ls='--', alpha=0.7),
        regression_line=dict(color='blue', ls='-', alpha=0.8)
    )
    
    def __init__(self):
        self.addminperiod(self.params.lookback) # Ensure enough data for lookback
            
    def next(self):
        """Calculate polynomial channels for current bar."""
        if len(self.data) < self.params.lookback:
            return
            
        # Get price data for the lookback period, reversed to get newest last
        prices = np.array([self.data.close[-i] for i in range(self.params.lookback-1, -1, -1)])
            
        try:
            # Create x values (time points from 0 to lookback-1)
            x = np.arange(len(prices)).reshape(-1, 1)
            
            # Create a pipeline for polynomial features and linear regression
            poly_reg = make_pipeline(PolynomialFeatures(self.params.degree), LinearRegression())
            poly_reg.fit(x, prices) # Fit the model to prices
                
            # Predict values using the fitted model
            y_pred = poly_reg.predict(x)
                
            # Calculate residuals (difference between actual and predicted prices)
            residuals = prices - y_pred
            std_residuals = np.std(residuals) # Standard deviation of residuals (error)
                
            # The current regression value is the last predicted point
            current_regression = y_pred[-1]
                
            # Set channel boundaries for the current bar
            self.lines.upper_channel[0] = current_regression + (self.params.channel_width * std_residuals)
            self.lines.lower_channel[0] = current_regression - (self.params.channel_width * std_residuals)
            self.lines.regression_line[0] = current_regression
                
        except Exception as e:
            # Fallback in case of calculation error (e.g., singular matrix)
            # Use previous values if available, otherwise NaN
            if len(self) > 1:
                self.lines.upper_channel[0] = self.lines.upper_channel[-1]
                self.lines.lower_channel[0] = self.lines.lower_channel[-1]
                self.lines.regression_line[0] = self.lines.regression_line[-1]
            else:
                self.lines.upper_channel[0] = float('nan')
                self.lines.lower_channel[0] = float('nan')
                self.lines.regression_line[0] = float('nan')