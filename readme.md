Seraph-R: The Reasoning AI Trading System (v2.0)
Seraph-R is a multi-pair, self-optimizing algorithmic trading framework built on a principle of Total Transparency. It is designed not as a black box, but as an analytical partner that verbalizes its complete thought process for every trade decision, presenting it in a modern, interactive command center dashboard.
[CRITICAL RISK WARNING & DISCLAIMER]
This software is provided for educational and research purposes only. It is NOT financial advice. Trading in financial markets carries an extreme level of risk and can result in the total loss of your capital. Its self-adaptive nature can lead to unpredictable behavior. You are the sole operator and are fully responsible for all outcomes. DO NOT DEPLOY ON A LIVE ACCOUNT. The author and all affiliates assume no responsibility for your trading results.
Philosophy & Core Features
The Reasoning Engine: Seraph-R synthesizes a human-readable narrative from its analytical modules, explaining why it is considering a trade. This reasoning is the centerpiece of the live dashboard.
Multi-Pair Mastery: Configure and trade an entire portfolio of assets (EURUSD, GBPJPY, XAUUSD, etc.). Seraph-R trains and deploys a unique, specialized model for each asset.
Dynamic ATR Risk Management: Stop Loss and Take Profit levels are dynamically calculated based on the current volatility (Average True Range) of each asset, leading to more intelligent and adaptive risk control.
Closed-Loop Self-Optimization: The Evaluator module analyzes real-world performance on your demo account and automatically adjusts the system's strategic weights to favor what's working and discard what isn't.
System Architecture
Seraph-R uses a modular, multi-brain architecture designed for clarity and power.
Generated code
+---------------------------------+
|        You (The Operator)       |
+---------------------------------+
                 |
                 v
+---------------------------------+
|        main.py (CLI)            |
|  (run, train, evaluate)         |
+---------------------------------+
                 |
                 v
+---------------------------------+
|   core/orchestrator.py          |
|   (The Master Conductor)        |
+---------------------------------+
                 |
+----------------+----------------+------------------+
|                |                |                  |
v                v                v                  v
+-----------+    +-----------+    +-----------+      +----------------+
| modules/  |    | modules/  |    | modules/  |      | core/          |
| TA        |    | SMC       |    | FA        |      | trade_logger.py|
| Brain     |    | Brain     |    | Brain     |      | (Writes Journal) |
+-----------+    +-----------+    +-----------+      +----------------+
      |                |                |                  |
      +----------------+----------------+------------------+
                               |
                               v
                     +----------------+
                     |  MT5 Terminal  |
                     +----------------+
                               |
                               ^
                     +----------------+
                     | core/          |
                     | evaluator.py   |
                     | (Analyzes P&L, |
                     | Adapts Weights)|
                     +----------------+
Use code with caution.
Setup and Installation (for Linux Mint)
This guide provides a step-by-step process for setting up the Seraph-R environment on a clean Linux Mint system.
1. System Prerequisites:
Open a terminal and install Wine for running MetaTrader 5:

"sudo apt update && sudo apt install wine64"

Install Python's package manager and virtual environment tools:

"sudo apt install python3-pip python3-venv"

2. Install MetaTrader 5:
Download the MT5 installer (mt5setup.exe) from your broker or the official MetaQuotes website.
Run the installer using Wine:

"wine mt5setup.exe"

Follow the on-screen installation prompts to complete the setup.
3. Clone the Seraph-R Repository:
Clone the project from your Git repository. Replace the URL below with your actual repository URL.

git clone https://github.com/YourUsername/seraph-r.git
cd seraph_r

4. Create a Virtual Environment & Install Dependencies:
Create a dedicated Python environment to keep dependencies isolated and clean. This is a critical best practice.

"python3 -m venv venv"
"source venv/bin/activate"
You should see (venv) at the beginning of your terminal prompt. Now, install all required libraries:
"pip install -r requirements.txt"
Note: This will download several large machine learning models and may take some time.

5. Configure Seraph-R:
Open the config.json file with a text editor.
In the mt5_credentials section, fill in your demo account login, password, and server.
In the fundamental_parameters section, get a free API key from newsapi.org and replace "YOUR_NEWSAPI_KEY" with your actual key. If you leave it, the Fundamental Analyzer will be safely disabled.
Review all other settings, especially symbols_to_trade, to match your preferences.

Operational Workflow

Step 1: Train the AI Brains
The very first step is to train the specialized models for all the symbols you configured. This command iterates through each symbol and builds its unique neural network model.
Important: You must be inside the activated virtual environment (source venv/bin/activate). This can take a significant amount of time depending on your hardware and the number of symbols.

python main.py train
```This will create a `models/` directory containing the trained model files.

### Step 2: Run the Live (Demo) Trading Bot
Once training is complete, ensure your MetaTrader 5 terminal is running and you are logged into your demo account. Then, from your terminal, deploy Seraph-R:

python main.py run
The system is now live. It will begin its operational loop: analyzing your configured pairs, logging its reasoning, executing trades based on its confidence, and periodically triggering the self-evaluation module.

### Step 3: Monitor Mission Control
With the bot running, open a **second terminal**. Navigate to the project directory and activate the virtual environment again (`source venv/bin/activate`). Then, launch the command center dashboard.

python seraph_dashboard.py
Navigate to http://127.0.0.1:8050 in your web browser.

### Step 4 (Optional): Manual Adaptation
Seraph-R evaluates its performance automatically after a set number of trades (as defined in config.json). However, you can trigger this process manually to force an immediate adaptation based on the latest trades in its journal.
"python main.py evaluate"
This is useful after a period of high volatility or if you want to see the adaptation logic in action immediately.

Command Line Reference
All operations are controlled via main.py.
Command	Action
"python main.py train"	Initiates the training process for all symbols listed in config.json. Creates model files.
"python main.py run"	Starts the live trading orchestrator. Requires MT5 to be running.
"python main.py evaluate"	Forces the system to analyze its trade journal and adapt its strategy weights immediately.