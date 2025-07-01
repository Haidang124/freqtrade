"""MEXC exchange subclass"""

import logging
from copy import deepcopy
from datetime import datetime
from typing import Any

import ccxt

from freqtrade.constants import BuySell
from freqtrade.enums import CandleType, MarginMode, PriceType, TradingMode
from freqtrade.exceptions import DDosProtection, ExchangeError, OperationalException, TemporaryError
from freqtrade.exchange import Exchange
from freqtrade.exchange.common import retrier
from freqtrade.exchange.exchange_types import CcxtOrder, FtHas, OHLCVResponse


logger = logging.getLogger(__name__)


class Mexc(Exchange):
    """
    MEXC exchange class. Contains adjustments needed for Freqtrade to work
    with this exchange.

    Please note that this exchange is not included in the list of exchanges
    officially supported by the Freqtrade development team. So some features
    may still not work as expected.
    """

    unified_account = False

    _ft_has: FtHas = {
        "ohlcv_has_history": True,
        "order_time_in_force": ["GTC", "FOK", "IOC"],
        "ws_enabled": True,
        "trades_has_history": False,  # Endpoint doesn't support pagination
        "fetch_orders_limit_minutes": 7 * 1440,  # 7 days
        "stoploss_on_exchange": True,
        "stoploss_order_types": {"limit": "limit", "market": "market"},
        "stoploss_blocks_assets": False,
    }

    _ft_has_futures: FtHas = {
        "ohlcv_has_history": True,
        "mark_ohlcv_timeframe": "4h",
        "funding_fee_timeframe": "8h",
        "funding_fee_candle_limit": 200,
        "stoploss_on_exchange": True,
        "stoploss_order_types": {"limit": "limit", "market": "market"},
        "stoploss_blocks_assets": False,
        "stop_price_prop": "stopPrice",
        "stop_price_type_field": "triggerBy",
        "stop_price_type_value_mapping": {
            PriceType.LAST: "LastPrice",
            PriceType.MARK: "MarkPrice",
            PriceType.INDEX: "IndexPrice",
        },
        "exchange_has_overrides": {
            "fetchOrder": True,
        },
        # MEXC specific OHLCV parameters for futures
        "ohlcv_params": {
            "price": "mark"  # Use mark price for futures
        },
    }

    _supported_trading_mode_margin_pairs: list[tuple[TradingMode, MarginMode]] = [
        # TradingMode.SPOT always supported and not required in this list
        (TradingMode.FUTURES, MarginMode.ISOLATED),
        (TradingMode.FUTURES, MarginMode.CROSS),
    ]

    @property
    def _ccxt_config(self) -> dict:
        # Parameters to add directly to ccxt sync/async initialization.
        config = {}
        if self.trading_mode == TradingMode.SPOT:
            config.update({"options": {"defaultType": "spot"}})
        elif self.trading_mode == TradingMode.FUTURES:
            config.update({"options": {"defaultType": "swap"}})
        config.update(super()._ccxt_config)
        return config

    def market_is_future(self, market: dict[str, Any]) -> bool:
        main = super().market_is_future(market)
        # For MEXC, we'll support USDT markets for futures
        return main and market.get("settle") == "USDT"

    @retrier
    def additional_exchange_init(self) -> None:
        """
        Additional exchange initialization logic.
        .api will be available at this point.
        Must be overridden in child methods if required.
        """
        try:
            if not self._config["dry_run"]:
                if self.trading_mode == TradingMode.FUTURES:
                    # Set position mode to one-way for MEXC
                    try:
                        position_mode = self._api.set_position_mode(False)
                        self._log_exchange_response("set_position_mode", position_mode)
                    except Exception as e:
                        logger.warning(f"Could not set position mode: {e}")
                        
                logger.info("MEXC: Exchange initialized successfully.")
        except ccxt.DDoSProtection as e:
            raise DDosProtection(e) from e
        except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f"Error in additional_exchange_init due to {e.__class__.__name__}. Message: {e}"
            ) from e
        except ccxt.BaseError as e:
            raise OperationalException(e) from e

    def _lev_prep(self, pair: str, leverage: float, side: BuySell, accept_fail: bool = False):
        if self.trading_mode != TradingMode.SPOT:
            params = {"leverage": leverage}
            self.set_margin_mode(pair, self.margin_mode, accept_fail=True, params=params)
            self._set_leverage(leverage, pair, accept_fail=True)

    def _get_params(
        self,
        side: BuySell,
        ordertype: str,
        leverage: float,
        reduceOnly: bool,
        time_in_force: str = "GTC",
    ) -> dict:
        params = super()._get_params(
            side=side,
            ordertype=ordertype,
            leverage=leverage,
            reduceOnly=reduceOnly,
            time_in_force=time_in_force,
        )
        if self.trading_mode == TradingMode.FUTURES:
            # MEXC specific parameters for futures
            params["position_idx"] = 0  # One-way position mode
        return params

    def _get_stop_params(self, side: BuySell, ordertype: str, stop_price: float) -> dict:
        params = super()._get_stop_params(
            side=side,
            ordertype=ordertype,
            stop_price=stop_price,
        )
        # MEXC specific stop order parameters
        if self.trading_mode == TradingMode.FUTURES:
            params["position_idx"] = 0
        return params

    def _order_needs_price(self, side: BuySell, ordertype: str) -> bool:
        # MEXC requires price for market orders in some cases
        return (
            ordertype != "market"
            or self._ft_has.get("marketOrderRequiresPrice", False)
        )

    def _async_get_candle_history(
        self,
        pair: str,
        timeframe: str,
        candle_type: CandleType,
        since_ms: int | None = None,
    ) -> OHLCVResponse:
        """
        Override for MEXC to handle futures OHLCV properly
        """
        try:
            # For MEXC futures, we need to specify price type
            params = deepcopy(self._ft_has.get("ohlcv_params", {}))
            
            if self.trading_mode == TradingMode.FUTURES:
                # MEXC futures requires specific price type
                if candle_type == CandleType.MARK:
                    params["price"] = "mark"
                elif candle_type == CandleType.FUTURES:
                    params["price"] = "mark"  # Use mark price for futures
                else:
                    params["price"] = "mark"  # Default to mark price
            
            # Call parent method with modified params
            return super()._async_get_candle_history(
                pair=pair,
                timeframe=timeframe,
                candle_type=candle_type,
                since_ms=since_ms,
            )
            
        except Exception as e:
            logger.warning(f"MEXC OHLCV fetch failed: {e}")
            # Fallback to parent method
            return super()._async_get_candle_history(
                pair=pair,
                timeframe=timeframe,
                candle_type=candle_type,
                since_ms=since_ms,
            )

    def dry_run_liquidation_price(
        self,
        pair: str,
        open_rate: float,  # Entry price of position
        is_short: bool,
        amount: float,
        stake_amount: float,
        leverage: float,
        wallet_balance: float,  # Or margin balance
        open_trades: list,
    ) -> float | None:
        """
        Calculate liquidation price for MEXC futures.
        
        MEXC liquidation price calculation:
        For isolated margin:
        Long: Liquidation Price = Entry Price - (Initial Margin - Maintenance Margin) / Contract Quantity
        Short: Liquidation Price = Entry Price + (Initial Margin - Maintenance Margin) / Contract Quantity
        
        :param pair: Pair to calculate liquidation price for
        :param open_rate: Entry price of position
        :param is_short: True if the trade is a short, false otherwise
        :param amount: Position size in contracts
        :param stake_amount: Stake amount in quote currency
        :param leverage: Leverage used
        :param wallet_balance: Wallet balance
        :param open_trades: List of open trades
        :return: Liquidation price or None if calculation fails
        """
        try:
            # Get market info for the pair
            market = self.markets.get(pair)
            if not market:
                return None
                
            # Get leverage tiers
            leverage_tiers = self._leverage_tiers.get(pair, [])
            if not leverage_tiers:
                return None
                
            # Find appropriate tier for our leverage
            tier = None
            for t in leverage_tiers:
                if leverage <= t.get("maxLeverage", float("inf")):
                    tier = t
                    break
                    
            if not tier:
                return None
                
            # Calculate liquidation price
            maintenance_margin_rate = tier.get("maintenanceMarginRate", 0.01)  # Default 1%
            initial_margin_rate = 1 / leverage
            
            margin_diff = initial_margin_rate - maintenance_margin_rate
            contract_value = amount * open_rate
            
            if is_short:
                liquidation_price = open_rate + (margin_diff * contract_value) / amount
            else:
                liquidation_price = open_rate - (margin_diff * contract_value) / amount
                
            return max(0, liquidation_price)
            
        except Exception as e:
            logger.warning(f"Could not calculate liquidation price for {pair}: {e}")
            return None

    def get_funding_fees(
        self, pair: str, amount: float, is_short: bool, open_date: datetime
    ) -> float:
        """
        Get funding fees for MEXC futures.
        
        :param pair: Trading pair
        :param amount: Position size
        :param is_short: True if short position
        :param open_date: Date when position was opened
        :return: Total funding fees
        """
        try:
            # Get funding rate history
            funding_rates = self._api.fetch_funding_rate_history(
                symbol=pair,
                since=int(open_date.timestamp() * 1000),
                limit=100
            )
            
            total_funding_fee = 0.0
            for rate_data in funding_rates:
                funding_rate = rate_data.get("fundingRate", 0)
                # Funding fees are paid every 8 hours
                funding_fee = amount * funding_rate * (8 / 24)  # 8 hours out of 24
                total_funding_fee += funding_fee
                
            return total_funding_fee
            
        except Exception as e:
            logger.warning(f"Could not fetch funding fees for {pair}: {e}")
            return 0.0

    def fetch_order(self, order_id: str, pair: str, params: dict | None = None) -> CcxtOrder:
        """
        Fetch order from MEXC.
        
        :param order_id: Order ID
        :param pair: Trading pair
        :param params: Additional parameters
        :return: Order information
        """
        try:
            return self._api.fetch_order(order_id, pair, params or {})
        except ccxt.OrderNotFound:
            # Try to fetch from stop orders if not found in regular orders
            try:
                return self._api.fetch_order(order_id, pair, {"stop": True})
            except ccxt.OrderNotFound:
                raise ExchangeError(f"Order {order_id} not found on MEXC")

    @retrier
    def get_leverage_tiers(self) -> dict[str, list[dict]]:
        """
        Get leverage tiers for MEXC futures.
        
        :return: Dictionary of leverage tiers by pair
        """
        try:
            if self.trading_mode == TradingMode.FUTURES:
                leverage_tiers = self._api.fetch_leverage_tiers()
                return leverage_tiers
            return {}
        except Exception as e:
            logger.warning(f"Could not fetch leverage tiers: {e}")
            return {} 