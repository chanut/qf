import os
import numpy as np
from numpy.core.multiarray import array as array
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta
from indicator import *

from datetime import datetime
from logging import getLogger
from typing import NamedTuple

from quantfreedom.helper_funcs import cart_product
from quantfreedom.indicators.tv_indicators import rsi_tv
from quantfreedom.enums import CandleBodyType
from quantfreedom.strategies.strategy import Strategy


logger = getLogger("info")


class DonChainLWTI(Strategy):
    def __init__(
        self,
        long_short: str,        
    ) -> None:
        self.long_short = long_short
        self.log_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        if long_short == "long":
            self.set_entries_exits_array = self.long_set_entries_exits_array
            self.log_indicator_settings = self.long_log_indicator_settings
            self.entry_message = self.long_entry_message
            self.live_evalutate = self.long_live_evaluate
            self.chart_title = "Long Signal"
        else:
            self.set_entries_exits_array = self.short_set_entries_exits_array
            self.log_indicator_settings = self.short_log_indicator_settings
            self.entry_message = self.short_entry_message
            self.live_evalutate = self.short_live_evaluate
            self.chart_title = "short Signal"
            
    #######################################################
    #######################################################
    #######################################################
    ##################      Long     ######################
    ##################      Long     ######################
    ##################      Long     ######################
    #######################################################
    #######################################################
    #######################################################
    

    def long_set_entries_exits_array(
        self,
        candles: np.array,
        ind_set_index: int,
    ):
        try:   
            self.open_prices = candles[:, CandleBodyType.Open];
            self.close_prices = candles[:, CandleBodyType.Close];
            self.high_prices = candles[:, CandleBodyType.High];
            self.low_prices = candles[:, CandleBodyType.Low];    
            self.volume = candles[:, CandleBodyType.Volume];    
            self.lwti_values = lwti(close=self.close_prices, high_prices=self.high_prices , low_prices=self.low_prices, period=25, smooth=True, smooth_type="EMA", smooth_period=20)              
            
            # Calculate Donchian Channels (with an offset to handle the initial period)
            period = 96  # Lookback period
            self.offset = period - 1  # Offset to skip incomplete calculations            
            basis, upper, lower = donchian_channels(self.high_prices, self.low_prices, period, self.offset)
            self.offset = self.offset
            self.basis = basis
            self.upper = upper
            self.lower = lower
            
            self.final_upper = shift_and_pad(self.upper, shift_amount=2, num_nan=self.offset)
            
            ma_volume = sma(self.volume, 30)
            prev_close = np.roll(self.close_prices,1)
            prev_close[0] = np.nan

            prev_prev_close = np.roll(prev_close,1)
            prev_prev_close[0] = np.nan

            price_touch_upper = self.close_prices > self.final_upper-50 # Close
            lwti_uptrend = self.lwti_values > 50
            volume_above_ma = self.volume > ma_volume
            rising = self.close_prices > prev_close
            rising2 = prev_close > prev_prev_close

            entries = np.where(price_touch_upper & lwti_uptrend & volume_above_ma & rising & rising2,True,False)

            signal_history = np.zeros_like(entries)  # Array to track recent signals
            filter_distance = 10  # Number of candles to look back
            for i, signal in enumerate(entries):
                if signal:
                    # Check for previous signals within the filter distance
                    if np.any(signal_history[max(0, i - filter_distance):i]):
                        entries[i] = False  # Filter out the current signal
                    else:
                        signal_history[i] = True  # Record this signal
                        
                filtered_indices = np.where(entries == True)
                        
                self.entry_signals = np.where(entries, self.close_prices, np.nan)
                self.exit_prices = np.full_like(self.close_prices, np.nan)            
                    
        except Exception as e:
            logger.error(f"Exception long_set_entries_exits_array -> {e}")
            raise Exception(f"Exception long_set_entries_exits_array -> {e}")
        
    #######################################################
    #######################################################
    #######################################################
    ##################      Plot     ######################
    ##################      Plot     ######################
    ##################      Plot     ######################
    #######################################################
    #######################################################
    #######################################################        
    def plot_signals(
        self,
        candles: np.array,
    ):
        datetimes = candles[:, CandleBodyType.Timestamp].astype("datetime64[ms]")
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True)  
        
        # Candlestick chart with Donchian Channels (Row 1)
        fig.add_trace(go.Candlestick(
            x=datetimes,
            name="Candles",
            open=self.open_prices, high=self.high_prices,
            low=self.low_prices, close=self.close_prices
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=datetimes[self.offset:], y=self.basis, name='Basis', line=dict(color='#FF6D00')), row=1, col=1)
        fig.add_trace(go.Scatter(x=datetimes[self.offset:], y=self.upper, name='Upper', line=dict(color='#2962FF')), row=1, col=1)
        fig.add_trace(go.Scatter(x=datetimes[self.offset:], y=self.lower, name='Lower', line=dict(color='#2962FF')), row=1, col=1)

        # ... (Donchian Channels background fill code - Add this to Row 1)

        # plot the signal
        fig.add_trace(go.Scatter(
            x=datetimes,
            y=self.entry_signals,
            mode='markers',
            marker=dict(color='green', symbol='triangle-up', size=10),
            name='Buy Signals'
        ))
        
        # LWTI Line (Row 2)
        fig.add_trace(go.Scatter(
            x=datetimes, y=self.lwti_values, 
            mode='lines+markers', name='LWTI', 
            marker=dict(color=[get_lwti_color(value) for value in self.lwti_values]),  # Color for markers
            line=dict(width=1)  # Styling for the line
        ), row=2, col=1)
        # Midline for LWTI
        fig.add_hline(y=50, line_dash="dot", line_color='gray', row=2, col=1)

        # Volume Indicator (Row 3)
        fig.add_trace(go.Bar(
            x=datetimes, 
            y=self.volume,    
            name="Volume",
            marker_color=list(map(calculate_volume_color, self.open_prices, self.close_prices))
        ), row=3, col=1)

        # Volume Moving Average (default period 30)
        ma_volume = sma(self.volume, 30)  # Assuming you have the 'ta' library for moving averages
        fig.add_trace(go.Scatter(
            x=datetimes,
            y=ma_volume,
            mode='lines',
            name='Volume MA 30',
            line=dict(color='white')
        ), row=3, col=1) 
        
        # Customize layout
        fig.update_layout(title="Candlestick Chart with Donchian Channels and LWTI",
                        xaxis_title="Date", 
                        yaxis_title="Price",                   
                        yaxis2_title="LWTI Value",
                        yaxis3_title="Volume MA",
                        width=1200,  # Set the desired width in pixels
                        height=800,   # Set the desired height in pixels
                        xaxis_rangeslider_visible=False,)

        fig.show()