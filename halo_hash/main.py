import time
from wserver import Wserver
from datetime import datetime, timedelta
import pandas as pd


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


def get_all_instrument_names(list_of_dicts: list[dict]) -> list:
    instrument_names = set(
        element["exchange"] + ":" + element["Instrument_name"]
        for element in list_of_dicts
    )
    return list(instrument_names)


def get_current_ltp(broker, instrument_name):
    ws = Wserver(broker)
    resp = ws.ltp(instrument_name)
    print(instrument_name, resp)
    ltp = resp.get(instrument_name.split(":")[-1], 0)
    return ltp


def execute_buy_strategy(config, broker):
    instrument_name = config["exchange"] + ":" + config["Instrument_name"]
    current_ltp = get_current_ltp(broker, instrument_name)
    risk_per_trade = config["Risk per trade"]
    candle_timeframe = config["Candle_timeframe"]
    capital_allocated = config["Capital_allocated_in_lac"]
    margin_required = config["Margin required"]
    strategy_start_time = config["strategy_entry_time"]
    strategy_end_time = config["strategy_exit_time"]
    rollover_symbol_name = config["Rollover_symbol_name"]
    rollover_date_time = config["rollover_date_time"]
    lot_size = config["lot_size"]
    high_of_last_ten_candles = (
        ""
    )  # get this from scanner. download_data using timeframe

    pass


def execute_sell_strategy(config, broker):
    pass


def execute_strategy(config, broker):
    if config["action"] == "BUY":
        execute_buy_strategy(config, broker)
    if config["action"] == "SELL":
        execute_sell_strategy(config, broker)
    pass


def initialise_strategy(configuration_details, broker, ws):
    instrument_names = get_all_instrument_names(configuration_details)
    print(instrument_names)

    yesterday = datetime.now() - timedelta(days=1)
    yesterday_time_string = yesterday.strftime("%d-%m-%Y") + " 00:00:00"
    time_obj = time.strptime(yesterday_time_string, "%d-%m-%Y %H:%M:%S")
    start_time = time.mktime(time_obj)

    ltp_dict = ws.ltp(instrument_names)
    for sym_config in configuration_details:
        token = broker.instrument_symbol(
            sym_config["exchange"], sym_config["Instrument_name"]
        )
        historical_data: list[dict] | None = broker.historical(
            sym_config["exchange"], token, start_time, None
        )
        if historical_data is not None:
            df = pd.DataFrame(historical_data[1:11])

    # get_ltp()


if __name__ == "__main__":
    dir_path = "../../"
    configuration_details = load_config_to_list_of_dicts(
        csv_file_path=dir_path + "buy_sell_config.csv"
    )
    print(configuration_details)
    instrument_names = get_all_instrument_names(configuration_details)
    print(instrument_names)

    from omspy_brokers.finvasia import Finvasia
    import yaml

    BROKER = Finvasia
    dir_path = "../../"
    with open(dir_path + "config2.yaml", "r") as f:
        config = yaml.safe_load(f)["finvasia"]
        print(config)
        broker = BROKER(**config)
        if broker.authenticate():
            print("success")

    ### init only once
    ws = Wserver(broker)

    initialise_strategy(
        configuration_details, broker, ws
    )  # do the initial buy or sell and store the value in config by mutation

    while True:
        for config in configuration_details:
            execute_strategy(
                config, broker
            )  # check for the ltp value and re-enter or buy/sell as per req
    # print(resp)
    # ws.close()
    # Add a delay or perform other operations here

    # When done, close the WebSocket connection

