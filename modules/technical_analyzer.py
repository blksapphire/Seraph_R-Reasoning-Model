import logging
import pandas as pd
import numpy as np

class TechnicalAnalyzer:
    def __init__(self, config):
        self.config = config

    def calculate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        logging.info("Calculating technical features...")
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-10)
        df['rsi'] = 100 - (100 / (1 + rs))
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma_20'] + (bb_std * 2)
        df['bb_lower'] = df['sma_20'] - (bb_std * 2)
        df['fvg'] = 0
        for i in range(2, len(df)):
            if df['high'].iloc[i-2] < df['low'].iloc[i]: df.loc[df.index[i-1], 'fvg'] = 1
            elif df['low'].iloc[i-2] > df['high'].iloc[i]: df.loc[df.index[i-1], 'fvg'] = -1
        return df

    def analyze(self, df: pd.DataFrame, model, scaler, feature_columns) -> dict:
        if model is None or scaler is None:
            return {'score': 0, 'narrative': 'Technical model not loaded for this symbol.'}
        
        narrative_parts = []
        last_row = df.iloc[-1]
        
        if last_row['rsi'] > 70: narrative_parts.append(f"RSI ({last_row['rsi']:.1f}) is Overbought.")
        elif last_row['rsi'] < 30: narrative_parts.append(f"RSI ({last_row['rsi']:.1f}) is Oversold.")
        
        if last_row['macd'] > last_row['macd_signal']: narrative_parts.append("MACD is bullish (line over signal).")
        else: narrative_parts.append("MACD is bearish (signal over line).")

        lookback = self.config["model_architecture"]["lookback_period"]
        latest_data = df[feature_columns].tail(lookback)
        if len(latest_data) < lookback: return {'score': 0, 'narrative': 'Not enough data for TA sequence.'}
            
        scaled_data = scaler.transform(latest_data)
        X_pred = np.array([scaled_data])
        prediction_raw = model.predict(X_pred, verbose=0)[0][0]
        score = (prediction_raw - 0.5) * 2
        
        narrative_parts.append(f"LSTM predicts {prediction_raw:.1%} chance of upward movement.")
        full_narrative = " ".join(narrative_parts)
        
        return {'score': score, 'narrative': full_narrative}