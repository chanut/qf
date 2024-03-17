import sys
import numpy as np
from logging import getLogger
from quantfreedom.custom_logger import set_loggers
from quantfreedom.email_sender import EmailSender
from quantfreedom.helper_funcs import dos_cart_product, get_dos, log_dynamic_order_settings
from quantfreedom.order_handler.order import OrderHandler
from quantfreedom.enums import (
    CandleBodyType,
    DynamicOrderSettingsArrays,
    IncreasePositionType,
    LeverageModeType,
    LeverageStrategyType,
    StaticOrderSettings,
    StopLossStrategyType,
    TakeProfitStrategyType,
    PositionModeType,
)


from quantfreedom.exchanges.bybit_exchange.bybit_live_mode import BybitLiveMode
from quantfreedom.exchanges.mufex_exchange.mufex_live_mode import MufexLiveMode
from quantfreedom.exchanges.bybit_exchange.bybit import Bybit
from quantfreedom.exchanges.mufex_exchange.mufex import Mufex
from live_strat import MacdCrossAndRSIOver
from my_stuff import EmailSenderInfo, MufexTestKeys


logger = getLogger("info")

ind_set_index = 65
dos_index = 0

email_sender = EmailSender(
    smtp_server=EmailSenderInfo.smtp_server,
    sender_email=EmailSenderInfo.sender_email,
    password=EmailSenderInfo.password,
    receiver=EmailSenderInfo.receiver,
)

strategy = MacdCrossAndRSIOver(
    long_short="long",
    rsi_length=np.array([14]),
    rsi_is_below=np.arange(20, 46, 5),
    ema_length=np.arange(200, 401, 200),
    fast_length=np.arange(10, 21, 10),
    macd_below=np.array([0]),    
    signal_smoothing=np.arange(5, 16, 10),
    slow_length=np.arange(30, 61, 30),  
    email_sender=email_sender
)


logger.disabled = False
set_loggers(log_folder=strategy.log_folder)

logger.debug("set strategy and logger")


strategy.live_set_indicator(ind_set_index=ind_set_index)
strategy.log_indicator_settings(ind_set_index=ind_set_index)

use_test_net = False

user_ex = Mufex(
        api_key=MufexTestKeys.api_key,
        secret_key=MufexTestKeys.secret_key,
        use_test_net=use_test_net,
    )
logger.debug("set exchange")

user_ex.set_exchange_settings(
    leverage_mode=LeverageModeType.Isolated,
    position_mode=PositionModeType.HedgeMode,
    symbol="BTCUSDT",
)
logger.debug("set exchange settings")

try:
    equity = user_ex.get_equity_of_asset(trading_with="USDT")
    logger.debug("got equity")
except Exception as e:
    logger.error(f"Couldn't get equtity -> {e}")
    raise Exception(f"Couldn't get equity -> {e}")

static_os = StaticOrderSettings(
    increase_position_type=IncreasePositionType.RiskPctAccountEntrySize,
    leverage_strategy_type=LeverageStrategyType.Dynamic,
    pg_min_max_sl_bcb="min",
    sl_strategy_type=StopLossStrategyType.SLBasedOnCandleBody,
    sl_to_be_bool=False,
    starting_bar=50,
    starting_equity=equity,
    static_leverage=None,
    tp_fee_type="limit",
    tp_strategy_type=TakeProfitStrategyType.RiskReward,
    trail_sl_bool=True,
    z_or_e_type=None,
)
logger.debug("set static order settings")

dos_arrays = DynamicOrderSettingsArrays(
    max_equity_risk_pct=np.array([12]),
    max_trades=np.array([3]),
    risk_account_pct_size=np.array([3]),
    risk_reward=np.array([2]),
    sl_based_on_add_pct=np.array([1]),
    sl_based_on_lookback=np.array([30]),
    sl_bcb_type=np.array([CandleBodyType.Low]),
    sl_to_be_cb_type=np.array([CandleBodyType.Nothing]),
    sl_to_be_when_pct=np.array([0]),
    trail_sl_bcb_type=np.array([CandleBodyType.Low]),
    trail_sl_by_pct=np.array([1]),
    trail_sl_when_pct=np.array([1]),
)
logger.debug("got dos arrays")

dos_cart_arrays = dos_cart_product(dos_arrays=dos_arrays)
logger.debug("got cart product of dos")

dynamic_order_settings = get_dos(
    dos_cart_arrays=dos_cart_arrays,
    dos_index=dos_index,
)
log_dynamic_order_settings(
    dos_index=dos_index,
    dynamic_order_settings=dynamic_order_settings,
)

order = OrderHandler(
    exchange_settings=user_ex.exchange_settings,
    long_short=strategy.long_short,
    static_os=static_os,
)
logger.debug("set order handler")

order.update_class_dos(dynamic_order_settings=dynamic_order_settings)

order.set_order_variables(equity=equity)

email_sender = EmailSender(
    smtp_server="sdfasdfasdf",
    sender_email="sdfasdfasdf",
    password="sdfasdfasdf",
    receiver="sdfasdfasdf",
)

logger.debug("set email sender")

logger.debug("running live trading")

MufexLiveMode(
        email_sender=email_sender,
        entry_order_type="market",
        exchange=user_ex,
        order=order,
        strategy=strategy,
        symbol="BTCUSDT",
        trading_with="USDT",
        tp_order_type="limit",
    ).run(
        candles_to_dl=1000,
        timeframe="1m",
    )
