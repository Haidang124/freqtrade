from freqtrade.strategy import IStrategy, Trade, Order, DecimalParameter, IntParameter
from pandas import DataFrame
from datetime import datetime, timedelta

class ScarpeStrategy(IStrategy):
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = '1m'
    process_only_new_candles = True
    startup_candle_count = 30

    # Cấu hình timeout cho lệnh chờ - quan trọng!
    unfilledtimeout = {
        "entry": 60,  # 60 phút cho lệnh entry
        "exit": 30,   # 30 phút cho lệnh exit
        "unit": "minutes"
    }

    # Cấu hình chiến lược - có thể tùy chỉnh trong config
    OC = DecimalParameter(1.0, 20.0, default=3.0, decimals=1, space="buy", optimize=True, load=False)
    Extent = DecimalParameter(20.0, 100.0, default=50.0, decimals=1, space="buy", optimize=True, load=False)
    Amount = IntParameter(1, 100, default=5, space="buy", optimize=True, load=True)
    TakeProfit = DecimalParameter(10.0, 100.0, default=35.0, decimals=1, space="sell", optimize=True, load=True)
    Reduce = DecimalParameter(1.0, 20.0, default=6.0, decimals=1, space="sell", optimize=True, load=True)
    UpReduce = DecimalParameter(10.0, 50.0, default=20.0, decimals=1, space="sell", optimize=True, load=True)

    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False,
    }
    order_time_in_force = {'entry': 'GTC', 'exit': 'GTC'}
    minimal_roi = {'0': 0.1}
    stoploss = -0.08  # Stop loss 15% thay vì 20%

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Tính toán biên độ OC và extent giá
        dataframe['oc_perc'] = (dataframe['close'] - dataframe['open']) / dataframe['open'] * 100
        dataframe['oc_abs'] = dataframe['close'] - dataframe['open']
        dataframe['high_perc'] = (dataframe['high'] - dataframe['open']) / dataframe['open'] * 100
        dataframe['low_perc'] = (dataframe['low'] - dataframe['open']) / dataframe['open'] * 100
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Đặt lệnh ngược chiều khi giá đạt extent
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0
        # Tính giá trị extent - sử dụng .value để lấy giá trị thực tế
        extent_val = self.OC.value * self.Extent.value / 100
        # Nếu nến tăng đủ extent, đặt lệnh short ở giá open + OC%
        dataframe.loc[
            (dataframe['high_perc'] >= extent_val),
            'enter_short'
        ] = 1
        # Nếu nến giảm đủ extent, đặt lệnh long ở giá open - OC%
        dataframe.loc[
            (dataframe['low_perc'] <= -extent_val),
            'enter_long'
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Không dùng exit signal, dùng custom_exit để kiểm soát TP động
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe
    
    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        # Luôn dùng đòn bẩy 20x, nhưng không vượt quá max_leverage sàn cho phép
        return min(20, max_leverage)

    def custom_entry_price(self, pair, trade, current_time, proposed_rate, entry_tag, side, **kwargs):
        # Đặt lệnh ở giá open +/- OC%
        # Sửa lỗi: get_analyzed_dataframe trả về tuple (dataframe, last_updated)
        analyzed_data = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if analyzed_data is not None:
            dataframe, last_updated = analyzed_data
            if len(dataframe) > 0:
                last_candle = dataframe.iloc[-1]
                if side == 'long':
                    return last_candle['open'] * (1 - self.OC.value / 100)
                else:
                    return last_candle['open'] * (1 + self.OC.value / 100)
        # Fallback về proposed_rate nếu không lấy được data
        return proposed_rate

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        # TP động giảm dần theo số nến đã qua
        entry_time = trade.open_date_utc
        now = current_time
        n_candles = int((now - entry_time).total_seconds() // 60)
        tp_dynamic = self.TakeProfit.value - n_candles * self.Reduce.value
        # Tính mức lợi nhuận mục tiêu dựa trên OC và Amount
        oc_val = trade.open_rate * self.OC.value / 100
        target_profit = tp_dynamic / 100 * oc_val * (trade.stake_amount / self.Amount.value)
        # Nếu đạt TP hoặc TP âm thì chốt lệnh
        if trade.calc_profit(current_rate) >= target_profit or tp_dynamic <= 0:
            return 'dynamic_tp'
        return None

    def check_entry_timeout(self, pair, trade, order, current_time, **kwargs):
        # Sửa logic timeout - chỉ hủy lệnh sau khi đã chờ đủ thời gian
        # Thời gian tối đa chờ lệnh: 30 phút
        max_wait_time = timedelta(minutes=30)
        
        # Nếu lệnh đã chờ quá 30 phút thì hủy
        if current_time - order.order_date > max_wait_time:
            return True  # Hủy lệnh
        
        # Kiểm tra thêm: nếu giá hiện tại đã đi quá xa so với giá đặt lệnh
        analyzed_data = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if analyzed_data is not None:
            dataframe, last_updated = analyzed_data
            if len(dataframe) > 0:
                current_price = dataframe.iloc[-1]['close']
                order_price = order.price
                
                # Nếu giá hiện tại cách xa giá đặt lệnh quá 5% thì hủy
                price_diff_percent = abs(current_price - order_price) / order_price * 100
                if price_diff_percent > 5:
                    return True  # Hủy lệnh
        
        return False  # Giữ lệnh

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage, entry_tag, side, **kwargs):
        # Luôn đặt đúng Amount cấu hình, nhưng không vượt quá max_stake
        return min(self.Amount.value, max_stake) 