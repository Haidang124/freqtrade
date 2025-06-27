"""
Test Strategy for MEXC Futures Trading
"""
from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import talib.abstract as ta
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List
import logging
from freqtrade.exchange import timeframe_to_minutes

logger = logging.getLogger(__name__)


class TestMexcStrategy(IStrategy):
    """
    Simple test strategy for MEXC futures trading
    """
    
    # Strategy parameters
    leverage = IntParameter(1, 10, default=5, space="buy")
    
    # Minimal ROI designed for the strategy
    minimal_roi = {
        "0": 0.05,
        "30": 0.025,
        "60": 0.015,
        "120": 0.01
    }
    
    # Optimal stoploss designed for the strategy
    stoploss = -0.25
    
    # Trailing stoploss
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True
    
    # Timeframe for the strategy
    timeframe = '5m'
    
    # Run "populate_any_indicators()" only for new candle.
    process_only_new_candles = True
    
    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    
    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30
    
    # Strategy parameters
    buy_rsi = IntParameter(10, 40, default=30, space="buy")
    sell_rsi = IntParameter(60, 90, default=70, space="sell")
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame
        """
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # Bollinger Bands
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
        dataframe['bb_lowerband'] = bollinger['lowerband']
        dataframe['bb_middleband'] = bollinger['middleband']
        dataframe['bb_upperband'] = bollinger['upperband']
        dataframe['bb_percent'] = (dataframe['close'] - dataframe['bb_lowerband']) / (dataframe['bb_upperband'] - dataframe['bb_lowerband'])
        
        # EMA
        dataframe['ema_9'] = ta.EMA(dataframe, timeperiod=9)
        dataframe['ema_21'] = ta.EMA(dataframe, timeperiod=21)
        
        # Volume indicators
        dataframe['volume_mean'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_mean']
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry columns populated
        """
        dataframe.loc[
            (
                # Long entry conditions
                (dataframe['rsi'] < self.buy_rsi.value) &
                (dataframe['macd'] > dataframe['macdsignal']) &
                (dataframe['close'] > dataframe['ema_21']) &
                (dataframe['volume_ratio'] > 1.2) &
                (dataframe['bb_percent'] < 0.2)
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                # Short entry conditions
                (dataframe['rsi'] > self.sell_rsi.value) &
                (dataframe['macd'] < dataframe['macdsignal']) &
                (dataframe['close'] < dataframe['ema_21']) &
                (dataframe['volume_ratio'] > 1.2) &
                (dataframe['bb_percent'] > 0.8)
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with exit columns populated
        """
        dataframe.loc[
            (
                # Exit long conditions
                (dataframe['rsi'] > self.sell_rsi.value) &
                (dataframe['macd'] < dataframe['macdsignal'])
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                # Exit short conditions
                (dataframe['rsi'] < self.buy_rsi.value) &
                (dataframe['macd'] > dataframe['macdsignal'])
            ),
            'exit_short'] = 1
        
        return dataframe
    
    def custom_stake_amount(self, pair: str, current_time: datetime, current_balance: float,
                          **kwargs) -> float:
        """
        Custom stake amount for this strategy
        """
        return self.wallets.get_total_stake_amount() * 0.1  # Use 10% of balance per trade
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                          time_in_force: str, current_time: datetime, entry_tag: str,
                          side: str, **kwargs) -> bool:
        """
        Additional confirmation for trade entry
        """
        # Get current market data
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = df.iloc[-1].squeeze()
        
        # Additional confirmation logic
        if side == "long":
            # Only enter long if price is above EMA
            return last_candle['close'] > last_candle['ema_21']
        elif side == "short":
            # Only enter short if price is below EMA
            return last_candle['close'] < last_candle['ema_21']
        
        return True
    
    def custom_entry_price(self, pair: str, current_time: datetime,
                          proposed_rate: float, entry_tag: str, side: str,
                          **kwargs) -> float:
        """
        Custom entry price for this strategy
        """
        # Use current market price for entry
        return proposed_rate
    
    def custom_exit(self, pair: str, trade, current_time: datetime, current_rate: float,
                   current_profit: float, **kwargs) -> str | None:
        """
        Custom exit logic
        """
        # Exit if profit is too high (take profit)
        if current_profit > 0.1:  # 10% profit
            return "take_profit"
        
        # Exit if loss is too high (emergency exit)
        if current_profit < -0.15:  # 15% loss
            return "emergency_exit"
        
        return None 