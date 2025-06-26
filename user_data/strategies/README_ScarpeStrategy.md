# ScarpeStrategy - Hướng dẫn cấu hình

## Mô tả
ScarpeStrategy là một chiến lược giao dịch dựa trên biên độ giá (OC - Open Close) với các tham số có thể tùy chỉnh động.

## Các tham số có thể cấu hình

### 1. OC (Biên độ)
- **Mô tả**: Biên độ phần trăm giữa giá mở và giá đóng
- **Phạm vi**: 1.0 - 20.0%
- **Mặc định**: 6.0%
- **Ví dụ**: OC = 6.0 nghĩa là biên độ 6%

### 2. Extent (Phần trăm biên độ để đặt lệnh)
- **Mô tả**: Phần trăm biên độ cần đạt để bắt đầu đặt lệnh
- **Phạm vi**: 20.0 - 100.0%
- **Mặc định**: 60.0%
- **Ví dụ**: Extent = 60.0 nghĩa là khi giá đạt 60% của biên độ OC thì đặt lệnh

### 3. Amount (Số tiền đặt lệnh)
- **Mô tả**: Số tiền USDT đặt cho mỗi lệnh
- **Phạm vi**: 10 - 1000 USDT
- **Mặc định**: 100 USDT

### 4. TakeProfit (Lợi nhuận mục tiêu ban đầu)
- **Mô tả**: Phần trăm lợi nhuận mục tiêu ban đầu trên biên độ OC
- **Phạm vi**: 10.0 - 100.0%
- **Mặc định**: 35.0%

### 5. Reduce (Giảm TP mỗi nến)
- **Mô tả**: Số phần trăm giảm TP mỗi phút (nến 1m)
- **Phạm vi**: 1.0 - 20.0%
- **Mặc định**: 6.0%

### 6. UpReduce (Tham số dự phòng)
- **Mô tả**: Tham số dự phòng cho tính năng tương lai
- **Phạm vi**: 5.0 - 50.0%
- **Mặc định**: 20.0%

## Cách cấu hình

### Phương pháp 1: Sử dụng config file
1. Sao chép file `config_scarpe_strategy.json` 
2. Chỉnh sửa phần `strategy_settings`:

```json
"strategy_settings": {
    "ScarpeStrategy": {
        "OC": 8.0,           // Thay đổi biên độ thành 8%
        "Extent": 70.0,      // Thay đổi extent thành 70%
        "Amount": 200,       // Thay đổi số tiền thành 200 USDT
        "TakeProfit": 40.0,  // Thay đổi TP thành 40%
        "Reduce": 8.0,       // Thay đổi reduce thành 8%
        "UpReduce": 25.0     // Thay đổi UpReduce thành 25%
    }
}
```

### Phương pháp 2: Sử dụng hyperopt để tối ưu
```bash
freqtrade hyperopt --config config_scarpe_strategy.json --strategy ScarpeStrategy --epochs 100
```

### Phương pháp 3: Chạy với tham số tùy chỉnh
```bash
freqtrade trade --config config_scarpe_strategy.json --strategy ScarpeStrategy
```

## Logic hoạt động

1. **Đặt lệnh**: Khi giá đạt `Extent%` của biên độ `OC`, đặt lệnh ngược chiều
   - Nếu giá tăng: đặt lệnh Short ở giá `open + OC%`
   - Nếu giá giảm: đặt lệnh Long ở giá `open - OC%`

2. **Take Profit động**: TP giảm dần theo thời gian
   - TP ban đầu = `TakeProfit%`
   - Mỗi phút giảm `Reduce%`
   - Khi TP ≤ 0, tự động chốt lệnh

3. **Quản lý lệnh**: Hủy lệnh chờ nếu sang nến mới mà chưa khớp

## Lưu ý quan trọng

- Chiến lược này phù hợp với thị trường có biến động cao
- Cần test kỹ trước khi sử dụng với tiền thật
- Có thể điều chỉnh các tham số theo từng cặp tiền tệ
- Nên sử dụng stop loss để bảo vệ vốn

## Ví dụ cấu hình cho thị trường khác nhau

### Thị trường biến động cao (BTC, ETH)
```json
{
    "OC": 8.0,
    "Extent": 70.0,
    "Amount": 150,
    "TakeProfit": 45.0,
    "Reduce": 8.0
}
```

### Thị trường ổn định (USDT pairs)
```json
{
    "OC": 4.0,
    "Extent": 50.0,
    "Amount": 100,
    "TakeProfit": 30.0,
    "Reduce": 5.0
}
``` 