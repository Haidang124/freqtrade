# ✅ Checklist Test MEXC Integration

## 🎯 Mục tiêu: Test MEXC integration trước khi dùng API key

### 📋 Bước 1: Kiểm tra cơ bản
- [ ] **1.1** Kiểm tra strategy có load được không
  ```bash
  freqtrade list-strategies --strategy-path user_data/strategies
  ```
  **Kết quả mong đợi**: Thấy "TestMexcStrategy"

- [ ] **1.2** Kiểm tra config có hợp lệ không
  ```bash
  freqtrade show-config -c config_mexc_dryrun.json
  ```
  **Kết quả mong đợi**: Hiển thị config mà không có lỗi

### 📊 Bước 2: Test dữ liệu
- [ ] **2.1** Download dữ liệu MEXC
  ```bash
  freqtrade download-data --exchange mexc --pairs BTC/USDT:USDT ETH/USDT:USDT --timeframe 5m --days 3
  ```
  **Kết quả mong đợi**: Download thành công, tạo file .feather

- [ ] **2.2** Kiểm tra dữ liệu đã download
  ```bash
  ls user_data/data/mexc/
  ```
  **Kết quả mong đợi**: Thấy file BTC_USDT_USDT-5m.feather

### 📈 Bước 3: Test Backtesting
- [ ] **3.1** Chạy backtesting
  ```bash
  freqtrade backtesting -c config_mexc_dryrun.json --strategy TestMexcStrategy --timerange 20241225-20241227
  ```
  **Kết quả mong đợi**: 
  - Không có lỗi
  - Hiển thị kết quả backtesting
  - Có trades được tạo

### 🤖 Bước 4: Test Dry-run
- [ ] **4.1** Chạy dry-run (5 phút)
  ```bash
  timeout 300 freqtrade trade -c config_mexc_dryrun.json --strategy TestMexcStrategy --dry-run-wallet 1000
  ```
  **Kết quả mong đợi**:
  - "Using Exchange 'Mexc'"
  - "Dry run wallet: 1000 USDT"
  - "Found X pairs"
  - "Bot is running"
  - Có thể có tín hiệu entry/exit

### 🔧 Bước 5: Test Hyperopt
- [ ] **5.1** Chạy hyperopt (10 epochs)
  ```bash
  freqtrade hyperopt -c config_mexc_dryrun.json --strategy TestMexcStrategy --epochs 10 --spaces buy
  ```
  **Kết quả mong đợi**:
  - Chạy thành công
  - Hiển thị kết quả tối ưu

## 🎯 Kết quả cuối cùng

### ✅ Thành công
- [ ] Tất cả 5 bước đều pass
- [ ] MEXC integration hoạt động tốt
- [ ] Có thể chuyển sang test với API key

### ❌ Cần sửa
- [ ] Có lỗi ở bước nào?
- [ ] Cần debug gì?
- [ ] Cần cập nhật code gì?

## 📝 Ghi chú

### Lỗi thường gặp:
1. **"Exchange not found"** → Cần kiểm tra import MEXC
2. **"Strategy not found"** → Cần kiểm tra file strategy
3. **"Download failed"** → Cần kiểm tra kết nối internet
4. **"Backtesting failed"** → Cần kiểm tra dữ liệu

### Logs quan trọng:
- `freqtrade.log` - Log chính
- `user_data/logs/` - Log chi tiết

## 🚀 Bước tiếp theo

Sau khi test thành công:
1. Tạo API key MEXC
2. Test với API key (vẫn dry-run)
3. Chuyển sang live trading (nếu muốn) 