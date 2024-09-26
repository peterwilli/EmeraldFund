import asyncio
import json
import os
from textwrap import dedent
from datetime import datetime, timedelta, date
from io import StringIO
from pathlib import Path
from collections import OrderedDict
from typing import List
import numpy as np
import optuna
import streamlit as st
from frontend.pages.config.emeraldfund.code_replace import code_replace
from frontend.st_utils import get_backend_api_client
from ruamel import yaml
from frontend.pages.config.emeraldfund.core.utils import (
    create_slices_of_start_end_date,
)


def render_save_best_trial_config(config_base_default: str, config_data: dict):
    st.write("### Save the best config")
    backend_api_client = get_backend_api_client()
    all_configs = backend_api_client.get_all_controllers_config()
    config_bases = set(config_name["id"].split("_")[0] for config_name in all_configs)
    config_base = config_base_default.split("_")[0]
    if config_base in config_bases:
        config_tag = max(
            float(config["id"].split("_")[-1])
            for config in all_configs
            if config_base in config["id"]
        )
        version, tag = str(config_tag).split(".")
        config_tag = f"{version}.{int(tag) + 1}"
    else:
        config_tag = "0.1"
    c1, c2, c3 = st.columns([1, 1, 0.5])
    with c1:
        config_base = st.text_input(
            "Config Base", value=config_base, key="EMTrialConfigBase"
        )
    with c2:
        config_tag = st.text_input(
            "Config Tag", value=config_tag, key="EMTrialConfigTag"
        )
    with c3:

        def on_upload_click():
            config_data["id"] = f"{config_base}_{config_tag}"
            backend_api_client.add_controller_config(config_data)
            st.success("Config uploaded successfully!")

        st.button("Upload", key="EMTrialUploadConfig", on_click=on_upload_click)


async def run_backtesting_fn(
    study_name: str,
    processor,
    inputs,
    storage_path: Path,
    amount_of_trials: int,
    date_ranges: List[List[int]],
):
    import sys

    dir_path = os.path.dirname(os.path.realpath(__file__))
    sys.path.append(dir_path)
    sys.path.append("/backend-api/bots")
    from decimal import Decimal

    from controllers.directional_trading.directional_emeraldfund import (
        DirectionalEmeraldFundControllerConfig,
    )
    from core.backtesting.optimizer import (
        BacktestingConfig,
        BaseStrategyConfigGenerator,
        StrategyOptimizer,
    )
    from hummingbot.strategy_v2.executors.position_executor.data_types import (
        TrailingStop,
    )

    class EmeraldFundConfigGenerator(BaseStrategyConfigGenerator):
        def __init__(self, date_ranges, processor, inputs):
            super().__init__(date_ranges)
            self.processor = processor
            self.inputs = inputs

        def generate_config(self, trial) -> BacktestingConfig:
            inputs = self.inputs
            processor = self.processor
            parameters = processor.get_parameters()
            for k in parameters:
                param = parameters[k]
                kt = type(param["current"])
                param_max = param["max"]
                param_min = param["min"]
                if kt is int:
                    param["current"] = trial.suggest_int(k, param_min, param_max)
                elif kt is float:
                    param["current"] = trial.suggest_float(k, param_min, param_max)
                elif kt is str:
                    param["current"] = trial.suggest_categorical(k, param["choices"])
                else:
                    raise ValueError(f"unknown type {kt}")

            processor_code = code_replace(inputs["processor_code"], parameters)
            max_executors_per_side = trial.suggest_int("max_executors_per_side", 1, 10)
            take_profit = trial.suggest_float("take_profit", 0.01, 0.5, step=0.01)
            stop_loss = trial.suggest_float("stop_loss", 0.01, 0.1, step=0.01)
            trailing_stop_activation_price = trial.suggest_float(
                "trailing_stop_activation_price", 0.005, 0.05, step=0.001
            )
            trailing_delta_ratio = trial.suggest_float(
                "trailing_delta_ratio", 0.01, 0.5, step=0.01
            )
            trailing_stop_trailing_delta = (
                trailing_stop_activation_price * trailing_delta_ratio
            )
            time_limit = trial.suggest_int("time_limit", 60, 60 * 60 * 24, step=60)
            cooldown_time = trial.suggest_int(
                "cooldown_time", 60, 60 * 60 * 12, step=60
            )
            interval = trial.suggest_categorical(
                "interval", ["1m", "3m", "5m", "15m", "1h"]
            )

            # Create the strategy configuration
            config = DirectionalEmeraldFundControllerConfig(
                processor_code=processor_code,
                connector_name=inputs["connector_name"],
                trading_pair=inputs["trading_pair"],
                candles_connector=inputs["candles_connector"],
                candles_trading_pair=inputs["candles_trading_pair"],
                interval=interval,
                max_records=inputs["max_records"],
                total_amount_quote=Decimal(inputs["total_amount_quote"]),
                take_profit=Decimal(take_profit),
                stop_loss=Decimal(stop_loss),
                trailing_stop=TrailingStop(
                    activation_price=Decimal(trailing_stop_activation_price),
                    trailing_delta=Decimal(trailing_stop_trailing_delta),
                ),
                time_limit=time_limit,
                max_executors_per_side=max_executors_per_side,
                cooldown_time=cooldown_time,
            )

            # Return the configuration encapsulated in BacktestingConfig
            return BacktestingConfig(
                config=config, resolution=interval, date_ranges=date_ranges
            )

    config_generator = EmeraldFundConfigGenerator(
        date_ranges=date_ranges, processor=processor, inputs=inputs
    )

    sqlite_path = storage_path / Path("studies.db")
    optimizer = StrategyOptimizer(storage_name=f"sqlite:///{sqlite_path}")
    study = optimizer._create_study(study_name, load_if_exists=True)
    study_bar = st.progress(0, "Running study...")
    for i in range(amount_of_trials):
        trial = study.ask()
        if i > 0:
            trial_with_best_max_drawdown = max(
                study.best_trials, key=lambda t: t.values[1]
            )
            study_bar.progress(
                i / amount_of_trials,
                f"Running study... Best profit so far: {trial_with_best_max_drawdown.values[1]:.4f}%. Max Drawdown: {trial_with_best_max_drawdown.values[0]:.4f}%",
            )
        else:
            study_bar.progress(
                i / amount_of_trials,
                "Running study...",
            )
        try:
            # Run the async objective function and get the result
            value = await optimizer._async_objective(trial, config_generator)
            # Report the result back to the study
            study.tell(trial, value)
        except Exception as e:
            print(f"Error in _optimize_async: {str(e)}")
            study.tell(trial, state=optuna.trial.TrialState.FAIL)
    study_bar.progress(1.0, "Done!")
    trial_with_best_max_drawdown = max(study.best_trials, key=lambda t: t.values[1])
    render_save_best_trial_config(
        st.session_state["default_config"]["id"],
        json.loads(trial_with_best_max_drawdown.user_attrs["config"]),
    )


def optuna_section(inputs, backend_api_client, processor):
    st.write("### Optimization Backtesting")
    c1, c2, c3 = st.columns(3)

    with c1:
        study_name = st.text_input("Study name")
    with c2:
        backtesting_resolution = st.selectbox(
            "Backtesting Resolution",
            options=["1m", "3m", "5m", "15m", "30m", "1h", "1s"],
            index=0,
            key="optuna_backtesting_resolution",
        )
    with c3:
        trade_cost = st.number_input(
            "Trade Cost (%)",
            min_value=0.0,
            value=0.06,
            step=0.01,
            format="%.2f",
            key="optuna_trade_cost",
        )

    default_end_time = datetime.now().date() - timedelta(days=1)
    default_start_time = default_end_time - timedelta(days=2)
    c1, c2, c3 = st.columns(3)
    with c1:
        start_date = st.date_input(
            "Start Date", value=default_start_time, key="EMOptunaStartTime"
        )

    with c2:
        end_date = st.date_input(
            "End Date", value=default_end_time, key="EMOptunaEndTime"
        )

    break_up_sections = st.checkbox(
        "Break up start and end date into random sections",
        key="EMOptunaBreakUpDate",
        value=False,
    )

    with c3:
        amount_of_trials = st.number_input(
            "Amount of Trials", value=1000, key="EMOptunaAmountOfTrials"
        )

    if break_up_sections:
        c1, c2, c3 = st.columns(3)
        with c1:
            amount_of_sections = st.number_input("Amount of sections", value=3)
        with c2:
            break_up_gap = st.number_input(
                "Gap in days between sections", key="EMOptunaBreakUpGap", value=0
            )
        with c3:
            jitter = st.number_input("Jitter", key="EMOptunaJitter", value=0)
        sections = create_slices_of_start_end_date(
            int(datetime.combine(start_date, datetime.min.time()).timestamp()),
            int(datetime.combine(end_date, datetime.min.time()).timestamp()),
            amount_of_sections,
            break_up_gap,
            jitter,
        )
        sections_table = dedent("""
        | Section # | Start Date | End Date | Days | Total Days |
        | ------------- | ------------- | ------------- | ------------- | ---------- |
        """)

        def display_unix_timestamp(ts: int) -> str:
            return datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")

        total_days = 0
        for idx, section in enumerate(sections):
            start_date = display_unix_timestamp(section[0])
            end_date = display_unix_timestamp(section[1])
            days = (section[1] - section[0]) // 86400
            total_days += days
            sections_table += (
                f"{idx + 1} | {start_date} | {end_date} | {days} | {total_days}\n"
            )

        print(sections_table)
        st.write(sections_table)
    else:
        sections = [
            [
                int(datetime.combine(start_date, datetime.min.time()).timestamp()),
                int(datetime.combine(end_date, datetime.min.time()).timestamp()),
            ]
        ]
    run_backtesting = st.button("Run Optimization")
    if run_backtesting:
        if len(study_name) == 0:
            raise ValueError("Study name is required")
        dir_path = os.path.dirname(os.path.realpath(__file__))
        storage_path = Path(dir_path) / Path("data")
        storage_path.mkdir(parents=True, exist_ok=True)
        asyncio.run(
            run_backtesting_fn(
                study_name, processor, inputs, storage_path, amount_of_trials, sections
            )
        )
