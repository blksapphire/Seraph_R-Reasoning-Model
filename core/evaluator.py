import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

class SeraphEvaluator:
    """
    Analyzes past trade performance and autonomously tunes the AI's strategy weights.
    This module creates the closed-loop learning mechanism.
    """
    def __init__(self, config):
        self.config = config
        self.ai_name = config["system_identity"]["name"]
        self.journal_path = config['evaluator_settings']['journal_file']
        logging.info(f"{self.ai_name} Evaluator module initialized.")

    def _connect_mt5(self):
        """Initializes a connection to the MT5 terminal."""
        if not mt5.initialize():
            logging.error(f"MT5 initialize() failed. Is the MT5 terminal running under Wine? Error: {mt5.last_error()}")
            return False
        if not mt5.login(self.config["mt5_credentials"]["login"], self.config["mt5_credentials"]["password"], self.config["mt5_credentials"]["server"]):
            logging.error(f"MT5 login() failed, error code = {mt5.last_error()}"); mt5.shutdown(); return False
        return True

    def analyze_and_adapt(self):
        """The main method to analyze performance and trigger adaptation."""
        logging.info("--- AUTONOMOUS PERFORMANCE EVALUATION & ADAPTATION CYCLE INITIATED ---")
        if not self._connect_mt5(): return

        try:
            journal_df = pd.read_json(self.journal_path, lines=True)
            journal_df['timestamp'] = pd.to_datetime(journal_df['timestamp'])
        except (FileNotFoundError, ValueError):
            logging.warning("Trade journal not found or is empty. Cannot evaluate performance.")
            mt5.shutdown()
            return

        start_date = journal_df['timestamp'].min() - timedelta(days=1)
        deals = mt5.history_deals_get(start_date, datetime.now())
        mt5.shutdown()

        if deals is None or len(deals) == 0:
            logging.warning("No trading deals found in MT5 history for this period.")
            return

        deals_df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
        deals_df = deals_df[deals_df['entry'] == mt5.DEAL_ENTRY_OUT] # We only care about closing deals for P/L
        deals_df['time'] = pd.to_datetime(deals_df['time'], unit='s')

        # Link trades from our journal to the broker's record of closed deals
        merged_df = pd.merge(journal_df, deals_df[['order', 'profit']], left_on='ticket', right_on='order')
        
        if merged_df.empty:
            logging.warning("Could not match journal entries to closed deals. Are trades still open?")
            return

        # Core Analysis: Calculate the correlation between each brain's score and the final profit
        scores_df = merged_df['scores'].apply(pd.Series)
        scores_df['profit'] = merged_df['profit']
        
        # We need both wins and losses to find a meaningful correlation
        if len(scores_df[scores_df['profit'] > 0]) == 0 or len(scores_df[scores_df['profit'] < 0]) == 0:
             logging.warning("Evaluation requires both winning and losing trades to adapt. Aborting cycle.")
             return

        correlation = scores_df.corr()['profit'].drop('profit')
        logging.info(f"Profit Correlation Analysis:\n{correlation.to_string()}")

        self._adapt_strategy(correlation)

    def _adapt_strategy(self, correlation: pd.Series):
        """Updates strategy weights based on the performance correlation."""
        current_weights = self.config['strategy_weights'].copy()
        learning_rate = self.config['evaluator_settings']['learning_rate']
        new_weights = current_weights.copy()
        
        for name, corr_value in correlation.items():
            analyzer_name = f"{name}_analysis" # e.g., 'technical' -> 'technical_analysis'
            if analyzer_name in new_weights and pd.notna(corr_value):
                # Apply the adjustment: increase weight for positive correlation, decrease for negative
                adjustment = corr_value * learning_rate
                new_weights[analyzer_name] += adjustment
        
        # Ensure weights are not negative and re-normalize to sum to 1.0
        total_weight = sum(max(0, w) for w in new_weights.values())
        if total_weight == 0:
            logging.error("All weights collapsed to zero during adaptation. Reverting to defaults.")
            return

        for name in new_weights:
            new_weights[name] = max(0, new_weights[name]) / total_weight
        
        logging.warning(f"ADAPTATION: Old Weights: { {k: round(v, 3) for k, v in current_weights.items()} }")
        logging.warning(f"ADAPTATION: Proposed New Weights: { {k: round(v, 3) for k, v in new_weights.items()} }")
        
        self._update_config_file(new_weights)

    def _update_config_file(self, new_weights):
        """Safely reads, modifies, and overwrites the config file."""
        try:
            with open('config.json', 'r+') as f:
                config_data = json.load(f)
                config_data['strategy_weights'] = new_weights
                f.seek(0)
                json.dump(config_data, f, indent=4)
                f.truncate()
            logging.info("SUCCESS: Configuration updated with new optimized weights.")
            with open("last_evaluation.log", "w") as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            logging.error(f"CRITICAL: Failed to write new weights to config.json! Error: {e}")