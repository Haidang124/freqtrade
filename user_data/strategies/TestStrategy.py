# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, Union
from functools import reduce

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
from freqtrade.strategy import DecimalParameter, IntParameter
from pandas import DataFrame
# --------------------------------

class TestStrategy(IStrategy):
    """
    Strategy để test MEXC futures trading
    - Tự động mua sau 5 phút
    - Chốt lời khi lãi 1%
    - Stop loss 2%
    """
    
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 3

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        "0": 0.01  # Chốt lời 1% ngay lập tức
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.02  # Stop loss 2%

    # Trailing stoploss
    trailing_stop = False
    trailing_stop_positive = None
    trailing_stop_positive_offset = 0.0
    trailing_only_offset_is_reached = False

    # Optimal timeframe for the strategy.
    timeframe = '4h'  # MEXC chỉ hỗ trợ 4h cho futures
    
    # Use mark price for MEXC futures
    candle_type = "mark"
    
    # Override candle type for futures
    def get_trade_stake_amount(self, pair: str, edge: float, available_balance: float, **kwargs) -> float:
        return self.wallets.get_total_stake_amount() / self.config['max_open_trades']

    # Run "populate_any_indicators()" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Strategy parameters
    buy_delay_minutes = IntParameter(5, 5, default=5, space="buy", optimize=False)
    
    # Leverage cho futures
    leverage = 1
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # Ghi lại thời gian bot khởi động
        from datetime import datetime
        self.bot_start_time = datetime.now()
        print(f"Bot khởi động lúc: {self.bot_start_time}")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Tính toán các chỉ báo kỹ thuật
        """
        # Thêm timestamp
        dataframe['timestamp'] = pd.to_datetime(dataframe['date'])
        
        # Thêm RSI để có thêm thông tin
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Thêm SMA để có trend
        dataframe['sma_20'] = ta.SMA(dataframe, timeperiod=20)
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Dựa trên các chỉ báo kỹ thuật, xác định xu hướng mua vào
        """
        conditions = []
        
        # Điều kiện mua: RSI < 70 (không quá overbought) và có volume
        conditions.append(
            (dataframe['rsi'] < 70) &
            (dataframe['volume'] > 0)  # Có volume
        )
        
        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Dựa trên các chỉ báo kỹ thuật, xác định xu hướng bán ra
        """
        # Không có exit signal cụ thể, sẽ dựa vào ROI và stoploss
        dataframe['exit_long'] = 0
        
        return dataframe

    def leverage_callback(self) -> float:
        """
        Callback để set leverage cho futures
        """
        return self.leverage

    def custom_stake_amount(self, pair: str, current_time: datetime, current_balance: float,
                          **kwargs) -> float:
        """
        Custom stake amount cho futures
        """
        return self.wallets.get_total_stake_amount() / self.config['max_open_trades']

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                          time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                          side: str, **kwargs) -> bool:
        """
        Xác nhận trước khi vào lệnh
        """
        # Kiểm tra xem đã đủ 5 phút từ khi bot khởi động chưa
        if hasattr(self, 'bot_start_time'):
            minutes_since_start = (current_time - self.bot_start_time).total_seconds() / 60
            if minutes_since_start < self.buy_delay_minutes.value:
                self.log(f"Chưa đủ {self.buy_delay_minutes.value} phút, bỏ qua lệnh mua. Đã qua: {minutes_since_start:.1f} phút")
                return False
        
        # Log thông tin lệnh
        self.log(f"Vào lệnh {side} {pair} với {amount} @ {rate}")
        return True

    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float,
                          rate: float, time_in_force: str, sell_reason: str,
                          current_time: datetime, **kwargs) -> bool:
        """
        Xác nhận trước khi thoát lệnh
        """
        # Log thông tin thoát lệnh
        self.log(f"Thoát lệnh {pair} với lý do: {sell_reason}")
        return True 