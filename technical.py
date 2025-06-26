import os
os.environ.setdefault("PANDAS_TA_SUPPRESS", "1")  # Silence TA-Lib warnings
import pandas as pd
import pandas_ta as ta
from finta import TA
from utils import log

class TechnicalAnalyzer:
    """Compute technical indicators using pandas-ta and detect candlestick patterns with pure pandas logic via Finta."""

    def __init__(self, ma_fast: int = 20, ma_slow: int = 50, volume_period: int = 20):
        self.ma_fast = ma_fast
        self.ma_slow = ma_slow
        self.volume_period = volume_period

    def calculate_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add simple moving average columns to df using rolling mean."""
        df['MA_fast'] = df['close'].rolling(self.ma_fast).mean()
        df['MA_slow'] = df['close'].rolling(self.ma_slow).mean()
        return df

    def add_m5_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich df with recommended M5 indicators using pandas-ta functions."""
        df['VWAP'] = ta.vwap(
            high=df['high'], low=df['low'], close=df['close'], volume=df['volume']
        )
        supertrend = ta.supertrend(
            high=df['high'], low=df['low'], close=df['close'], length=10, multiplier=3
        )
        df['SUPERT'] = supertrend['SUPERT_10_3.0']
        df['EMA5'] = ta.ema(df['close'], length=5)
        df['EMA20'] = ta.ema(df['close'], length=20)
        df['EMA_CROSS'] = df['EMA5'] > df['EMA20']
        df['RSI7'] = ta.rsi(df['close'], length=7)
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD_HIST'] = macd['MACDh_12_26_9']
        bbands = ta.bbands(df['close'], length=20, std=2)
        df['BB_UP'] = bbands['BBU_20_2.0']
        df['BB_DN'] = bbands['BBL_20_2.0']
        adx = ta.adx(
            high=df['high'], low=df['low'], close=df['close'], length=14
        )
        df['ADX14'] = adx['ADX_14']
        df['ATR14'] = ta.atr(
            high=df['high'], low=df['low'], close=df['close'], length=14
        )
        return df

    def detect_trend(self, df: pd.DataFrame) -> str:
        """Return 'up', 'down' or 'flat' based on moving averages."""
        last = df.iloc[-1]
        if last['MA_fast'] > last['MA_slow']:
            return "up"
        elif last['MA_fast'] < last['MA_slow']:
            return "down"
        return "flat"

    def detect_breakout(self, df: pd.DataFrame, lookback: int = 50) -> str:
        """Detect breakout above resistance or below support.

        The support and resistance levels are calculated using
        :py:meth:`support_resistance` which requires at least two touches of
        each level within ``lookback`` candles.
        """
        support, resistance = self.support_resistance(df, lookback)
        if support is None or resistance is None:
            return None
        last_close = df['close'].iloc[-1]
        if resistance is not None and last_close > resistance:
            return "breakout_up"
        if support is not None and last_close < support:
            return "breakout_down"
        return None

    def detect_candlestick_patterns(self, df: pd.DataFrame) -> list:
        """Detect all candlestick patterns using pure-Python 'finta' library (no TA-Lib)."""
        patterns = []
        if df.empty:
            return patterns
        for name in dir(TA):
            if not name.startswith('CDL'):
                continue
            func = getattr(TA, name)
            try:
                series = func(df)
            except Exception:
                continue
            if hasattr(series, 'iloc') and series.iloc[-1] != 0:
                patterns.append((name.lower(), int(series.iloc[-1])))
        return patterns

    def support_resistance(self, df: pd.DataFrame, lookback: int = 50) -> tuple:
        """Return support and resistance touched at least twice.

        The function searches local minima and maxima within ``lookback``
        candles and only returns a level if it has been tested two or more
        times. ``None`` is returned for a level without confirmation.
        """
        recent = df.tail(lookback)
        tolerance = recent['close'].std() * 0.02 if len(recent) > 1 else 0

        lows = recent['low']
        highs = recent['high']

        local_min = (lows <= lows.shift(1)) & (lows <= lows.shift(-1))
        local_max = (highs >= highs.shift(1)) & (highs >= highs.shift(-1))

        support = None
        resistance = None

        if local_min.any():
            level = lows[local_min].min()
            touches = (abs(lows - level) <= tolerance).sum()
            if touches >= 2:
                support = level

        if local_max.any():
            level = highs[local_max].max()
            touches = (abs(highs - level) <= tolerance).sum()
            if touches >= 2:
                resistance = level

        return support, resistance

    def fibonacci_levels(self, df: pd.DataFrame) -> dict:
        """Return key Fibonacci retracement levels using pandas calculations."""
        swing_high = df['high'].max()
        swing_low = df['low'].min()
        diff = swing_high - swing_low
        levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        return {f'fib_{int(l*100)}': swing_low + diff * l for l in levels}

    def draw_trendlines(self, df: pd.DataFrame) -> dict:
        """Return basic trendline points for LTA and LTB using pandas."""
        top_idx = df['high'].idxmax()
        bottom_idx = df['low'].idxmin()
        return {
            'LTA': (bottom_idx, df.at[bottom_idx, 'low']),
            'LTB': (top_idx, df.at[top_idx, 'high'])
        }

    def validate_candle_pattern(self, candle: pd.Series, pattern_name: str) -> bool:
        """Stub for pattern validation."""
        return True