import time
from wserver import Wserver
from datetime import datetime, timedelta
import pandas as pd  # pip install pandas
import pendulum  # pip install pendulum
import requests  # pip install requests
import yaml  # pip install pyyaml

dir_path = "../../"
roll_over_occurred_today = False


def send_msg_to_telegram(message):
    with open(dir_path + "config2.yaml", "r") as f:
        config = yaml.safe_load(f)["telegram"]
        print(config)
    url = f"https://api.telegram.org/bot{config['bot_api_token']}/sendMessage?chat_id={config['chat_id']}&text={message}"
    print(requests.get(url).json())


def load_config_to_list_of_dicts(csv_file_path):
    """
    output example:
    [
        {'action': 'SELL', 'Instrument_name': 'INFY-EQ', 'exchange': 'NSE', 'Candle_timeframe': '5m', 'Capital_allocated_in_lac': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'INFY_EEEE', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '1'},
        {'action': 'SELL', 'Instrument_name': 'SBIN-EQ', 'exchange': 'NSE', 'Candle_timeframe': '15m', 'Capital_allocated_in_lac': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'SNIN-EQQQQ', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '2'},
        {'action': 'BUY', 'Instrument_name': 'INFY-EQ', 'exchange': 'NSE', 'Candle_timeframe': '5m', 'Capital_allocated_in_lac': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'INFY_EEEE', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '3'},
        {'action': 'BUY', 'Instrument_name': 'SBIN-EQ', 'exchange': 'NSE', 'Candle_timeframe': '15m', 'Capital_allocated_in_lac': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'SNIN-EQQQQ', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '4'}
        ]
    """
    csv_data = open(csv_file_path).read()
    rows = [row.split(",") for row in csv_data.split("\n") if row]
    headers = [row[0] for row in rows]
    data_rows = [row[1:] for row in rows]
    list_of_dicts = [{} for _ in range(len(rows[0]) - 1)]
    for i in range(len(data_rows[0])):
        for j in range(len(data_rows)):
            list_of_dicts[i][headers[j]] = data_rows[j][i]
    return list_of_dicts



# def get_current_ltp(broker, instrument_name):
#     ws = Wserver(broker)
#     resp = ws.ltp(instrument_name)
#     print(instrument_name, resp)
#     ltp = resp.get(instrument_name.split(":")[-1], 0)
#     return ltp


# def exit_all_strategies(strategies):
#     return []


# def rollover_symbols(configuration_details, strategies):
#     global roll_over_occurred_today
#     current_time = pendulum.now()
#     if not roll_over_occurred_today and current_time.day == 21 and current_time.hour == 10 and current_time.minute >= 0:
#         for i in configuration_details:
#             i["Instrument_name"] = i["Rollover_symbol_name"]
#         strategies = exit_all_strategies(strategies)
#         roll_over_occurred_today = True
#     return configuration_details, strategies


def get_historical_data(sym_config, broker):
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_time_string = yesterday.strftime("%d-%m-%Y") + " 00:00:00"
    time_obj = time.strptime(yesterday_time_string, "%d-%m-%Y %H:%M:%S")
    start_time = time.mktime(time_obj)
    historical_data: list[dict] | None = broker.historical(
            sym_config["exchange"], sym_config["token"], start_time, None
        )
    if historical_data is not None:
        return pd.DataFrame(historical_data[1:11])
    return pd.DataFrame()


def place_order_with_params(sym_config, historical_data_df):
    risk_per_trade = int(sym_config["Risk per trade"])
    capital_allocated = int(sym_config["Capital_allocated_in_lac"]) * 1_00_000
    margin_required = int(sym_config["Margin required"])
    lot_size = int(sym_config["lot_size"])
    allowable_quantity_as_per_capital = capital_allocated / margin_required
    
    if sym_config["action"] == "SELL":
        high_of_last_10_candles = historical_data_df["inth"].max()
        ltp = ws.ltp.get(sym_config["exchange|token"])
        stop_loss = high_of_last_10_candles - ltp
        sym_config["stop_loss"] = stop_loss
        allowable_quantity_as_per_risk = risk_per_trade / stop_loss
        traded_quantity = min(
            allowable_quantity_as_per_risk, allowable_quantity_as_per_capital
        )
        if traded_quantity == 1:
            sell_quantity = 1
        else:
            temp = int(int(traded_quantity / lot_size) * lot_size)
            sell_quantity = int(int(temp / 2) * 2)
        # place_order("SELL") # TODO: @pannet1
    else:
        lowest_of_last_10_candles = historical_data_df["intl"].min()
        ltp = ws.ltp.get(sym_config["exchange|token"])
        stop_loss = ltp - lowest_of_last_10_candles
        sym_config["stop_loss"] = stop_loss
        allowable_quantity_as_per_risk = risk_per_trade / stop_loss
        traded_quantity = min(
            allowable_quantity_as_per_risk, allowable_quantity_as_per_capital
        )
        if traded_quantity == 1:
            buy_quantity = 1
        else:
            temp = int(int(traded_quantity / lot_size) * lot_size)
            buy_quantity = int(int(temp / 2) * 2)
        # place_order("BUY") # TODO: @pannet1
    return sym_config


def place_first_order_for_strategy(sym_config, broker, ws):
    historical_data_df = get_historical_data(sym_config, broker)
    if historical_data_df.empty():
        sym_config["strategy_started"] = False
        return sym_config
    return place_order_with_params(sym_config, historical_data_df)


def is_start_time_reached(sym_config):
    # check if the start time has reached as per configuration 
    # and return True or False
    entry_time = sym_config["strategy_entry_time"].split(":")
    current_time = pendulum.now()
    target_time = current_time.replace(hour=int(entry_time[0]), minute=int(entry_time[1]), second=0, microsecond=0)
    return False if current_time < target_time else True 


def execute_strategy(sym_config, broker, ws):
    if not sym_config.get("strategy_started", None):
        # strategy is not started, so start it 
        # by checking if the start time has reached or not
        if not is_start_time_reached(sym_config):
            # start time has not reached, so wait for the next loop
            return sym_config
        # start time has reached, so proceed
        sym_config["strategy_started"] = True
        sym_config = place_first_order_for_strategy(sym_config, broker, ws)
        if not sym_config.get("strategy_started", None):
            return sym_config
    
            
    else:
        # strategy is started, so manage it
        pass


if __name__ == "__main__":
    configuration_details = load_config_to_list_of_dicts(
        csv_file_path=dir_path + "buy_sell_config.csv"
    )
    
    from omspy_brokers.finvasia import Finvasia

    BROKER = Finvasia
    dir_path = "../../"
    with open(dir_path + "config2.yaml", "r") as f:
        config = yaml.safe_load(f)["finvasia"]
        print(config)
        broker = BROKER(**config)
        if broker.authenticate():
            print("success")

    for sym_config in configuration_details:
        sym_config["token"] = broker.instrument_symbol(
            sym_config["exchange"], sym_config["Instrument_name"]
        )
        sym_config["exchange|token"] = sym_config["exchange"] + "|" + sym_config["token"]

    instruments_for_ltp = list((sym_config["exchange|token"] for sym_config in configuration_details))
    ### init only once
    ws = Wserver(broker, instruments_for_ltp)

    # initialise_strategy(
    #     configuration_details, broker
    # )  # do the initial buy or sell and store the value in config by mutation

    while True:
        print(ws.ltp)
        time.sleep(1)
        for config in configuration_details:
            config = execute_strategy(
                config, broker, ws
            )  # check for the ltp value and re-enter or buy/sell as per req
    # Add a delay or perform other operations here

    # When done, close the WebSocket connection

