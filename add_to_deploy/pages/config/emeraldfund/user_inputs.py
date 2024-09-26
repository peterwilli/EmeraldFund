from textwrap import dedent
import streamlit as st
from frontend.components.directional_trading_general_inputs import (
    get_directional_trading_general_inputs,
)
from frontend.components.market_making_general_inputs import (
    get_market_making_general_inputs,
)
from frontend.components.risk_management import get_risk_management_inputs
import importlib.util

# Check if the module exists
if importlib.util.find_spec("streamlit_code_editor") is None:
    # Install the module using pip
    import subprocess
    import sys

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "streamlit_code_editor"]
    )

    # Reload the module
    import importlib

    importlib.reload(importlib.util)

from code_editor import code_editor
from frontend.pages.config.emeraldfund.ai_input import ai_input


def user_inputs(controller_type: str):
    config = None
    if controller_type == "directional":
        default_config = st.session_state.get("default_config", {})
        (
            connector_name,
            trading_pair,
            leverage,
            total_amount_quote,
            max_executors_per_side,
            cooldown_time,
            position_mode,
            candles_connector_name,
            candles_trading_pair,
            interval,
        ) = get_directional_trading_general_inputs()

        sl, tp, time_limit, ts_ap, ts_delta, take_profit_order_type = (
            get_risk_management_inputs()
        )
        max_records = st.number_input(
            "Enter the maximum amount of candles to process",
            value=default_config.get("max_records", 100),
        )

        processor_code = default_config.get(
            "processor_code",
            dedent("""
            class SignalProcessor:
                def process_candles(self, candles):
                    candles["signal"] = 0
                    candles.loc[candles["close"] > candles["open"], "signal"] = 1 
                    return candles
        """).strip(),
        )
        ai_input()
        processor_code_editor = code_editor(processor_code)
        # Somehow code_editor returns an empty string if default value is used
        if processor_code_editor["text"] == "":
            processor_code_editor["text"] = processor_code

        config = {
            "controller_name": "directional_emeraldfund",
            "controller_type": "directional_trading",
            "manual_kill_switch": None,
            "candles_config": [],
            "connector_name": connector_name,
            "trading_pair": trading_pair,
            "total_amount_quote": total_amount_quote,
            "max_executors_per_side": max_executors_per_side,
            "cooldown_time": cooldown_time,
            "leverage": leverage,
            "max_records": max_records,
            "position_mode": position_mode,
            "candles_connector": candles_connector_name,
            "candles_trading_pair": candles_trading_pair,
            "interval": interval,
            "stop_loss": sl,
            "take_profit": tp,
            "time_limit": time_limit,
            "take_profit_order_type": take_profit_order_type.value,
            "trailing_stop": {"activation_price": ts_ap, "trailing_delta": ts_delta},
            "processor_code": processor_code_editor["text"],
        }

        return config
    if controller_type == "pmm":
        default_config = st.session_state.get("default_config", {})
        (
            connector_name,
            trading_pair,
            leverage,
            total_amount_quote,
            position_mode,
            cooldown_time,
            executor_refresh_time,
            candles_connector,
            candles_trading_pair,
            interval,
        ) = get_market_making_general_inputs(custom_candles=True)
        sl, tp, time_limit, ts_ap, ts_delta, take_profit_order_type = (
            get_risk_management_inputs()
        )
        max_records = st.number_input(
            "Enter the maximum amount of candles to process", value=100
        )

        processor_code = default_config.get(
            "processor_code",
            dedent("""
            class SignalProcessor:
                def process_candles(self, candles):
                    candles["price_multiplier"] = 0
                    candles["spread_multiplier"] = 0.01
                    return candles
        """).strip(),
        )
        ai_input()
        processor_code_editor = code_editor(processor_code)
        # Somehow code_editor returns an empty string if default value is used
        if processor_code_editor["text"] == "":
            processor_code_editor["text"] = processor_code

        config = {
            "controller_name": "pmm_emeraldfund",
            "controller_type": "market_making",
            "manual_kill_switch": None,
            "candles_config": [],
            "connector_name": connector_name,
            "trading_pair": trading_pair,
            "total_amount_quote": total_amount_quote,
            "executor_refresh_time": executor_refresh_time,
            "cooldown_time": cooldown_time,
            "leverage": leverage,
            "max_records": max_records,
            "position_mode": position_mode,
            "candles_connector": candles_connector,
            "candles_trading_pair": candles_trading_pair,
            "interval": interval,
            "stop_loss": sl,
            "take_profit": tp,
            "time_limit": time_limit,
            "take_profit_order_type": take_profit_order_type.value,
            "trailing_stop": {"activation_price": ts_ap, "trailing_delta": ts_delta},
            "processor_code": processor_code_editor["text"],
        }

    return config
