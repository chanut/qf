import numpy as np
from time import sleep
from logging import getLogger
from quantfreedom.custom_logger import set_loggers
from quantfreedom.email_sender import EmailSender
from quantfreedom.exchanges.mufex_exchange.mufex import Mufex
from quantfreedom.helper_funcs import dos_cart_product, get_dos, log_dynamic_order_settings
from quantfreedom.live_mode import LiveTrading
from quantfreedom.order_handler.order import OrderHandler
from live_strat import DonChainLWTI
from my_stuff import EmailSenderInfo, MufexTestKeys

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

logger = getLogger("info")

ind_set_index = 0
dos_index = 2

email_sender = EmailSender(
    smtp_server=EmailSenderInfo.smtp_server,
    sender_email=EmailSenderInfo.sender_email,
    password=EmailSenderInfo.password,
    receiver=EmailSenderInfo.receiver,
)
logger.debug("set email sender")


strategy = DonChainLWTI(
    long_short="long",
    period=np.array([96]),   
    email_sender=email_sender
)

logger.disabled = False
set_loggers(log_folder=strategy.log_folder)

logger.debug("set strategy and logger")

strategy.live_set_indicator(ind_set_index=ind_set_index)
strategy.log_indicator_settings(ind_set_index=ind_set_index)

mufex_test = Mufex(
    api_key=MufexTestKeys.api_key,
    secret_key=MufexTestKeys.secret_key,
    use_test_net=False,
)
logger.debug("set exchange")

mufex_test.set_exchange_settings(
    leverage_mode=LeverageModeType.Isolated,
    position_mode=PositionModeType.HedgeMode,
    symbol="BTCUSDT",
)
logger.debug("set exchange settings")

try:
    equity = mufex_test.get_equity_of_asset(trading_with="USDT")
    logger.debug("got equity")
except Exception as e:
    logger.error(f"Couldn't get equtity -> {e}")
    raise Exception(f"Couldn't get equity -> {e}")

# default live
# static_os = StaticOrderSettings(
#     increase_position_type=IncreasePositionType.RiskPctAccountEntrySize,
#     leverage_strategy_type=LeverageStrategyType.Dynamic,
#     pg_min_max_sl_bcb="min",
#     sl_strategy_type=StopLossStrategyType.SLBasedOnCandleBody,
#     sl_to_be_bool=False,
#     starting_bar=50,
#     starting_equity=27.0,
#     static_leverage=None,
#     tp_fee_type="limit",
#     tp_strategy_type=TakeProfitStrategyType.RiskReward,
#     trail_sl_bool=False,
#     z_or_e_type=None,
# )
try:
    equity = mufex_test.get_equity_of_asset(trading_with="USDT")
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

# default live
# dos_arrays = DynamicOrderSettingsArrays(
#     max_equity_risk_pct=np.array([0.03]),
#     max_trades=np.array([5]),
#     risk_account_pct_size=np.array([0.01]),
#     risk_reward=np.array([2, 5]),
#     sl_based_on_add_pct=np.array([0.1, 0.25, 0.5]),
#     sl_based_on_lookback=np.array([20, 50]),
#     sl_bcb_type=np.array([CandleBodyType.Low]),
#     sl_to_be_cb_type=np.array([CandleBodyType.Nothing]),
#     sl_to_be_when_pct=np.array([0]),
#     trail_sl_bcb_type=np.array([CandleBodyType.Low]),
#     trail_sl_by_pct=np.array([0.5, 1.0]),
#     trail_sl_when_pct=np.array([1, 2]),
# )

#test live
dos_arrays = DynamicOrderSettingsArrays(
    max_equity_risk_pct=np.array([12]),
    max_trades=np.array([1]),
    risk_account_pct_size=np.array([3]),
    risk_reward=np.array([1, 3]),
    sl_based_on_add_pct=np.array([1, 0.25]),
    sl_based_on_lookback=np.array([30]),
    sl_bcb_type=np.array([CandleBodyType.Low]),
    sl_to_be_cb_type=np.array([CandleBodyType.Nothing]),
    sl_to_be_when_pct=np.array([0]),
    trail_sl_bcb_type=np.array([CandleBodyType.Low]),
    trail_sl_by_pct=np.array([1, 2, 3]),
    trail_sl_when_pct=np.array([1, 2]),
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
    exchange_settings=mufex_test.exchange_settings,
    long_short=strategy.long_short,
    static_os=static_os,
)
logger.debug("set order handler")

order.update_class_dos(dynamic_order_settings=dynamic_order_settings)

order.set_order_variables(equity=equity)



while True:
    try:
        logger.debug("running live tradin BTCUSDT")        
        LiveTrading(
            email_sender=email_sender,
            entry_order_type="market",
            exchange=mufex_test,
            order=order,
            strategy=strategy,
            symbol="BTCUSDT",
            trading_with="USDT",
            tp_order_type="limit",
        ).run(
            candles_to_dl=1000,
            timeframe="5m",
        )
        break  # If no errors, exit the loop
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Retrying in 5 seconds...")
        sleep(5)  # Pause for 5 seconds before retrying
        
