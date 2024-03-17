
import numpy as np
import ta

def donchian_channels(high, low, period=96, offset=0):
        """Calculates Donchian Channels with an offset."""

        upper = np.full_like(high, np.nan)  # Initialize with NaN
        lower = np.full_like(low, np.nan)
        basis = np.full_like(high, np.nan)

        for i in range(period, len(high)):
            # Enhanced Debugging
            # print("Iteration:", i)
            # print("Index Range:", i - period + 1, "to", i)
            # print("Current high slice:", high[i - period + 1:i + 1])

            upper[i] = max(high[i - period: i + 1])  # Adjust from i - period + 1 
            lower[i] = min(low[i - period + 1:i + 1])
            basis[i] = (upper[i] + lower[i]) / 2

        # print("Length of input data:", len(high), len(low))
        # print("Length of upper array:", len(upper))

        return basis[offset:], upper[offset:].copy(), lower[offset:]
    
def ema(data, period):
    """Calculates the Exponential Moving Average (EMA).

    Args:
        data (array-like): Array of values  
        period (int): The smoothing period.

    Returns:
        array-like: The calculated EMA values.
    """
    alpha = 2 / (period + 1)  # Smoothing factor
    ema_values = np.zeros_like(data)
    ema_values[period - 1] = np.mean(data[:period])  # Initial simple average

    for i in range(period, len(data)):
        ema_values[i] = alpha * data[i] + (1 - alpha) * ema_values[i - 1]

    return ema_values

def sma(data, period):
    """Calculates the Simple Moving Average (SMA).

    Args:
        data (array-like): Array of values.
        period (int): The smoothing period.

    Returns:
        array-like: The calculated SMA values.
    """
    sma_values = np.zeros_like(data)
    for i in range(period - 1, len(data)):
        sma_values[i] = np.mean(data[i - period + 1: i + 1])

    return sma_values

def calculate_ma(data, period, ma_type):
    if ma_type == "SMA":
        return ta.sma(data, period)  
    elif ma_type == "EMA":
        return ema(data, period)  # Use our custom 'ema' function
    # ... Add cases for WMA and RMA if those functions are available 
    else:  
        return ta.sma(data, period)  # Default to SMA

def smooth_indicator(data, smooth_type, period):
    # Implement smoothing functions for EMA, WMA, RMA if needed
    if smooth_type == "SMA":
        return ta.sma(data, period) 
    # ... 
    else: 
        return data 
    

def atr(high, low, close, period):
    """Calculates the Average True Range (ATR).

    Args:
        high (array-like): Array of high prices.
        low (array-like): Array of low prices.
        close (array-like): Array of closing prices.
        period (int): The lookback period.

    Returns:
        array-like: The calculated ATR values.
    """
    tr = np.zeros_like(high)
    atr_values = np.zeros_like(high)

    for i in range(1, len(high)):
        tr[i] = max(
            high[i] - low[i], 
            abs(high[i] - close[i - 1]), 
            abs(low[i] - close[i - 1])
        )

    atr_values[period - 1] = np.mean(tr[:period])  # Initial simple average

    for i in range(period, len(high)):
        atr_values[i] = (atr_values[i - 1] * (period - 1) + tr[i]) / period

    return atr_values

def lwti(close, high_prices=None, low_prices=None, period=8, smooth=False, smooth_type="SMA", smooth_period=5):
    """Calculates the Larry Williams Large Trade Index (LWTI)."""

    def calculate_range(high, low):  # True Range helper 
        tr = np.maximum(high - low, np.abs(np.subtract(high, np.roll(close, 1))))
        return tr

    diff = close - np.roll(close, period)
    tr = calculate_range(high_prices, low_prices) 

    ma_diff = calculate_ma(diff, period, smooth_type) 
    ma_tr = calculate_ma(tr, period, smooth_type) 

    lwti = np.where(ma_tr == 0, 50, (ma_diff / ma_tr) * 50 + 50) 

    if smooth:
        lwti = smooth_indicator(lwti, smooth_type, smooth_period)

    return lwti

def get_lwti_color(value):
    if value > 50:
        return 'green'
    elif value < 50:
        return 'red'
    else:
        return 'gray'  # Or a color of your choice for the midline     
    
def calculate_volume_color(open_price, close_price):
    if close_price >= open_price:
        return 'green'
    else:
        return 'red'
    
def shift_and_pad(arr, shift_amount, num_nan):
    shifted_arr = np.roll(arr, shift_amount)  # Shift the array
    padding = np.full(num_nan, np.nan)        # Create NaN padding
    return np.concatenate((padding, shifted_arr))  # Combine padding and shifted array