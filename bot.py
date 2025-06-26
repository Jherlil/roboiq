import logging
import time
import pandas as pd
from iqoptionapi.stable_api import IQ_Option
from utils import log, load_config, entry_strength
from fundamental import FundamentalAnalyzer
from technical import TechnicalAnalyzer
from risk import RiskManager
from ml_model import MLModel

# Reduz nível de log global
logging.getLogger().setLevel(logging.CRITICAL)


def safe_get_candles_df(IQ, asset, timeframe, num_candles):
    """
    Tenta obter velas até 3 vezes, reconectando em caso de falha.
    Retorna um DataFrame com colunas OHLCV.
    """
    for attempt in range(3):
        try:
            root_logger = logging.getLogger()
            prev_level = root_logger.getEffectiveLevel()
            root_logger.setLevel(logging.WARNING)

            try:
                candles = IQ.get_candles(asset, timeframe, num_candles, time.time())
            finally:
                root_logger.setLevel(prev_level)

            if not candles or not isinstance(candles, list):
                raise ValueError("Resposta de velas inválida ou vazia")

            df = pd.DataFrame(candles)
            df.rename(columns={'min': 'low', 'max': 'high'}, inplace=True)
            df['time'] = pd.to_datetime(df['from'], unit='s')
            df.set_index('time', inplace=True)
            df.sort_index(inplace=True)
            return df
        except Exception as exc:
            log(f"safe_get_candles_df erro ({exc}), reconectando...", level="error")
            try:
                IQ.connect()
            except Exception as e:
                log(f"Falha ao reconectar: {e}", level="error")
            time.sleep(1)
    raise RuntimeError(f"Não foi possível obter velas para {asset} após várias tentativas")


def main():
    """Ponto de entrada para o robô de trading."""
    config = load_config("config.yaml")

    # Intervalos
    loop_interval = config.get('loop_interval', 5)
    trade_duration = config.get('trade_duration', int(config['timeframe_main'] / 60))

    IQ = IQ_Option(config["email"], config["password"])

    try:
        IQ.connect()
    except Exception as exc:
        log(f"Falha ao conectar: {exc}", level="error")
        return

    IQ.change_balance(config['account_type'].upper())

    fundamental = FundamentalAnalyzer(buffer_minutes=config['news_buffer_minutes'])
    technical = TechnicalAnalyzer(
        ma_fast=config['trend_ma_fast'],
        ma_slow=config['trend_ma_slow'],
        volume_period=config['volume_period'],
    )
    risk = RiskManager(
        stop_loss_amount=config['stop_loss_amount'],
        stop_loss_consecutive=config['stop_loss_consecutive'],
        stop_win_amount=config['stop_win_amount'],
        stop_win_victories=config['stop_win_victories'],
        strategy=config['strategy'],
        martingale_factor=config['martingale_factor'],
        soros_level=config['soros_level'],
        use_martingale_if_high_chance=config['use_martingale_if_high_chance'],
        use_soros_if_low_payout=config['use_soros_if_low_payout'],
        min_payout_for_soros=config['min_payout_for_soros'],
        assets=config['assets'],
    )
    ml = MLModel()

    daily_wins = 0
    last_trade_date = None

    while True:
        log("Loop principal...", level="info")

        ml.check_and_train_daily()

        if fundamental.check_high_impact_news():
            log("Aguardando notícia importante...", level="info")
            time.sleep(60)
            continue

        now = pd.Timestamp.now()
        if last_trade_date is None or last_trade_date.date() < now.date():
            daily_wins = 0
        last_trade_date = now

        if daily_wins >= config['stop_win_victories']:
            log("Stop win diário atingido — aguardando amanhã...", level="info")
            time.sleep(3600)
            continue

        all_profit = IQ.get_all_profit() or {}

        for asset in config['assets']:
            payout = all_profit.get(asset, {}).get('turbo', 0)
            if payout < config['min_payout'] or payout > config['max_payout']:
                continue

            try:
                df = safe_get_candles_df(IQ, asset, config['timeframe_main'], num_candles=100)
            except Exception as exc:
                log(f"Erro ao obter velas: {exc}", level="error")
                continue

            df = technical.calculate_moving_averages(df)
            df = technical.add_m5_indicators(df)

            breakout = technical.detect_breakout(df, lookback=config.get('breakout_lookback', 50))
            trend = technical.detect_trend(df)
            patterns = technical.detect_candlestick_patterns(df)
            pattern_name = patterns[0][0] if patterns else None
            last_candle = df.iloc[-1]

            avg_volume = df['volume'].rolling(config['volume_period']).mean().iloc[-1]
            volume_ratio = last_candle.volume / avg_volume if avg_volume > 0 else 0

            features = {
                "pattern_name": pattern_name or "unknown",
                "breakout": breakout or "none",
                "trend": trend,
                "volume_ratio": volume_ratio,
                "payout": payout,
                "ema_cross": bool(df['EMA_CROSS'].iloc[-1]),
                "rsi7": float(df['RSI7'].iloc[-1]) if 'RSI7' in df.columns else 50.0,
                "macd_hist": float(df['MACD_HIST'].iloc[-1]) if 'MACD_HIST' in df.columns else 0.0,
                "adx14": float(df['ADX14'].iloc[-1]) if 'ADX14' in df.columns else 0.0,
                "atr14": float(df['ATR14'].iloc[-1]) if 'ATR14' in df.columns else 0.0,
            }
            ml_high = ml.predict_high_chance(features)

            if not risk.can_trade(asset):
                continue

            super_dir = "up" if last_candle.close > last_candle.SUPERT else "down"
            direction = None
            if trend == "up" and super_dir == "up":
                direction = "call"
            elif trend == "down" and super_dir == "down":
                direction = "put"
            if not direction:
                continue

            signals = []
            debug_signals = {
                'breakout': breakout,
                'pattern': pattern_name,
                'volume_ratio': round(volume_ratio, 2),
                'trend': trend,
                'ema_cross': bool(df['EMA_CROSS'].iloc[-1]),
                'macd_hist': features['macd_hist'],
                'adx14': features['adx14'],
                'supertrend_dir': super_dir,
            }
            log(f"[{asset}] Debug signals: {debug_signals}", level="debug")

            if breakout:
                signals.append("breakout")
            if pattern_name:
                signals.append("pattern")
            if volume_ratio > 1.0:
                signals.append("volume")
            if trend != "flat":
                signals.append("trend")
            if df['EMA_CROSS'].iloc[-1]:
                signals.append("ema_cross")
            if ((trend == "up" and df['MACD_HIST'].iloc[-1] > 0) or (trend == "down" and df['MACD_HIST'].iloc[-1] < 0)):
                signals.append("macd")
            if df['ADX14'].iloc[-1] > 20:
                signals.append("adx")
            if ((trend == "up" and last_candle.close > last_candle.SUPERT) or (trend == "down" and last_candle.close < last_candle.SUPERT)):
                signals.append("supertrend")
            if ((trend == "up" and last_candle.close > last_candle.VWAP) or (trend == "down" and last_candle.close < last_candle.VWAP)):
                signals.append("vwap")
            if ml_high:
                signals.append("ml")

            strength = entry_strength(len(signals))
            if strength in ("nenhuma", "fraca"):
                log(f"[{asset}] Ignorando trade (confluências insuficientes: {len(signals)}) -> {strength}", level="info")
                continue

            amount = risk.next_amount(asset, high_chance=strength != "fraca", payout=payout)
            log(f"[{asset}] Entrando {direction} com {amount} — confluências:{len(signals)} ({strength})")

            status, order_id = False, None
            try:
                status, order_id = IQ.buy(amount, asset, direction, trade_duration)
            except Exception as exc:
                log(f"[{asset}] Erro ao enviar ordem: {exc}", level="error")

            if not status:
                log(f"[{asset}] Ordem não executada.", level="error")
                risk.register_trade(asset, False)
                ml.log_trade(features, False)
                continue

            log(f"[{asset}] Ordem enviada com sucesso: order_id={order_id}")

            try:
                result, _ = IQ.check_win(order_id)
            except Exception as exc:
                log(f"[{asset}] Erro ao verificar resultado: {exc}", level="error")
                result = False

            log(f"[{asset}] Resultado da ordem: {'Win' if result else 'Loss'}")

            risk.register_trade(asset, result)
            ml.log_trade(features, result)

            if result:
                daily_wins += 1

        log("Esperando próximo ciclo...", level="info")
        time.sleep(loop_interval)


if __name__ == "__main__":
    main()
