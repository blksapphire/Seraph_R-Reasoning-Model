import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import MetaTrader5 as mt5
import json
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go

# Load config to get dashboard settings without needing full app context
try:
    with open("config.json", 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    print("Dashboard could not start: config.json not found.")
    exit()
    
AI_NAME = config["system_identity"]["name"]

app = dash.Dash(__name__)
app.title = f"{AI_NAME} Command Center"

# --- Main Application Layout ---
app.layout = html.Div(style={'backgroundColor': '#111111', 'color': '#E0E0E0', 'fontFamily': 'Monospace', 'padding': '15px'}, children=[
    dcc.Interval(id='interval-component', interval=3000, n_intervals=0), # 3-second refresh
    
    # Header Section
    html.Div([
        html.H1(f"// {AI_NAME} // COMMAND CENTER", style={'textAlign': 'center', 'color': '#00BCD4', 'letterSpacing': '3px'}),
        html.Div(id='live-status', style={'textAlign': 'center', 'fontSize': '16px', 'marginBottom': '5px'}),
        html.Div(id='evaluation-status', style={'textAlign': 'center', 'fontSize': '12px', 'color': '#888'})
    ], style={'marginBottom': '20px'}),
    
    # Main Content Area (Two Columns)
    html.Div(style={'display': 'flex', 'flexDirection': 'row'}, children=[
        
        # Left Panel (Main Analysis)
        html.Div(style={'width': '60%', 'paddingRight': '15px'}, children=[
            html.H2("LIVE REASONING ENGINE", style={'borderBottom': '1px solid #00BCD4'}),
            html.Div(html.Pre(id='reasoning-panel', style={'whiteSpace': 'pre-wrap', 'wordBreak': 'break-all', 'backgroundColor': '#1E1E1E', 'border': '1px solid #333', 'padding': '15px', 'fontSize': '14px', 'minHeight': '300px'})),
            html.H2("OPEN POSITIONS", style={'borderBottom': '1px solid #00BCD4', 'marginTop': '20px'}),
            html.Div(id='positions-table', style={'maxHeight': '300px', 'overflowY': 'auto'})
        ]),
        
        # Right Panel (Intel & Vitals)
        html.Div(style={'width': '40%', 'paddingLeft': '15px'}, children=[
            html.H2("CONFIDENCE GAUGE", style={'borderBottom': '1px solid #00BCD4'}),
            dcc.Graph(id='confidence-gauge', config={'displayModeBar': False}),
            html.H2("INTEL BREAKDOWN", style={'borderBottom': '1px solid #00BCD4'}),
            html.Div(id='confidence-breakdown'),
            html.H2("DYNAMIC WEIGHTS", style={'borderBottom': '1px solid #00BCD4'}),
            html.Div(id='strategy-weights'),
            html.H2("ACCOUNT VITALS", style={'borderBottom': '1px solid #00BCD4'}),
            html.Div(id='account-info'),
        ]),
    ]),
])

@app.callback(
    [Output('live-status', 'children'),
     Output('evaluation-status', 'children'),
     Output('confidence-gauge', 'figure'),
     Output('confidence-breakdown', 'children'),
     Output('strategy-weights', 'children'),
     Output('reasoning-panel', 'children'),
     Output('account-info', 'children'),
     Output('positions-table', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    # Default values
    status_text = "OFFLINE"
    eval_text = "Self-Evaluation: Standing By"
    conf_breakdown, strat_weights, reasoning_text = "...", "...", "Awaiting analysis cycle..."
    acc_text, pos_table = "MT5 Disconnected", "MT5 Disconnected"
    
    # Create default gauge figure
    gauge_fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = 0,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Confidence", 'font': {'color': '#E0E0E0'}},
        gauge = {'axis': {'range': [-1, 1], 'tickwidth': 1, 'tickcolor': "#E0E0E0"},
                 'bar': {'color': "#888"},
                 'steps' : [{'range': [-1, -0.5], 'color': '#F44336'}, {'range': [0.5, 1], 'color': '#4CAF50'}],
                 'threshold' : {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': 0}},
        number={'font': {'color': '#E0E0E0'}}
    ))
    gauge_fig.update_layout(paper_bgcolor='#111111', font={'color': '#E0E0E0'})
    
    # Read status file first - it works even if MT5 is down
    try:
        with open(config["system_files"]["status_file"], 'r') as f:
            status_data = json.load(f)
        status_text = f"STATUS: {status_data.get('status', 'IDLE')}"
        reasoning_text = status_data.get('reasoning', "Awaiting analysis cycle...")
        scores = status_data.get('scores', {})
        
        # Reload current weights for display
        current_weights = config['strategy_weights']
        with open('config.json', 'r') as f_cfg:
            current_weights = json.load(f_cfg)['strategy_weights']

        final_confidence = sum(scores.get(key, 0) * current_weights.get(f"{key}_analysis", 0) for key in scores)
        
        gauge_fig.update_traces(value=final_confidence, selector=dict(type='indicator'))
        gauge_fig.update_traces(gauge_threshold_value=final_confidence, selector=dict(type='indicator'))
        
        conf_breakdown = html.Ul([html.Li(f"{key.capitalize()}: {value:.3f}") for key, value in scores.items()])
        strat_weights = html.Ul([html.Li(f"{key.replace('_analysis', '').capitalize()}: {value:.3f}") for key, value in current_weights.items()])

    except (FileNotFoundError, json.JSONDecodeError): pass
        
    try:
        with open("last_evaluation.log", "r") as f:
            eval_text = f"Last Self-Evaluation: {datetime.fromisoformat(f.read()).strftime('%Y-%m-%d %H:%M:%S')}"
    except FileNotFoundError: pass
        
    # Now, connect to MT5 for live data
    if mt5.initialize(login=config['mt5_credentials']['login'], password=config['mt5_credentials']['password'], server=config['mt5_credentials']['server']):
        acc_info = mt5.account_info()
        if acc_info:
            acc_info_dict = acc_info._asdict()
            acc_text = html.Ul([
                html.Li(f"Balance: {acc_info_dict['balance']:.2f} {acc_info_dict['currency']}"),
                html.Li(f"Equity: {acc_info_dict['equity']:.2f} {acc_info_dict['currency']}"),
                html.Li(f"Profit: {acc_info_dict['profit']:.2f} {acc_info_dict['currency']}"),
            ])
        
        positions = mt5.positions_get()
        if positions:
            pos_df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())[['symbol', 'type', 'volume', 'price_open', 'profit']]
            pos_df['type'] = pos_df['type'].apply(lambda x: 'BUY' if x == 0 else 'SELL')
            pos_table = html.Table([
                html.Thead(html.Tr([html.Th(col) for col in pos_df.columns])),
                html.Tbody([html.Tr([html.Td(pos_df.iloc[i][col], style={'color': '#4CAF50' if pos_df.iloc[i]['profit'] > 0 else '#F44336' if pos_df.iloc[i]['profit'] < 0 else '#E0E0E0'}) for col in pos_df.columns]) for i in range(len(pos_df))])
            ], style={'width': '100%', 'textAlign': 'left'})
        else:
            pos_table = "No open positions."
        mt5.shutdown()
    
    return status_text, eval_text, gauge_fig, conf_breakdown, strat_weights, reasoning_text, acc_text, pos_table

if __name__ == '__main__':
    app.run_server(debug=False, host=config['dashboard']['host'], port=config['dashboard']['port'])