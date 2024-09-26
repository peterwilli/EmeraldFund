import pandas_ta as ta  # noqa: F401
from frontend.visualization import theme
import plotly.graph_objects as go

def clean_consecutive_values(s, steps=1):
    for idx in range(steps):
        s = s.where(s.ne(s.shift(idx + 1)), 0)
    return s

def get_market_making_traces(df, price_multiplier, spread_multiplier):
    tech_colors = theme.get_color_scheme()
    upper_bound = (df['close'] * (1 + price_multiplier)) * (1 + spread_multiplier)
    lower_bound = (df['close'] * (1 + price_multiplier)) * (1 - spread_multiplier)
    traces = [
        go.Scatter(x=df.index, y=upper_bound, line=dict(color=tech_colors['upper_band']),
                   name='Upper Band'),
        go.Scatter(x=df.index, y=lower_bound, line=dict(color=tech_colors['lower_band']),
                   name='Lower Band'),
    ]
    return traces
