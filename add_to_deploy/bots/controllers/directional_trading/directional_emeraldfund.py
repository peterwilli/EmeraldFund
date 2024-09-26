from typing import List

import pandas_ta as ta  # noqa: F401
import pandas as pd

from pydantic import Field, validator

from hummingbot.client.config.config_data_types import ClientFieldData
from hummingbot.data_feed.candles_feed.data_types import CandlesConfig
from hummingbot.strategy_v2.controllers.directional_trading_controller_base import (
    DirectionalTradingControllerBase,
    DirectionalTradingControllerConfigBase,
)


class DirectionalEmeraldFundControllerConfig(DirectionalTradingControllerConfigBase):
    controller_name = "directional_emeraldfund"
    candles_config: List[CandlesConfig] = []
    processor_code: str = Field(
        client_data=ClientFieldData(
            is_updatable=True,
            prompt_on_new=True,
            prompt=lambda mi: "Enter the processor code",
        )
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
    interval: str = Field(
        default="3m",
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the candle interval (e.g., 1m, 5m, 1h, 1d): ",
            prompt_on_new=False,
        ),
    )
    max_records: int = Field(
        default=100,
        client_data=ClientFieldData(
            prompt=lambda mi: "Enter the maximum amount of candles to process: ",
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


class DirectionalEmeraldFundController(DirectionalTradingControllerBase):
    def __init__(self, config: DirectionalEmeraldFundControllerConfig, *args, **kwargs):
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
        if hasattr(self.processor, "get_parameters"):
            parameters = self.processor.get_parameters()
            for k in parameters:
                param = parameters[k]
                setattr(self.processor, k, param["current"])
        super().__init__(config, *args, **kwargs)

    async def update_processed_data(self):
        candles = self.market_data_provider.get_candles_df(
            connector_name=self.config.candles_connector,
            trading_pair=self.config.candles_trading_pair,
            interval=self.config.interval,
            max_records=self.max_records,
        )
        self.processor.process_candles(candles)
        # Update processed data
        self.processed_data["signal"] = candles["signal"].iloc[-1]
        self.processed_data["features"] = candles
