import os
import json
import pickle
import logging
import time
from datetime import datetime
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import tensorflow as tf

from .trade_logger import TradeLogger
from .evaluator import SeraphEvaluator
from modules.technical_analyzer import TechnicalAnalyzer
from modules.structural_analyzer import StructuralAnalyzer
from modules.fundamental_analyzer import FundamentalAnalyzer

class SeraphROrchestrator:
    """
    The main decision-making engine of the Seraph-R system.
    It orchestrates the analysis of multiple symbols, synthesizes a final decision with
    clear reasoning, executes trades, and triggers the self-evaluation loop.
    """
    def __init__(self, config):
        self.config = config
        self.ai_name = config["system_identity"]["name"]
        self.is_trading_enabled = False
        self.trade_counter = 0

        # Initialize Brains and Logger
        self.tech_analyzer = TechnicalAnalyzer(config)
        self.struct_analyzer = StructuralAnalyzer(config)
        self.fund_analyzer = FundamentalAnalyzer(config)
        self.logger = TradeLogger(config)
        
        # Placeholders for per-symbol models and scalers
        self.models = {}
        self.scalers = {}
        self.feature_columns = {}
        
    def _connect_mt5(self):
        # ... [Same connection logic as Evaluator] ...
        pass

    def _load_all_models(self):
        """Pre-loads all necessary models and scalers into memory for performance."""
        logging.info("Pre-loading all trained models and scalers...")
        model_folder = self.config['model_architecture']['model_folder']
        for symbol in self.config['trading_parameters']['symbols_to_trade']:
            try:
                timeframe = self.config['trading_parameters']['timeframe']
                base_path = os.path.join(model_folder, f"{symbol}_{timeframe}")
                
                self.models[symbol] = tf.keras.models.load_model(f"{base_path}_model.h5")
                with open(f"{base_path}_scaler.pkl", 'rb') as f:
                    self.scalers[symbol] = pickle.load(f)
                with open(f"{base_path}_features.json", 'r') as f:
                    self.feature_columns[symbol] = json.load(f)
                
                logging.info(f"Successfully loaded model and assets for {symbol}.")
            except FileNotFoundError:
                logging.error(f"CRITICAL: Model or assets for {symbol} not found! This symbol will be skipped. Please train first.")
            except Exception as e:
                logging.error(f"Error loading assets for {symbol}: {e}")
        
    def get_live_data_for_analysis(self, symbol):
        """Fetches and prepares the latest market data for a given symbol."""
        timeframe = getattr(mt5, self.config['trading_parameters']['timeframe'])
        bars_to_fetch = self.config['model_architecture']['lookback_period'] + 150 # Fetch extra for indicator calculations
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars_to_fetch)
        
        if rates is None or len(rates) < bars_to_fetch:
            logging.warning(f"Could not retrieve enough live data for {symbol}.")
            return None

        df = pd.DataFrame(rates); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
        # Apply the exact same feature engineering as the trainer
        df = self.tech_analyzer.calculate_features(df)
        df.dropna(inplace=True)
        return df

    def run(self):
        """The main operational loop of the trading bot."""
        logging.info(f"--- {self.ai_name.upper()} ORCHESTRATOR DEPLOYED (REASONING & SELF-OPTIMIZING) ---")
        if not self._connect_mt5(): return
        
        self._load_all_models()
        self.is_trading_enabled = True
        
        while self.is_trading_enabled:
            for symbol in self.config['trading_parameters']['symbols_to_trade']:
                # Skip symbol if its model failed to load
                if symbol not in self.models: continue
                
                try:
                    logging.info(f"--- Analyzing {symbol} ---")
                    df_live = self.get_live_data_for_analysis(symbol)
                    if df_live is None: continue

                    tech_signal = self.tech_analyzer.analyze(df_live, self.models[symbol], self.scalers[symbol], self.feature_columns[symbol])
                    struct_signal = self.struct_analyzer.analyze(df_live)
                    fund_signal = self.fund_analyzer.get_news_sentiment_for_pair(symbol)
                    
                    scores = {'technical': tech_signal['score'], 'structural': struct_signal['score'], 'fundamental': fund_signal['score']}
                    weights = self.config['strategy_weights']
                    final_confidence = sum(scores[key] * weights[key] for key in scores)
                    
                    reasoning_block = (
                        f"SYNTHESIS FOR {symbol}:\n"
                        f"  [TA]: {tech_signal['narrative']}\n"
                        f"  [SMC]: {struct_signal['narrative']}\n"
                        f"  [FA]: {fund_signal['narrative']}\n"
                        f"  >> FINAL CONFIDENCE: {final_confidence:.3f}"
                    )
                    
                    logging.info(reasoning_block)
                    self._update_status("Thinking", reasoning_block, scores)

                    trade_signal = "HOLD"
                    if final_confidence > 0.55: trade_signal = "BUY"
                    elif final_confidence < -0.55: trade_signal = "SELL"
                        
                    if trade_signal != "HOLD":
                        self.execute_trade_with_atr(symbol, trade_signal, final_confidence, df_live)

                except Exception as e:
                    logging.critical(f"UNHANDLED EXCEPTION during analysis of {symbol}: {e}", exc_info=True)

            logging.info("All symbols analyzed. Waiting for next cycle...")
            self._check_for_evaluation()
            time.sleep(60 * 5)
            
    def _check_for_evaluation(self):
        """Checks if it's time to run the self-evaluation module."""
        eval_period = self.config['evaluator_settings']['evaluation_period_trades']
        if self.trade_counter > 0 and self.trade_counter % eval_period == 0:
            logging.warning("Evaluation trade count reached. Triggering self-optimization cycle.")
            evaluator = SeraphEvaluator(self.config)
            evaluator.analyze_and_adapt()
            
            # Reload config to get new weights
            with open('config.json', 'r') as f:
                self.config = json.load(f)
            logging.info("Configuration reloaded with new adapted weights.")

    def execute_trade_with_atr(self, symbol, signal, confidence, df):
        """Executes a trade with dynamically calculated SL/TP based on ATR."""
        atr_period = self.config['dynamic_risk_management']['atr_period']
        atr = (df['high'] - df['low']).rolling(window=atr_period).mean().iloc[-1]
        point = mt5.symbol_info(symbol).point
        
        sl_multiplier = self.config['dynamic_risk_management']['sl_atr_multiplier']
        tp_multiplier = self.config['dynamic_risk_management']['tp_atr_multiplier']
        
        sl_points = int((atr * sl_multiplier) / point)
        tp_points = int((atr * tp_multiplier) / point)
        
        price = mt5.symbol_info_tick(symbol).ask if signal == "BUY" else mt5.symbol_info_tick(symbol).bid
        sl = price - sl_points * point if signal == "BUY" else price + sl_points * point
        tp = price + tp_points * point if signal == "BUY" else price - tp_points * point

        request = {
            "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": self.config['trading_parameters']['lot_size'],
            "type": mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": price, "sl": sl, "tp": tp, "deviation": 20, "magic": 202403,
            "comment": f"{self.ai_name} {signal} {confidence:.2f}", "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"ORDER SEND FAILED for {symbol}: {result.comment}")
        else:
            logging.info(f"ORDER SENT for {symbol} {signal} @ {price}. Ticket: {result.order}")
            self.logger.log_execution(symbol, signal, confidence, {'technical':0,'structural':0,'fundamental':0}, result.order)
            self.trade_counter += 1

    def _update_status(self, status, reasoning, scores):
        """Writes the current status and reasoning to the status file for the dashboard."""
        status_payload = {
            'timestamp': datetime.now().isoformat(), 'ai_name': self.ai_name,
            'status': status, 'reasoning': reasoning, 'scores': {k:round(v,3) for k,v in scores.items()}
        }
        with open(self.config["system_files"]["status_file"], 'w') as f:
            json.dump(status_payload, f, indent=4)