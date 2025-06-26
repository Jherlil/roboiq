"""Risk management helpers."""

from utils import log

class RiskManager:
    """Manage trade amounts and stop conditions for each asset."""

    def __init__(
        self,
        stop_loss_amount: float,
        stop_loss_consecutive: int,
        stop_win_amount: float,
        stop_win_victories: int,
        strategy: str,
        martingale_factor: float,
        soros_level: float,
        use_martingale_if_high_chance: bool,
        use_soros_if_low_payout: bool,
        min_payout_for_soros: float,
        assets,
    ):
        self.stop_loss_amount = stop_loss_amount
        self.stop_loss_consecutive = stop_loss_consecutive
        self.stop_win_amount = stop_win_amount
        self.stop_win_victories = stop_win_victories
        self.strategy = strategy
        self.martingale_factor = martingale_factor
        self.soros_level = soros_level
        self.use_martingale_if_high_chance = use_martingale_if_high_chance
        self.use_soros_if_low_payout = use_soros_if_low_payout
        self.min_payout_for_soros = min_payout_for_soros
        self.assets = {
            asset: {
                "current_amount": 1,
                "losses_amount": 0,
                "wins_amount": 0,
                "consecutive_losses": 0,
                "consecutive_wins": 0,
                "last_result": None,
            }
            for asset in assets
        }

    def can_trade(self, asset):
        """Return ``True`` if trading on *asset* is allowed under risk limits."""
        a = self.assets[asset]
        if a["losses_amount"] >= self.stop_loss_amount:
            log(f"[{asset}] Stop loss global atingido — perdas: {a['losses_amount']}")
            return False
        if a["consecutive_losses"] >= self.stop_loss_consecutive:
            log(f"[{asset}] Stop loss consecutivo atingido — {a['consecutive_losses']} perdas seguidas")
            return False
        if a["wins_amount"] >= self.stop_win_amount:
            log(f"[{asset}] Stop win global atingido — ganhos: {a['wins_amount']}")
            return False
        if a["consecutive_wins"] >= self.stop_win_victories:
            log(f"[{asset}] Stop win consecutivo atingido — {a['consecutive_wins']} vitórias seguidas")
            return False
        return True

    def next_amount(self, asset, high_chance=False, payout=1.0):
        """Return the next order amount for *asset* based on strategy.

        The value ``current_amount`` is updated based on the result of the last
        trade stored in ``last_result``. Losses increase the stake according to
        the strategy while wins or triggered limits reset it to ``1``.
        """
        a = self.assets[asset]

        # Reset if any global/consecutive limit was hit
        if not self.can_trade(asset):
            a["current_amount"] = 1
            a["last_result"] = None
            return a["current_amount"]

        if a["last_result"] is not None:
            if a["last_result"]:
                a["current_amount"] = 1
            else:
                if self.strategy == "martingale" and (
                    high_chance or not self.use_martingale_if_high_chance
                ):
                    a["current_amount"] *= self.martingale_factor
                elif self.strategy == "soros" and (
                    not self.use_soros_if_low_payout
                    or payout >= self.min_payout_for_soros
                ):
                    a["current_amount"] *= self.soros_level
            a["last_result"] = None

        return a["current_amount"]

    def register_trade(self, asset, result):
        """Update statistics after a trade finishes."""
        a = self.assets[asset]
        if result:
            a["wins_amount"] += a["current_amount"]
            a["consecutive_wins"] += 1
            a["consecutive_losses"] = 0
        else:
            a["losses_amount"] += a["current_amount"]
            a["consecutive_losses"] += 1
            a["consecutive_wins"] = 0
        a["last_result"] = result
        log(
            f"[{asset}] Valor atual: {a['current_amount']} | perdas: {a['losses_amount']} | vitórias seguidas: {a['consecutive_wins']} | perdas seguidas: {a['consecutive_losses']} | ganhos totais: {a['wins_amount']}"
        )