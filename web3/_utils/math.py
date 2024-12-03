from typing import Optional, Sequence
from web3.exceptions import InsufficientData

def percentile(values: Optional[Sequence[int]]=None, percentile: Optional[float]=None) -> float:
    """Calculates a simplified weighted average percentile"""
    if values is None or percentile is None:
        raise InsufficientData("Both values and percentile must be provided")
    
    if not values:
        raise InsufficientData("The values sequence is empty")
    
    if not 0 <= percentile <= 100:
        raise ValueError("Percentile must be between 0 and 100")
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    if n == 1:
        return float(sorted_values[0])
    
    rank = percentile / 100.0 * (n - 1)
    lower_index = int(rank)
    upper_index = lower_index + 1
    
    if upper_index >= n:
        return float(sorted_values[-1])
    
    lower_value = sorted_values[lower_index]
    upper_value = sorted_values[upper_index]
    
    fraction = rank - lower_index
    
    return lower_value + (upper_value - lower_value) * fraction
