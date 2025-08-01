import argparse
import json
import logging
import sys

# Add core directory to Python path to allow imports
sys.path.append('core')

from core.orchestrator import SeraphROrchestrator
from core.evaluator import SeraphEvaluator
from seraph_trainer import SeraphTrainer

def setup_logging(config):
    """Configures the central logger for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config["system_files"]["log_file"]),
            logging.StreamHandler(sys.stdout)
        ]
    )
    # Set higher logging level for verbose libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('tensorflow').setLevel(logging.ERROR)

def main():
    """Parses command-line arguments to run the specified action."""
    parser = argparse.ArgumentParser(description="Seraph-R: The Reasoning AI Trading System")
    parser.add_argument(
        'action',
        type=str,
        choices=['run', 'train', 'evaluate'],
        help="The action to perform: 'run' the live bot, 'train' all models, or 'evaluate' past performance."
    )
    args = parser.parse_args()

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("FATAL: config.json not found. Please ensure it exists in the project root.")
        return

    setup_logging(config)
    
    # Add a logger for the main script itself
    main_logger = logging.getLogger(config["system_identity"]["name"])

    if args.action == 'run':
        main_logger.info("Action 'run' selected. Initializing Orchestrator...")
        bot = SeraphROrchestrator(config)
        bot.run()
    elif args.action == 'train':
        main_logger.info("Action 'train' selected. Initializing Trainer...")
        trainer = SeraphTrainer(config)
        trainer.train_all_models()
    elif args.action == 'evaluate':
        main_logger.info("Action 'evaluate' selected. Initializing Evaluator...")
        evaluator = SeraphEvaluator(config)
        evaluator.analyze_and_adapt()

if __name__ == "__main__":
    main()