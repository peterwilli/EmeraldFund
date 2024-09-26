from numpy import place, result_type
from frontend.pages.config.emeraldfund.backtesting_optuna import optuna_section
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import traceback
import pandas_ta as ta  # noqa: F401
import pandas as pd

from backend.services.backend_api_client import BackendAPIClient
from CONFIG import BACKEND_API_HOST, BACKEND_API_PORT
from frontend.components.config_loader import get_default_config_loader
from frontend.components.executors_distribution import get_executors_distribution_inputs
from frontend.components.save_config import render_save_config

# Import submodules
from frontend.components.backtesting import backtesting_section
from frontend.pages.config.emeraldfund.utils import get_market_making_traces
from frontend.pages.config.emeraldfund.user_inputs import user_inputs
from frontend.pages.config.utils import get_max_records, get_candles
from frontend.st_utils import initialize_st_page
from frontend.st_utils import initialize_st_page, get_backend_api_client
from frontend.visualization import theme
from frontend.visualization.backtesting import create_backtesting_figure
from frontend.visualization.candles import get_candlestick_trace
from frontend.visualization.executors_distribution import (
    create_executors_distribution_traces,
)
from frontend.visualization.backtesting_metrics import (
    render_backtesting_metrics,
    render_close_types,
    render_accuracy_metrics,
)
from frontend.visualization.indicators import get_volume_trace
from frontend.visualization.utils import add_traces_to_fig
from frontend.visualization.signals import get_signal_traces

# Initialize the Streamlit page
initialize_st_page(title="PMM Emerlad Fund", icon="💚")
backend_api_client = get_backend_api_client()

# Page content
st.text(
    "This tool will let you create a config for PMM Emerald Fund, backtest and upload it to the Backend API."
)
get_default_config_loader("directional_emeraldfund")
# Get user inputs
inputs = user_inputs("directional")
st.session_state["default_config"].update(inputs)
st.write("### Visualizing MACD and NATR indicators for PMM Emerald Fund")
st.text(
    "The MACD is used to shift the mid price and the NATR to make the spreads dynamic. "
    "In the order distributions graph, we are going to see the values of the orders affected by the average NATR"
)
days_to_visualize = st.number_input(
    "Days to Visualize", min_value=1, max_value=365, value=3
)
# Load candle data
candles = get_candles(
    connector_name=inputs["candles_connector"],
    trading_pair=inputs["candles_trading_pair"],
    interval=inputs["interval"],
    days=days_to_visualize,
)
try:
    exec(inputs["processor_code"])
except Exception:
    st.error(f"Error running the processing code:\n\n```{traceback.format_exc()}```")
processor = SignalProcessor()
if hasattr(processor, "get_parameters"):
    parameters = processor.get_parameters()
    for k in parameters:
        param = parameters[k]
        setattr(processor, k, param["current"])
processed_candles = processor.process_candles(candles)


def get_custom_candle_trace_additions(candles, placement: str = "overlay"):
    result = []

    for col in candles.columns:
        key = f"line_{placement}"
        if col.startswith(key):
            result.append(
                go.Scatter(
                    x=candles.index,
                    y=candles[col],
                    name=col[len(key) + 1 :],
                    line=dict(color="blue"),
                )
            )

    return result


with st.expander("Visualizing Indicators", expanded=True):
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        subplot_titles=(
            "Candlestick with Market Making spread",
            "Strategy data",
            "Volume",
        ),
        row_heights=[0.6, 0.2, 0.2],
    )

    add_traces_to_fig(fig, [get_candlestick_trace(candles)], row=1, col=1)
    add_traces_to_fig(fig, get_custom_candle_trace_additions(candles), row=1, col=1)
    add_traces_to_fig(
        fig, get_custom_candle_trace_additions(candles, "separate"), row=2, col=1
    )
    add_traces_to_fig(fig, [get_volume_trace(candles)], row=3, col=1)
    add_traces_to_fig(
        fig,
        get_signal_traces(
            processed_candles[processed_candles["signal"] == 1],
            processed_candles[processed_candles["signal"] == -1],
        ),
        row=1,
        col=1,
    )
    fig.update_layout(**theme.get_default_layout())
    # Use Streamlit's functionality to display the plot
    st.plotly_chart(fig, use_container_width=True)

if hasattr(processor, "get_parameters"):
    optuna_section(inputs, backend_api_client, processor)
bt_results = backtesting_section(inputs, backend_api_client)
if bt_results:
    fig = create_backtesting_figure(
        df=bt_results["processed_data"],
        executors=bt_results["executors"],
        config=inputs,
    )
    c1, c2 = st.columns([0.9, 0.1])
    with c1:
        render_backtesting_metrics(bt_results["results"])
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        render_accuracy_metrics(bt_results["results"])
        st.write("---")
        render_close_types(bt_results["results"])
st.write("---")
render_save_config(
    st.session_state["default_config"]["id"], st.session_state["default_config"]
)
