class SignalProcessor:
    def get_strategy_type(self):
        return "directional"

    def get_parameters(self):
        return {
            "sma_period_1": {"current": 9, "max": 45, "min": 1},
            "sma_period_2": {"current": 10, "max": 45, "min": 1},
            "sma_treshold": {"current": 0.1, "max": 0.8, "min": 0.2},
        }

    def normalize(self, x):
        import numpy as np

        divider = np.abs(x).max()
        if divider == 0:
            return x
        else:
            return x / divider

    def calculate_sma(self, candles):
        import numpy as np

        sma_1 = ta.sma(
            (candles["close"] + candles["high"] + candles["low"]) / 3,
            self.sma_period_1,
        )
        sma_2 = ta.sma(
            (candles["close"] + candles["high"] + candles["low"]) / 3,
            self.sma_period_1 + self.sma_period_2,
        )
        sma_delta = (sma_1 - sma_2) / np.maximum(sma_1, sma_2)
        return self.normalize(sma_delta)

    def process_candles(self, candles):
        candles["signal"] = 0
        candles["line_separate_sma_delta"] = self.calculate_sma(candles)
        candles.loc[
            candles["line_separate_sma_delta"] > self.sma_treshold, "signal"
        ] = 1
        candles.loc[
            candles["line_separate_sma_delta"] < -1 * self.sma_treshold, "signal"
        ] = -1

        return candles

