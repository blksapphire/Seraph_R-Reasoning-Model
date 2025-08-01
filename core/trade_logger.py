import json
from datetime import datetime
import logging

class TradeLogger:
    """
    A dedicated class for logging the complete context of a trade decision to a journal file.
    This journal is used by the Evaluator module for performance analysis.
    """
    def __init__(self, config):
        """Initializes the logger with the path to the journal file from the config."""
        self.journal_path = config['evaluator_settings']['journal_file']

    def log_execution(self, symbol: str, signal: str, confidence_score: float, scores_breakdown: dict, ticket_id: int):
        """
        Writes a detailed entry for a single executed trade.

        Args:
            symbol (str): The financial instrument being traded (e.g., 'EURUSD').
            signal (str): The trade direction ('BUY' or 'SELL').
            confidence_score (float): The final synthesized confidence score.
            scores_breakdown (dict): The individual scores from each analyzer brain.
            ticket_id (int): The order ticket ID from the MT5 broker.
        """
        try:
            trade_context = {
                'timestamp': datetime.now().isoformat(),
                'ticket': ticket_id,
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence_score,
                'scores': scores_breakdown
            }
            with open(self.journal_path, 'a') as f:
                f.write(json.dumps(trade_context) + '\n')
            logging.info(f"Trade context for ticket {ticket_id} successfully logged to journal.")
        except Exception as e:
            logging.error(f"Failed to write to trade journal: {e}")