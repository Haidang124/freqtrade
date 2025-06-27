# MEXC Exchange

MEXC Global là một sàn giao dịch tiền điện tử hỗ trợ cả spot và futures trading. Freqtrade đã được tích hợp để hỗ trợ MEXC cho futures trading.

## Cấu hình

### 1. Tạo API Key

1. Đăng ký tài khoản tại [MEXC Global](https://www.mexc.com/)
2. Vào phần API Management
3. Tạo API Key mới với các quyền:
   - Spot & Margin Trading
   - Futures Trading
   - Read Info

### 2. Cấu hình Freqtrade

Sử dụng file config mẫu `config_examples/config_mexc.example.json`:

```json
{
    "exchange": {
        "name": "mexc",
        "key": "your_exchange_key",
        "secret": "your_exchange_secret",
        "ccxt_config": {
            "options": {
                "defaultType": "swap"
            }
        },
        "pair_whitelist": [
            "BTC/USDT:USDT",
            "ETH/USDT:USDT",
            "BNB/USDT:USDT"
        ]
    },
    "trading_mode": "futures",
    "margin_mode": "isolated"
}
```

### 3. Các cặp tiền được hỗ trợ

MEXC hỗ trợ các cặp USDT futures với format: `SYMBOL/USDT:USDT`

Ví dụ:
- `BTC/USDT:USDT`
- `ETH/USDT:USDT`
- `BNB/USDT:USDT`
- `ADA/USDT:USDT`
- `SOL/USDT:USDT`

## Tính năng hỗ trợ

### ✅ Đã hỗ trợ
- Spot trading
- Futures trading (USDT-M)
- Isolated margin mode
- Cross margin mode
- Stop-loss orders
- Leverage trading
- Funding fees calculation
- Liquidation price calculation
- WebSocket connections

### ⚠️ Hạn chế
- Chỉ hỗ trợ USDT futures markets
- Position mode được set mặc định là one-way
- Một số tính năng nâng cao có thể chưa hoạt động hoàn hảo

## Sử dụng

### Khởi chạy bot

```bash
freqtrade trade -c config_mexc.json
```

### Backtesting

```bash
freqtrade backtesting -c config_mexc.json --strategy YourStrategy
```

### Hyperopt

```bash
freqtrade hyperopt -c config_mexc.json --strategy YourStrategy --epochs 100
```

## Lưu ý quan trọng

1. **Leverage**: MEXC hỗ trợ leverage từ 1x đến 125x tùy theo cặp tiền
2. **Funding Rate**: Được tính mỗi 8 giờ (00:00, 08:00, 16:00 UTC)
3. **Position Mode**: Mặc định sử dụng one-way position mode
4. **Risk Management**: Luôn sử dụng stop-loss và quản lý rủi ro cẩn thận

## Troubleshooting

### Lỗi thường gặp

1. **API Key không hợp lệ**: Kiểm tra lại API key và secret
2. **Không thể tạo order**: Kiểm tra balance và leverage settings
3. **Lỗi position mode**: Đảm bảo tài khoản đã được set up cho futures trading

### Liên hệ hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra logs của Freqtrade
2. Tham khảo [MEXC API Documentation](https://mexcdevelop.github.io/apidocs/)
3. Tạo issue trên GitHub repository của Freqtrade

## Ví dụ Strategy

```python
from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import talib.abstract as ta

class MexcFuturesStrategy(IStrategy):
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
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['macd'] > dataframe['macdsignal'])
            ),
            'enter_long'] = 1
        
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) &
                (dataframe['macd'] < dataframe['macdsignal'])
            ),
            'enter_short'] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) &
                (dataframe['macd'] < dataframe['macdsignal'])
            ),
            'exit_long'] = 1
        
        dataframe.loc[
            (
                (dataframe['rsi'] < 30) &
                (dataframe['macd'] > dataframe['macdsignal'])
            ),
            'exit_short'] = 1
        
        return dataframe
```

## Cập nhật

Để cập nhật hỗ trợ MEXC lên phiên bản mới nhất:

```bash
git pull origin develop
pip install -e .
```

## Đóng góp

Nếu bạn muốn đóng góp để cải thiện hỗ trợ MEXC, vui lòng:

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## Disclaimer

Trading futures có rủi ro cao và có thể dẫn đến mất toàn bộ vốn đầu tư. Hãy sử dụng cẩn thận và chỉ giao dịch với số tiền bạn có thể chấp nhận mất. 