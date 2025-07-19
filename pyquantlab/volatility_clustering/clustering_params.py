from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class VolatilityClusteringParams:
    # Data Acquisition
    ticker: str = 'BTC-USD'
    period: str = '1y'
    
    # Volatility Clustering Parameters
    clustering_window: int = 20
    volatility_threshold: float = 1.5 # Multiplier for mean volatility to define cluster entry
    cluster_persistence_factor: float = 0.7 # (Note: This param isn't explicitly used in the provided code's logic)
    
    # Signal Generation
    entry_method: str = 'zscore'  # 'zscore', 'rolling_std', 'exponential_weighted'
    exit_method: str = 'cluster_breakdown'  # (Note: Exit logic is primarily cluster end)
    
    # Position Sizing
    position_sizing: str = 'cluster_persistence'  # 'cluster_persistence', 'volatility', 'adaptive'
    max_position_size: float = 0.2
    min_position_size: float = 0.05
    
    # Advanced Parameters
    volatility_smoothing: int = 5 # Window for smoothing the raw volatility metric
    cluster_detection_sensitivity: float = 1.0 # Factor to adjust cluster detection threshold
    
    # Debugging and Visualization
    verbose: bool = False