#!/usr/bin/env python3
"""
Script để test MEXC dry-run tự động
"""
import subprocess
import sys
import os
import time
from datetime import datetime

def run_command(command, description):
    """Chạy command và hiển thị kết quả"""
    print(f"\n{'='*50}")
    print(f"🔄 {description}")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💻 Command: {command}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✅ Thành công!")
            print("📄 Output:")
            print(result.stdout)
        else:
            print("❌ Lỗi!")
            print("📄 Error:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Timeout - Command chạy quá lâu")
        return False
    except Exception as e:
        print(f"💥 Exception: {e}")
        return False
    
    return True

def main():
    """Main function"""
    print("🚀 Bắt đầu test MEXC dry-run")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Kiểm tra file config
    if not os.path.exists("config_mexc_dryrun.json"):
        print("❌ File config_mexc_dryrun.json không tồn tại!")
        return
    
    # Test 1: Kiểm tra strategy
    print("\n📋 Test 1: Kiểm tra strategy")
    success1 = run_command(
        "freqtrade list-strategies --strategy-path user_data/strategies",
        "Liệt kê strategies"
    )
    
    # Test 2: Download dữ liệu
    print("\n📊 Test 2: Download dữ liệu")
    success2 = run_command(
        "freqtrade download-data --exchange mexc --pairs BTC/USDT:USDT ETH/USDT:USDT --timeframe 5m --days 7",
        "Download dữ liệu MEXC"
    )
    
    # Test 3: Backtesting
    print("\n📈 Test 3: Backtesting")
    success3 = run_command(
        "freqtrade backtesting -c config_mexc_dryrun.json --strategy TestMexcStrategy --timerange 20241220-20241227",
        "Chạy backtesting"
    )
    
    # Test 4: Dry-run trading
    print("\n🤖 Test 4: Dry-run trading (5 phút)")
    success4 = run_command(
        "timeout 300 freqtrade trade -c config_mexc_dryrun.json --strategy TestMexcStrategy --dry-run-wallet 1000",
        "Chạy dry-run trading"
    )
    
    # Test 5: Hyperopt
    print("\n🔧 Test 5: Hyperopt")
    success5 = run_command(
        "freqtrade hyperopt -c config_mexc_dryrun.json --strategy TestMexcStrategy --epochs 10 --spaces buy",
        "Chạy hyperopt"
    )
    
    # Tổng kết
    print(f"\n{'='*50}")
    print("📊 TỔNG KẾT TEST")
    print(f"{'='*50}")
    
    tests = [
        ("Kiểm tra strategy", success1),
        ("Download dữ liệu", success2),
        ("Backtesting", success3),
        ("Dry-run trading", success4),
        ("Hyperopt", success5)
    ]
    
    passed = 0
    for test_name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 Kết quả: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 Tất cả tests đều thành công! MEXC integration hoạt động tốt.")
    else:
        print("⚠️ Một số tests thất bại. Vui lòng kiểm tra lại.")
    
    print(f"\n⏰ Hoàn thành lúc: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main() 