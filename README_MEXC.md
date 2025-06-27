# Hướng dẫn sử dụng MEXC với Freqtrade

## 🎯 Tổng quan

MEXC Global đã được tích hợp vào Freqtrade để hỗ trợ futures trading. Bạn có thể sử dụng MEXC để giao dịch các cặp USDT futures với đầy đủ tính năng.

## 📋 Yêu cầu

- Tài khoản MEXC Global
- API Key với quyền futures trading
- Freqtrade đã được cài đặt

## ⚙️ Cấu hình

### 1. Tạo API Key

1. Đăng nhập vào [MEXC Global](https://www.mexc.com/)
2. Vào **API Management**
3. Tạo API Key mới với các quyền:
   - ✅ Spot & Margin Trading
   - ✅ Futures Trading  
   - ✅ Read Info

### 2. Tạo file config

Tạo file `config_mexc.json`:

```json
{
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 0.05,
    "trading_mode": "futures",
    "margin_mode": "isolated",
    "exchange": {
        "name": "mexc",
        "key": "your_api_key_here",
        "secret": "your_api_secret_here",
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
    "pairlists": [
        {"method": "StaticPairList"}
    ]
}
```

## 🚀 Sử dụng

### Chạy bot
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

## 📊 Các cặp tiền hỗ trợ

MEXC hỗ trợ các cặp USDT futures với format: `SYMBOL/USDT:USDT`

Ví dụ:
- `BTC/USDT:USDT`
- `ETH/USDT:USDT`
- `BNB/USDT:USDT`
- `ADA/USDT:USDT`
- `SOL/USDT:USDT`

## ⚠️ Lưu ý quan trọng

1. **Rủi ro cao**: Futures trading có rủi ro rất cao, có thể mất toàn bộ vốn
2. **Test trước**: Luôn test với dry-run trước khi giao dịch thật
3. **Quản lý rủi ro**: Sử dụng stop-loss và quản lý position size cẩn thận
4. **Leverage**: MEXC hỗ trợ leverage từ 1x đến 125x

## 🔧 Troubleshooting

### Lỗi thường gặp

1. **API Key không hợp lệ**
   - Kiểm tra lại API key và secret
   - Đảm bảo có quyền futures trading

2. **Không thể tạo order**
   - Kiểm tra balance
   - Kiểm tra leverage settings
   - Đảm bảo cặp tiền có trong whitelist

3. **Lỗi position mode**
   - MEXC sử dụng one-way position mode mặc định

## 📞 Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra logs của Freqtrade
2. Tham khảo [MEXC API Documentation](https://mexcdevelop.github.io/apidocs/)
3. Tạo issue trên GitHub

## ⚖️ Disclaimer

Trading futures có rủi ro cao và có thể dẫn đến mất toàn bộ vốn đầu tư. Hãy sử dụng cẩn thận và chỉ giao dịch với số tiền bạn có thể chấp nhận mất. 