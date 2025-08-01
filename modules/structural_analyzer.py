import pandas as pd

class StructuralAnalyzer:
    def __init__(self, config):
        self.config = config
        self.lookback = config['structural_parameters']['swing_point_lookback']

    def analyze(self, df: pd.DataFrame) -> dict:
        score = 0
        narrative = "Market structure is consolidating with no clear bias."
        try:
            atr_period = self.config['dynamic_risk_management']['atr_period']
            atr = (df['high'] - df['low']).rolling(window=atr_period).mean().iloc[-1]
            bos_threshold = self.config['structural_parameters']['bos_choch_threshold_atr'] * atr
            
            recent_high = df['high'].rolling(self.lookback).max().iloc[-2]
            recent_low = df['low'].rolling(self.lookback).min().iloc[-2]
            last_candle = df.iloc[-1]

            if last_candle['high'] > recent_high and last_candle['close'] < recent_high:
                score -= 0.5; narrative = f"Bearish Liquidity Sweep above swing high at {recent_high:.4f}."
            if last_candle['low'] < recent_low and last_candle['close'] > recent_low:
                score += 0.5; narrative = f"Bullish Liquidity Sweep below swing low at {recent_low:.4f}."
            if last_candle['close'] > recent_high + bos_threshold:
                score += 1.0; narrative = f"Bullish Break of Structure confirmed with a strong close above {recent_high:.4f}."
            if last_candle['close'] < recent_low - bos_threshold:
                score -= 1.0; narrative = f"Bearish Break of Structure confirmed with a strong close below {recent_low:.4f}."
        except IndexError:
            return {'score': 0, 'narrative': 'Not enough historical data for full structural analysis.'}

        return {'score': max(-1.0, min(1.0, score)), 'narrative': narrative}