import os
import json
import pickle
import logging
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

from modules.technical_analyzer import TechnicalAnalyzer

class SeraphTrainer:
    """
    Trains specialized LSTM models for each financial symbol specified in the config.
    Each symbol gets its own model, scaler, and feature set, acknowledging their unique behaviors.
    """
    def __init__(self, config):
        self.config = config
        self.ai_name = config["system_identity"]["name"]
        logging.info(f"{self.ai_name} Trainer initialized.")
        self.tech_analyzer = TechnicalAnalyzer(config)

    def _connect_mt5(self):
        # ... [Same connection logic as other modules] ...
        pass

    def train_all_models(self):
        """The main entry point to train a model for every symbol in the config."""
        symbols = self.config['trading_parameters']['symbols_to_trade']
        logging.info(f"Initiating training for all configured symbols: {symbols}")
        
        model_folder = self.config['model_architecture']['model_folder']
        if not os.path.exists(model_folder):
            os.makedirs(model_folder)
            logging.info(f"Created models directory at: {model_folder}")
            
        if not self._connect_mt5(): return

        for symbol in symbols:
            logging.info(f"--- Starting Training Cycle for {symbol} ---")
            self._train_single_model(symbol)
        
        mt5.shutdown()
        logging.info("All training cycles complete. MT5 connection closed.")

    def _train_single_model(self, symbol: str):
        """Contains the full logic for fetching data and training a model for one symbol."""
        # 1. Fetch Data
        timeframe = getattr(mt5, self.config['trading_parameters']['timeframe'])
        bars = self.config["training_settings"]["historical_data_bars"]
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        
        if rates is None or len(rates) < bars:
            logging.error(f"Could not fetch sufficient training data for {symbol}. Skipping.")
            return

        df = pd.DataFrame(rates); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
        
        # 2. Engineer Features
        df = self.tech_analyzer.calculate_features(df)
        df.dropna(inplace=True)
        
        # 3. Create Sequences and Save Assets
        feature_columns = ['close', 'high', 'low', 'open', 'tick_volume', 'sma_20', 'sma_50', 'ema_12', 'ema_26', 'macd', 'macd_signal', 'rsi', 'bb_upper', 'bb_lower', 'fvg']
        available_features = [col for col in feature_columns if col in df.columns]
        
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(df[available_features])
        
        lookback = self.config["model_architecture"]["lookback_period"]
        X, y = [], []
        for i in range(lookback, len(scaled_data)):
            X.append(scaled_data[i-lookback:i, :])
            y.append(1 if df['close'].iloc[i] > df['close'].iloc[i-1] else 0)
        X, y = np.array(X), np.array(y)
        
        # 4. Define Dynamic Paths for Saving
        timeframe_str = self.config['trading_parameters']['timeframe']
        base_path = os.path.join(self.config['model_architecture']['model_folder'], f"{symbol}_{timeframe_str}")
        model_path = f"{base_path}_model.h5"
        scaler_path = f"{base_path}_scaler.pkl"
        features_path = f"{base_path}_features.json"

        with open(scaler_path, 'wb') as f: pickle.dump(scaler, f)
        with open(features_path, 'w') as f: json.dump(available_features, f)
        logging.info(f"Scaler and feature list for {symbol} saved.")
        
        # 5. Build and Train Model
        model = self._build_model((X.shape[1], X.shape[2]))
        
        callbacks = [
            EarlyStopping(monitor='val_loss', patience=10, verbose=1, restore_best_weights=True),
            ModelCheckpoint(filepath=model_path, save_best_only=True, monitor='val_loss', verbose=1)
        ]
        
        logging.info(f"Beginning model training for {symbol}. Training samples: {len(X)}")
        model.fit(X, y, 
            epochs=self.config["training_settings"]["epochs"],
            batch_size=self.config["training_settings"]["batch_size"],
            validation_split=0.2,
            callbacks=callbacks,
            verbose=2)
        logging.info(f"--- Training for {symbol} Complete. Model saved to {model_path} ---")

    def _build_model(self, input_shape):
        """Builds the LSTM neural network architecture."""
        model = Sequential([
            LSTM(100, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(100, return_sequences=False),
            Dropout(0.2),
            Dense(50, activation='relu'),
            Dense(1, activation='sigmoid')
        ])
        model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
        return model