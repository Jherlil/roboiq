# tests/test_risk.py

import sys
from pathlib import Path
import pytest

# ajusta o path para conseguir importar RiskManager
sys.path.append(str(Path(__file__).resolve().parents[1]))
from risk import RiskManager

# lista dos ativos (Forex + OTC cripto)
ASSETS = [
    # Forex spots
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "AUDCAD", "EURGBP",
    "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "NZDCAD", "NZDJPY",
    # Forex OTC
    "EURUSD-OTC", "GBPUSD-OTC", "USDJPY-OTC", "AUDUSD-OTC", "AUDCAD-OTC", "EURGBP-OTC",
    "USDCHF-OTC", "NZDUSD-OTC", "EURJPY-OTC", "GBPJPY-OTC", "NZDCAD-OTC", "NZDJPY-OTC",
    # Cripto OTC na IQ Option
    "BTCUSD-OTC", "ETHUSD-OTC", "LTCUSD-OTC", "XRPUSD-OTC",
    "BCHUSD-OTC", "EOSUSD-OTC", "TRXUSD-OTC", "DASHUSD-OTC", "XMRUSD-OTC"
]


@pytest.fixture
def rm_limits():
    return RiskManager(
        cash=10, stake=2,
        max_loss=10, max_trades=3,
        mode='normal', multiplier=2, soros_multiplier=3,
        stop_on_loss=True, stop_on_win=True,
        win_rate=0.8, assets=ASSETS
    )

@pytest.fixture
def rm_martingale():
    return RiskManager(
        cash=100, stake=10,
        max_loss=100, max_trades=10,
        mode='martingale', multiplier=2, soros_multiplier=3,
        stop_on_loss=True, stop_on_win=True,
        win_rate=0.8, assets=ASSETS
    )

@pytest.fixture
def rm_soros():
    return RiskManager(
        cash=100, stake=10,
        max_loss=100, max_trades=10,
        mode='soros', multiplier=2, soros_multiplier=3,
        stop_on_loss=True, stop_on_win=True,
        win_rate=0.8, assets=ASSETS
    )

def test_can_trade_limits_all_assets(rm_limits):
    for asset in ASSETS:
        # no início, pode operar
        assert rm_limits.can_trade(asset), f"deveria poder operar {asset}"
        # forçamos perdas acima do limite
        rm_limits.assets[asset]['losses_amount'] = rm_limits.max_loss + 5
        assert not rm_limits.can_trade(asset), f"não deveria poder operar {asset} após perdas"

def test_next_amount_martingale_all_assets(rm_martingale):
    for asset in ASSETS:
        rm = rm_martingale
        rm.register_trade(asset, won=False)
        # após perda, valor é multiplicado
        assert rm.next_amount(asset, high_chance=True) == rm.multiplier, \
            f"martingale para {asset} deveria dar {rm.multiplier}"
        rm.register_trade(asset, won=True)
        # após ganho, valor volta ao mínimo (1 unidade)
        assert rm.next_amount(asset, high_chance=True) == 1, \
            f"martingale reset para {asset} deveria dar 1"

def test_next_amount_soros_all_assets(rm_soros):
    for asset in ASSETS:
        rm = rm_soros
        # simula derrota: valor aumenta pelo soros_multiplier
        rm.register_trade(asset, won=False)
        expected = rm.multiplier + rm.soros_multiplier
        assert rm.next_amount(asset, high_chance=True, payout=0.9) == expected, \
            f"soros para {asset} deveria dar {expected}"
        # simula vitória: reset
        rm.register_trade(asset, won=True)
        assert rm.next_amount(asset) == 1, \
            f"soros reset para {asset} deveria dar 1"

def test_next_amount_reset_on_limit_all_assets(rm_martingale):
    for asset in ASSETS:
        rm = RiskManager(
            cash=5, stake=1,
            max_loss=10, max_trades=3,
            mode='martingale', multiplier=2, soros_multiplier=3,
            stop_on_loss=True, stop_on_win=True,
            win_rate=0.8, assets=ASSETS
        )
        # força perdas acima do limite e valor alto atual
        rm.assets[asset]['losses_amount'] = rm.max_loss + 1
        rm.assets[asset]['current_amount'] = 4
        # deve resetar para o valor mínimo (1)
        assert rm.next_amount(asset) == 1, f"reset no limite para {asset} deveria dar 1"
