import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1]))
from technical import TechnicalAnalyzer


def test_breakout_repeated_level():
    ta = TechnicalAnalyzer()
    df = pd.DataFrame({
        'open':  [1, 1.05, 1.07, 1.08, 1.09, 1.1],
        'high':  [1.1, 1.1, 1.09, 1.1, 1.1, 1.15],
        'low':   [1, 1.02, 1.04, 1.05, 1.05, 1.08],
        'close': [1.05, 1.08, 1.07, 1.09, 1.1, 1.12],
        'volume':[1]*6,
    })
    assert ta.detect_breakout(df, lookback=5) == 'breakout_up'


def test_no_breakout_without_touches():
    ta = TechnicalAnalyzer()
    df = pd.DataFrame({
        'open':  [1, 1.05, 1.07, 1.08],
        'high':  [1.1, 1.05, 1.06, 1.07],
        'low':   [0.9, 0.95, 0.96, 0.97],
        'close': [1.05, 1.04, 1.05, 1.06],
        'volume':[1]*4,
    })
    assert ta.detect_breakout(df, lookback=4) is None
