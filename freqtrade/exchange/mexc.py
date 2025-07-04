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
from freqtrade.util.datetime_helpers import dt_from_ts


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
            "price": "default"  # Default price type for futures
        },
    }

    _supported_trading_mode_margin_pairs: list[tuple[TradingMode, MarginMode]] = [
        # TradingMode.SPOT always supported and not required in this list
        (TradingMode.FUTURES, MarginMode.ISOLATED),
        (TradingMode.FUTURES, MarginMode.CROSS),
    ]

    @property
    def _ccxt_config(self) -> dict:
        config = {}
        if self.trading_mode == TradingMode.SPOT:
            config.update({"options": {"defaultType": "spot"}})
        elif self.trading_mode == TradingMode.FUTURES:
            config.update({"options": {"defaultType": "swap"}})
        # Hardcode key/secret để test ổn định
        config["apiKey"] = "mx0vglaf7Q3iNkxBzA"
        config["secret"] = "0ebc0b45759449beaa40c07b4b4820a2"
        parent_config = super()._ccxt_config
        config.update(parent_config)
        
        # Force MEXC to use v3 API instead of v1
        config.update({
            "urls": {
                "api": {
                    "public": "https://contract.mexc.com/api/v3",
                    "private": "https://contract.mexc.com/api/v3",
                }
            }
        })
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

    def _get_positionType(self, side: BuySell, reduceOnly: bool):
        """
        Get position type for MEXC leverage setting.
        :param side: 'buy' or 'sell'
        :param reduceOnly: True if this is a reduce-only order
        :return: "1" for long, "2" for short
        """
        if not reduceOnly:
            # Enter position
            return "1" if side == "buy" else "2"
        else:
            # Exit position (reduce only)
            return "1" if side == "sell" else "2"

    @retrier
    def _lev_prep(self, pair: str, leverage: float, side: BuySell, accept_fail: bool = False):
        if self.trading_mode != TradingMode.SPOT:
            try:
                # Determine openType based on margin_mode
                open_type = "1" if self.margin_mode == MarginMode.ISOLATED else "2"
                
                res = self._api.set_leverage(
                    leverage=leverage,
                    symbol=pair,
                    params={
                        "openType": open_type,  # 1 for isolated, 2 for cross
                        "positionType": self._get_positionType(side, False),
                    },
                )
                self._log_exchange_response("set_leverage", res)

            except ccxt.DDoSProtection as e:
                raise DDosProtection(e) from e
            except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
                if not accept_fail:
                    raise TemporaryError(
                        f"Could not set leverage due to {e.__class__.__name__}. Message: {e}"
                    ) from e
            except ccxt.BaseError as e:
                raise OperationalException(e) from e

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
            
            # Add leverage parameter for isolated margin orders
            if self.margin_mode == MarginMode.ISOLATED:
                params["leverage"] = leverage
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

    async def _async_get_candle_history(
        self,
        pair: str,
        timeframe: str,
        candle_type: CandleType,
        since_ms: int | None = None,
    ) -> OHLCVResponse:
        """
        Override for MEXC to handle OHLCV properly.
        MEXC only supports [default, index, mark] price types.
        """
        try:
            # Fetch OHLCV asynchronously
            s = "(" + dt_from_ts(since_ms).isoformat() + ") " if since_ms is not None else ""
            logger.debug(
                "Fetching pair %s, %s, interval %s, since %s %s...",
                pair,
                candle_type,
                timeframe,
                since_ms,
                s,
            )
            
            # MEXC specific price type mapping
            params = deepcopy(self._ft_has.get("ohlcv_params", {}))
            candle_limit = self.ohlcv_candle_limit(
                timeframe, candle_type=candle_type, since_ms=since_ms
            )

            # Map candle types to MEXC supported price types
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
                # Funding rate is handled separately
                data = await self._fetch_funding_rate_history(
                    pair=pair,
                    timeframe=timeframe,
                    limit=candle_limit,
                    since_ms=since_ms,
                )
            else:
                # For any other candle type, use default
                params["price"] = "default"
            
            if candle_type != CandleType.FUNDING_RATE:
                # Add delay to avoid rate limiting
                import asyncio
                await asyncio.sleep(0.5)  # 500ms delay between requests
                
                # Retry logic for rate limiting
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        data = await self._api_async.fetch_ohlcv(
                            pair, timeframe=timeframe, since=since_ms, limit=candle_limit, params=params
                        )
                        break
                    except ccxt.ExchangeError as e:
                        if "请求频率过快" in str(e) and attempt < max_retries - 1:
                            logger.warning(f"Rate limit hit for {pair}, retrying in 2 seconds... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(2)
                            continue
                        else:
                            raise
            
            # Some exchanges sort OHLCV in ASC order and others in DESC.
            # Only sort if necessary to save computing time
            try:
                if data and data[0][0] > data[-1][0]:
                    data = sorted(data, key=lambda x: x[0])
            except IndexError:
                logger.exception("Error loading %s. Result was %s.", pair, data)
                return pair, timeframe, candle_type, [], self._ohlcv_partial_candle
                
            logger.debug("Done fetching pair %s, %s interval %s...", pair, candle_type, timeframe)
            return pair, timeframe, candle_type, data, self._ohlcv_partial_candle

        except ccxt.NotSupported as e:
            raise OperationalException(
                f"Exchange {self._api.name} does not support fetching historical "
                f"candle (OHLCV) data. Message: {e}"
            ) from e
        except ccxt.DDoSProtection as e:
            raise DDosProtection(e) from e
        except (ccxt.OperationFailed, ccxt.ExchangeError) as e:
            raise TemporaryError(
                f"Could not fetch historical candle (OHLCV) data "
                f"for {pair}, {timeframe}, {candle_type} due to {e.__class__.__name__}. "
                f"Message: {e}"
            ) from e
        except ccxt.BaseError as e:
            raise OperationalException(
                f"Could not fetch historical candle (OHLCV) data for "
                f"{pair}, {timeframe}, {candle_type}. Message: {e}"
            ) from e

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
        Nếu order_id là dry_run thì trả về None (hoặc raise ExchangeError dễ hiểu), tránh gọi lên sàn thật khi dry-run.
        """
        if order_id.startswith('dry_run_'):
            # Có thể trả về None hoặc raise ExchangeError với message rõ ràng
            raise ExchangeError(f"Order {order_id} is a dry-run order and does not exist on MEXC.")
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