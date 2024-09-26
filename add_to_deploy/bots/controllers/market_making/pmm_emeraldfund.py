from decimal import Decimal
from typing import List

import pandas_ta as ta  # noqa: F401
import pandas as pd
from pydantic import Field, validator

from hummingbot.client.config.config_data_types import ClientFieldData
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.strategy_v2.controllers.market_making_controller_base import (
    MarketMakingControllerBase,
    MarketMakingControllerConfigBase,
)
from hummingbot.strategy_v2.executors.position_executor.data_types import (
    PositionExecutorConfig,
)


class PMMEmeraldFund(MarketMakingControllerConfigBase):
    controller_name = "pmm_emeraldfund"
    candles_config: List[CandlesConfig] = []
    processor_code: str = Field(
        client_data=ClientFieldData(
            is_updatable=True,
            prompt_on_new=True,
            prompt=lambda mi: "Enter the processor code",
        )
    )
    buy_spreads: List[float] = Field(
        default="1,2,4",
        client_data=ClientFieldData(
            is_updatable=True,
            prompt_on_new=True,
            prompt=lambda mi: "Enter a comma-separated list of buy spreads (e.g., '0.01, 0.02'):",
        ),
    )
    buy_spreads: List[float] = Field(
        default="1,2,4",
        client_data=ClientFieldData(
            is_updatable=True,
            prompt_on_new=True,
            prompt=lambda mi: "Enter a comma-separated list of buy spreads (e.g., '0.01, 0.02'):",
        ),
    )
    sell_spreads: List[float] = Field(
        default="1,2,4",
        client_data=ClientFieldData(
            is_updatable=True,
            prompt_on_new=True,
            prompt=lambda mi: "Enter a comma-separated list of sell spreads (e.g., '0.01, 0.02'):",
        ),
    )
    candles_connector: str = Field(
        default=None,
        client_data=ClientFieldData(
            prompt_on_new=True,
            prompt=lambda mi: "Enter the connector for the candles data, leave empty to use the same exchange as the connector: ",
        ),
    )
    candles_trading_pair: str = Field(
        default=None,
        client_data=ClientFieldData(
            prompt_on_new=True,
            prompt=lambda mi: "Enter the trading pair for the candles data, leave empty to use the same trading pair as the connector: ",
        ),
    )
    max_records: int = Field(
        default=100,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the maximum amount of candles to process: ",
            prompt_on_new=False,
        ),
    )
    interval: str = Field(
        default="3m",
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the candle interval (e.g., 1m, 5m, 1h, 1d): ",
            prompt_on_new=False,
        ),
    )

    @validator("candles_connector", pre=True, always=True)
    def set_candles_connector(cls, v, values):
        if v is None or v == "":
            return values.get("connector_name")
        return v

    @validator("candles_trading_pair", pre=True, always=True)
    def set_candles_trading_pair(cls, v, values):
        if v is None or v == "":
            return values.get("trading_pair")
        return v


class EmeraldFundPMMController(MarketMakingControllerBase):
    """
    This is a dynamic version of the PMM controller.It uses the MACD to shift the mid-price and the NATR
    to make the spreads dynamic. It also uses the Triple Barrier Strategy to manage the risk.
    """

    def __init__(self, config: PMMEmeraldFund, *args, **kwargs):
        self.config = config
        self.max_records = self.config.max_records
        if len(self.config.candles_config) == 0:
            self.config.candles_config = [
                CandlesConfig(
                    connector=config.candles_connector,
                    trading_pair=config.candles_trading_pair,
                    interval=config.interval,
                    max_records=self.max_records,
                )
            ]
        local_obj = {}
        exec(self.config.processor_code, dict(ta=ta, pd=pd), local_obj)
        self.processor = local_obj["SignalProcessor"]()
        super().__init__(config, *args, **kwargs)

    async def update_processed_data(self):
        candles = self.market_data_provider.get_candles_df(
            connector_name=self.config.candles_connector,
            trading_pair=self.config.candles_trading_pair,
            interval=self.config.interval,
            max_records=self.max_records,
        )
        self.processor.process_candles(candles)
        candles["reference_price"] = candles["close"] * (
            1 + candles["price_multiplier"]
        )
        self.processed_data = {
            "reference_price": Decimal(candles["reference_price"].iloc[-1]),
            "spread_multiplier": Decimal(1)
            + Decimal(candles["spread_multiplier"].iloc[-1]),
            "features": candles,
        }

    def get_executor_config(self, level_id: str, price: Decimal, amount: Decimal):
        trade_type = self.get_trade_type_from_level_id(level_id)
        return PositionExecutorConfig(
            timestamp=self.market_data_provider.time(),
            level_id=level_id,
            connector_name=self.config.connector_name,
            trading_pair=self.config.trading_pair,
            entry_price=price,
            amount=amount,
            triple_barrier_config=self.config.triple_barrier_config,
            leverage=self.config.leverage,
            side=trade_type,
        )
