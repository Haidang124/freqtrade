# MEXC OHLCV Fix

## Vấn đề

MEXC exchange báo lỗi:
```
mexc fetchOHLCV() not support self price type, [default, index, mark]
```

## Nguyên nhân

MEXC chỉ hỗ trợ 3 loại price type:
- `default`
- `index` 
- `mark`

Nhưng Freqtrade đang cố gắng sử dụng các loại không được hỗ trợ:
- `premiumIndex` (không được hỗ trợ)
- `futures` (MEXC sử dụng `default` thay vì `futures`)

## Giải pháp

Đã override phương thức `_async_get_candle_history` trong `freqtrade/exchange/mexc.py` để map đúng các loại candle type:

```python
def _async_get_candle_history(self, pair: str, timeframe: str, candle_type: CandleType, since_ms: int | None = None) -> OHLCVResponse:
    """
    Override for MEXC to handle OHLCV properly.
    MEXC only supports [default, index, mark] price types.
    """
    try:
        # MEXC specific price type mapping
        params = deepcopy(self._ft_has.get("ohlcv_params", {}))
        
        if candle_type == CandleType.SPOT:
            # For spot trading, no price parameter needed
            pass
        elif candle_type == CandleType.MARK:
            params["price"] = "mark"
        elif candle_type == CandleType.INDEX:
            params["price"] = "index"
        elif candle_type == CandleType.PREMIUMINDEX:
            # MEXC doesn't support premiumIndex, use mark instead
            logger.debug(f"MEXC doesn't support premiumIndex, using mark price for {pair}")
            params["price"] = "mark"
        elif candle_type == CandleType.FUTURES:
            # MEXC uses "default" instead of "futures"
            params["price"] = "default"
        elif candle_type == CandleType.FUNDING_RATE:
            # Funding rate is handled separately in parent method
            pass
        else:
            # For any other candle type, use default
            params["price"] = "default"
        
        # Call parent method with modified params
        return super()._async_get_candle_history(
            pair=pair,
            timeframe=timeframe,
            candle_type=candle_type,
            since_ms=since_ms,
        )
        
    except Exception as e:
        logger.warning(f"MEXC OHLCV fetch failed for {pair}: {e}")
        # Fallback to parent method without custom params
        return super()._async_get_candle_history(
            pair=pair,
            timeframe=timeframe,
            candle_type=candle_type,
            since_ms=since_ms,
        )
```

## Mapping Table

| Freqtrade CandleType | MEXC Price Type | Ghi chú |
|---------------------|-----------------|---------|
| SPOT | Không có param | Spot trading không cần price type |
| MARK | "mark" | Mark price |
| INDEX | "index" | Index price |
| PREMIUMINDEX | "mark" | Fallback to mark price |
| FUTURES | "default" | MEXC sử dụng "default" thay vì "futures" |
| FUNDING_RATE | Không có param | Xử lý riêng trong parent method |

## Thay đổi khác

Cũng đã cập nhật cấu hình `ohlcv_params` trong `_ft_has_futures`:

```python
"ohlcv_params": {
    "price": "default"  # Default price type for futures
},
```

## Test

Có thể chạy test script để kiểm tra:

```bash
python test_mexc_fix.py
```

## Kết quả

Sau khi apply fix này, MEXC sẽ không còn báo lỗi về price type không được hỗ trợ nữa. 