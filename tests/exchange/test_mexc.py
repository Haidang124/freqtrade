"""Test MEXC exchange"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from freqtrade.enums import MarginMode, TradingMode
from tests.conftest import EXMS, get_patched_exchange


def test_mexc_initialization(default_conf, mocker):
    """Test MEXC exchange initialization"""
    exchange_name = "mexc"
    default_conf["dry_run"] = False
    default_conf["trading_mode"] = "futures"
    default_conf["margin_mode"] = "isolated"
    
    api_mock = MagicMock()
    api_mock.options = {"defaultType": "swap"}
    api_mock.set_position_mode = MagicMock(return_value={"retCode": 0})
    
    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange=exchange_name)
    
    assert exchange.name == "Mexc"
    assert exchange.trading_mode == TradingMode.FUTURES
    assert exchange.margin_mode == MarginMode.ISOLATED


def test_mexc_market_is_future(default_conf, mocker):
    """Test MEXC market_is_future method"""
    exchange_name = "mexc"
    default_conf["trading_mode"] = "futures"
    
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange=exchange_name)
    
    # Test USDT futures market
    usdt_market = {
        "symbol": "BTC/USDT:USDT",
        "type": "swap",
        "spot": False,
        "future": True,
        "linear": True,  # Required for futures markets
        "settle": "USDT"
    }
    assert exchange.market_is_future(usdt_market) is True
    
    # Test spot market
    spot_market = {
        "symbol": "BTC/USDT",
        "type": "spot",
        "spot": True,
        "future": False
    }
    assert exchange.market_is_future(spot_market) is False


def test_mexc_get_params(default_conf, mocker):
    """Test MEXC _get_params method"""
    exchange_name = "mexc"
    default_conf["trading_mode"] = "futures"
    
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange=exchange_name)
    
    params = exchange._get_params(
        side="buy",
        ordertype="limit",
        leverage=10.0,
        reduceOnly=False,
        time_in_force="GTC"
    )
    
    # Check that position_idx is set for futures
    assert "position_idx" in params
    assert params["position_idx"] == 0


def test_mexc_fetch_order(default_conf, mocker):
    """Test MEXC fetch_order method"""
    exchange_name = "mexc"
    default_conf["trading_mode"] = "futures"
    
    api_mock = MagicMock()
    order_response = {
        "id": "test_order_id",
        "symbol": "BTC/USDT:USDT",
        "status": "closed",
        "side": "buy",
        "type": "limit",
        "amount": 0.001,
        "price": 50000.0
    }
    api_mock.fetch_order = MagicMock(return_value=order_response)
    
    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange=exchange_name)
    
    order = exchange.fetch_order("test_order_id", "BTC/USDT:USDT")
    
    assert order["id"] == "test_order_id"
    assert order["symbol"] == "BTC/USDT:USDT"
    assert order["status"] == "closed"


def test_mexc_get_leverage_tiers(default_conf, mocker):
    """Test MEXC get_leverage_tiers method"""
    exchange_name = "mexc"
    default_conf["trading_mode"] = "futures"
    
    api_mock = MagicMock()
    leverage_tiers_response = {
        "BTC/USDT:USDT": [
            {
                "tier": 1,
                "minNotional": 0,
                "maxNotional": 10000,
                "maxLeverage": 125,
                "maintenanceMarginRate": 0.004
            }
        ]
    }
    api_mock.fetch_leverage_tiers = MagicMock(return_value=leverage_tiers_response)
    
    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange=exchange_name)
    
    leverage_tiers = exchange.get_leverage_tiers()
    
    assert "BTC/USDT:USDT" in leverage_tiers
    assert len(leverage_tiers["BTC/USDT:USDT"]) == 1
    assert leverage_tiers["BTC/USDT:USDT"][0]["maxLeverage"] == 125


def test_mexc_dry_run_liquidation_price(default_conf, mocker):
    """Test MEXC dry_run_liquidation_price method"""
    exchange_name = "mexc"
    default_conf["trading_mode"] = "futures"
    
    api_mock = MagicMock()
    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange=exchange_name)
    
    # Mock markets and leverage tiers
    exchange.markets = {
        "BTC/USDT:USDT": {
            "symbol": "BTC/USDT:USDT",
            "type": "swap",
            "taker": 0.0005,  # Required for liquidation calculation
            "inverse": False,  # Required for liquidation calculation
            "linear": True
        }
    }
    exchange._leverage_tiers = {
        "BTC/USDT:USDT": [
            {
                "maxLeverage": 125,
                "maintenanceMarginRate": 0.004,
                "minNotional": 0
            }
        ]
    }
    
    # Mock get_maintenance_ratio_and_amt method
    exchange.get_maintenance_ratio_and_amt = MagicMock(return_value=(0.004, None))
    
    liquidation_price = exchange.dry_run_liquidation_price(
        pair="BTC/USDT:USDT",
        open_rate=50000.0,
        is_short=False,
        amount=0.001,
        stake_amount=50.0,
        leverage=10.0,
        wallet_balance=1000.0,
        open_trades=[]
    )
    
    # Should return a valid liquidation price
    assert liquidation_price is not None
    assert liquidation_price > 0


def test_mexc_get_funding_fees(default_conf, mocker):
    """Test MEXC get_funding_fees method"""
    exchange_name = "mexc"
    default_conf["trading_mode"] = "futures"
    
    api_mock = MagicMock()
    funding_rates_response = [
        {
            "symbol": "BTC/USDT:USDT",
            "fundingRate": 0.0001,
            "timestamp": 1640995200000
        },
        {
            "symbol": "BTC/USDT:USDT",
            "fundingRate": 0.0002,
            "timestamp": 1641024000000
        }
    ]
    api_mock.fetch_funding_rate_history = MagicMock(return_value=funding_rates_response)
    
    exchange = get_patched_exchange(mocker, default_conf, api_mock, exchange=exchange_name)
    
    open_date = datetime(2022, 1, 1, 0, 0, 0)
    funding_fees = exchange.get_funding_fees(
        pair="BTC/USDT:USDT",
        amount=0.001,
        is_short=False,
        open_date=open_date
    )
    
    # Should return a valid funding fee
    assert funding_fees >= 0.0 