import os
import numpy as np
from numpy.core.multiarray import array as array
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from datetime import datetime
from logging import getLogger
from typing import NamedTuple

from quantfreedom.helper_funcs import cart_product
from quantfreedom.indicators.tv_indicators import macd_tv, ema_tv,rsi_tv,sma_tv
from quantfreedom.enums import CandleBodyType
from quantfreedom.strategies.strategy import Strategy

logger = getLogger("info")

def calculate_volume_color(open_price, close_price):
    if close_price >= open_price:
        return 'green'
    else:
        return 'red'
    
def calculate_volume_color(open_price, close_price):
    if close_price >= open_price:
        return 'green'
    else:
        return 'red'

class IndicatorSettingsArrays(NamedTuple):
    rsi_is_above: np.array
    rsi_is_below: np.array
    rsi_length: np.array
    ema_length: np.array
    fast_length: np.array
    macd_below: np.array
    signal_smoothing: np.array
    slow_length: np.array
    
class MacdCrossAndRSIOver(Strategy):        
    def __init__(
        self,
        long_short: str,
        rsi_length: int,
        rsi_is_above: np.array = np.array([0]),
        rsi_is_below: np.array = np.array([0]),
        ema_length: np.array = np.array([0]),
        fast_length: np.array = np.array([0]),
        macd_below: np.array = np.array([0]),
        signal_smoothing: np.array = np.array([0]),
        slow_length: np.array = np.array([0]),
              
    ) -> None:
        self.long_short = long_short
        self.log_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        cart_arrays = cart_product(
            named_tuple=IndicatorSettingsArrays(
                rsi_is_above=rsi_is_above,
                rsi_is_below=rsi_is_below,
                rsi_length=rsi_length,
                ema_length=ema_length,
                fast_length=fast_length,
                macd_below=macd_below,
                signal_smoothing=signal_smoothing,
                slow_length=slow_length,
            )
        )
        print('bf',len(cart_arrays))
        # cart_arrays = cart_arrays.T[cart_arrays[1] < cart_arrays[4]].T
        print('aft',len(cart_arrays))
        
        self.indicator_settings_arrays: IndicatorSettingsArrays = IndicatorSettingsArrays(
            rsi_is_above=cart_arrays[0],
            rsi_is_below=cart_arrays[1],
            rsi_length=cart_arrays[2].astype(np.int_),
            ema_length=cart_arrays[3].astype(np.int_),
            fast_length=cart_arrays[4].astype(np.int_),
            macd_below=cart_arrays[5].astype(np.int_),
            signal_smoothing=cart_arrays[6].astype(np.int_),
            slow_length=cart_arrays[7].astype(np.int_),
        )
        
        # print(self.indicator_settings_arrays)
        
        
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
            self.open_prices = candles[:,CandleBodyType.Open]
            self.closing_prices = candles[:, CandleBodyType.Close]
            self.low_prices = candles[:, CandleBodyType.Low]
            self.volume = candles[:,CandleBodyType.Volume]
            
            # print(self.indicator_settings_arrays[0])
            self.rsi_is_below = self.indicator_settings_arrays.rsi_is_below[ind_set_index]
            self.rsi_length = self.indicator_settings_arrays.rsi_length[ind_set_index]
            self.h_line = self.rsi_is_below
            self.ema_length = self.indicator_settings_arrays.ema_length[ind_set_index]
            self.fast_length = self.indicator_settings_arrays.fast_length[ind_set_index]
            self.macd_below = self.indicator_settings_arrays.macd_below[ind_set_index]
            self.signal_smoothing = self.indicator_settings_arrays.signal_smoothing[ind_set_index]
            self.slow_length = self.indicator_settings_arrays.slow_length[ind_set_index]
            
            self.current_ind_settings = IndicatorSettingsArrays(
                rsi_is_above=np.nan, 
                rsi_is_below=self.rsi_is_below,
                rsi_length=self.rsi_length,
                ema_length= self.ema_length,
                fast_length= self.fast_length,
                macd_below= self.macd_below,
                signal_smoothing= self.signal_smoothing,
                slow_length= self.slow_length,
            )
            
            self.ma_volume = sma_tv(
                source=self.volume,
                length=30
            )

            rsi = rsi_tv(
                source=candles[:, CandleBodyType.Close],
                length=self.rsi_length,
            )

            self.rsi = np.around(rsi, 1)
            logger.info(f"Created RSI rsi_length= {self.rsi_length}")
            
            is_below = self.rsi < self.rsi_is_below
            
            self.histogram, self.macd, self.signal = macd_tv(
                source=self.closing_prices,
                fast_length=self.fast_length,
                slow_length=self.slow_length,
                signal_smoothing=self.signal_smoothing,
            )

            self.ema = ema_tv(
                source=self.closing_prices,
                length=self.ema_length,
            )

            prev_macd = np.roll(self.macd, 1)
            prev_macd[0] = np.nan

            prev_signal = np.roll(self.signal, 1)
            prev_signal[0] = np.nan

            macd_below_signal = prev_macd < prev_signal
            macd_above_signal = self.macd > self.signal
            # low_price_below_ema = low_prices > self.ema
            macd_below_number = self.macd < self.macd_below
            
            look_back = 10            
            has_recent_oversold_rsi = np.zeros_like(self.closing_prices, dtype=bool)  # Initialize as False
            for i in range(look_back, len(rsi)):
                window = rsi[i - look_back: i]
                has_recent_oversold_rsi[i] = np.any(window < self.rsi_is_below)
                
            look_back_ema = 48
            has_close_above_ema = np.zeros_like(self.closing_prices, dtype=bool)  # Initialize as False
            # Ensure you have at least 48 candles of data 
            if len(self.closing_prices) >= look_back_ema:                
                for i in range(look_back_ema, len(self.closing_prices)):
                    tmp = self.closing_prices[i - look_back_ema: i]
                    ema_value = self.ema[i]
                    has_close_above_ema[i] = np.any(tmp > ema_value) 
            else:
                # Handle the case where you don't have enough data yet 
                print("Not enough candles for calculation")   
                
            volume_above_ma = self.volume > self.ma_volume
            
            # Calculate MACD Crossovers
            macd_crossovers = np.diff(np.sign(self.macd - self.signal))
            
            look_back_macd_cross = 12
            # Check for recent MACD cross up (bullish crossover)
            recent_macd_cross_up = np.any(macd_crossovers[-look_back_macd_cross:] == 2)
            
            macd_cross = (
            # (low_price_below_ema == True)
            (macd_above_signal == True)
            & (macd_below_signal == True)
            # & (macd_below_number == True)
            )
            
            self.entries = (
                 (macd_above_signal == True)
                & (macd_below_signal == True)
                # & (macd_below_number == True)
                & (has_recent_oversold_rsi == True)
                & (volume_above_ma == True)
                & (has_close_above_ema == True)
                # & recent_macd_cross_up == False  # Skip entry if recent MACD cross up
            )            
            
            self.entry_signals = np.where(self.entries, self.macd,np.nan)
            
            self.entry_signals_rsi = np.where(self.entries, rsi, np.nan)
            self.entry_signals_macd = np.where(self.entries, self.macd, np.nan)
            self.macd_cross_plot = np.where(macd_cross, self.macd, np.nan)
            self.entry_signals_close = np.where(self.entries, self.closing_prices, np.nan)
            
            self.exit_prices= np.full_like(self.entries, np.nan)                   
        except Exception as e:
            logger.error(f"Exception long_set_entries_exits_array -> {e}")
            raise Exception(f"Exception long_set_entries_exits_array -> {e}")

    def long_log_indicator_settings(
        self,
        ind_set_index: int,
    ):
        # logger.info(
        #     f"Indicator Settings\
        # \nIndicator Settings Index= {ind_set_index}\
        # \nema_length= {self.ema_length}\
        # \nfast_length= {self.fast_length}\
        # \nmacd_below= {self.macd_below}\
        # \nsignal_smoothing= {self.signal_smoothing}\
        # \nslow_length= {self.slow_length}        
        # \nrsi_length= {self.rsi_length}\
        # \nrsi_is_below= {self.rsi_is_below}"
        # )
        
        logger.info(
            f"Indicator settings\
        \nIndicator settings Index= {ind_set_index}\
        \nema_length= {self.ema_length}\
        \nfast_length= {self.fast_length}\
        \nmacd_below= {self.macd_below}\
        \nsignal_smoothing= {self.signal_smoothing}\
        \nslow_length= {self.slow_length}"
        )

    def long_entry_message(
        self,
        bar_index: int,
    ):
        logger.info("\n\n")
        logger.info(
            f"Entry time!!! {self.rsi[bar_index-2]} > {self.rsi[bar_index-1]} < {self.rsi[bar_index]} and {self.rsi[bar_index]} < {self.rsi_is_below}"
        )
        
    #######################################################
    #######################################################
    ####################     Plot     #####################
    ####################     Plot     #####################
    ####################     Plot     #####################
    #######################################################
    #######################################################
        
    def plot_signals(self, candles: np.array):
        datetimes = candles[:,CandleBodyType.Timestamp].astype('datetime64[ms]')
        fig = go.Figure()
        fig = make_subplots(
            cols=1,
            rows=4,
            shared_xaxes=True,
            subplot_titles=["Candles","MACD","RSI"],
            # row_heights=[0.6,0.4],
            vertical_spacing=0.1
        )
        # Candlestick chart for pricing
        fig.append_trace(
            go.Candlestick(
                x=datetimes,
                open=candles[:, CandleBodyType.Open],        
                high=candles[:, CandleBodyType.High],        
                low=candles[:, CandleBodyType.Low],        
                close=candles[:, CandleBodyType.Close],       
                name="Candles",
            ),
            col=1,
            row=1
        )

        fig.append_trace(
            go.Scatter(
                x=datetimes,
                y=self.ema,
                name="EMA",
                line_color="yellow",
            ),
            col=1,
            row=1,
        )

        fig.append_trace(
            go.Scatter(
                x=datetimes,
                y=self.entry_signals_close,
                mode="markers",
                name="entries",
                marker=dict(
                    size=12,
                    symbol="circle",
                    color="#00F6FF",
                    line=dict(
                        width=1,
                        color="DarkSlateGray",
                    )
                )
            ),
            row=1,
            col=1        
        )



        ind_shift = np.roll(self.histogram, 1)
        ind_shift[0] = np.nan
        colors = np.where(
            self.histogram >= 0,
            np.where(ind_shift < self.histogram, "#26A69A", "#B2DFBD"),
            np.where(ind_shift < self.histogram, "#FFCDD2", "#FF5252"),
        )

        # fig.append_trace(
        #     go.Bar(
        #         x=datetimes,
        #         y=self.histogram,
        #         name="histogram",
        #         marker_color=colors
        #     ),
        #     row=2,
        #     col=1
        # )

        # fig.append_trace(
        #     go.Scatter(
        #         x=datetimes,
        #         y=self.macd,
        #         name="macd",
        #         line_color="#2962FF"
        #     ),
        #     row=2,
        #     col=1
        # )

        # fig.append_trace(
        #     go.Scatter(
        #         x=datetimes,
        #         y=self.signal,
        #         name="signal",
        #         line_color="#FF6D00"
        #     ),
        #     row=2,
        #     col=1
        # )

        # fig.append_trace(
        #     go.Scatter(
        #         x=datetimes,
        #         # y=entry_signals_macd,
        #         y=self.macd_cross_plot,
        #         mode="markers",
        #         name="entries",
        #         marker=dict(
        #             size=12,
        #             symbol="circle",
        #             color="#00F6FF",
        #             line=dict(
        #                 width=1,
        #                 color="DarkSlateGray",
        #             )
        #         )
        #     ),
        #     row=2,
        #     col=1        
        # )

        fig.append_trace(
            go.Scatter(
                x=datetimes,
                y=self.rsi,
                name="rsi",
                line_color="yellow",
            ),
            row=3,
            col=1
        )

        fig.append_trace(
            go.Scatter(
                x=datetimes,
                y=self.entry_signals_rsi,
                mode="markers",
                name="entries",
                marker=dict(
                    size=12,
                    symbol="circle",
                    color="#00F6FF",
                    line=dict(
                        width=1,
                        color="DarkSlateGray",
                    )
                )
            ),
            row=3,
            col=1        
        )

        fig.add_hline(
            y=self.rsi_is_below,
            opacity=0.3,
            line_color="red",
            row=3,
            col=1  
        )

        # Volume Indicator (Row 3)
        fig.add_trace(go.Bar(
            x=datetimes, 
            y=self.volume,    
            name="Volume",
            marker_color=list(map(calculate_volume_color, self.open_prices, self.closing_prices))
        ), row=4, col=1)

        fig.add_trace(go.Scatter(
            x=datetimes,
            y=self.ma_volume,
            mode='lines',
            name='Volume MA 30',
            line=dict(color='white')
        ), row=4, col=1) 


        # Update options and show plot
        fig.update_layout(height=800, xaxis_rangeslider_visible=False)
        fig.show()
