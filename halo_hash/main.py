import time
from wserver import Wserver
from datetime import datetime, timedelta
import pandas as pd # pip install pandas
import pendulum # pip install pendulum
import requests # pip install requests
import yaml # pip install pyyaml
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


def get_all_instrument_names(list_of_dicts: list[dict]) -> list:
    instrument_names = set(
        element["exchange"] + ":" + element["Instrument_name"]
        for element in list_of_dicts
    )
    return list(instrument_names)


# def get_current_ltp(broker, instrument_name):
#     ws = Wserver(broker)
#     resp = ws.ltp(instrument_name)
#     print(instrument_name, resp)
#     ltp = resp.get(instrument_name.split(":")[-1], 0)
#     return ltp


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


def initialise_strategy(configuration_details, broker):
    """perform the initial buy or sell based on the configuration details in 
    buy_sell_config.csv

    Args:
        configuration_details (list[dict]): _description_
        broker (_type_): _description_
    """
    instrument_names = get_all_instrument_names(configuration_details)
    print(instrument_names)

    yesterday = datetime.now() - timedelta(days=1)
    yesterday_time_string = yesterday.strftime("%d-%m-%Y") + " 00:00:00"
    time_obj = time.strptime(yesterday_time_string, "%d-%m-%Y %H:%M:%S")
    start_time = time.mktime(time_obj)

    # ltp_dict = ws.ltp(instrument_names)
    for sym_config in configuration_details:
        entry_time = sym_config["strategy_entry_time"].split(":")
        current_time = pendulum.now()
        if current_time.hour >= int(entry_time[0]) and current_time.minute >= int(entry_time[1]):
            print(f"Time has not reached for the symbol - {sym_config}")
            continue
        token = broker.instrument_symbol(
            sym_config["exchange"], sym_config["Instrument_name"]
        )
        historical_data: list[dict] | None = broker.historical(
            sym_config["exchange"], token, start_time, None
        )
        if historical_data is not None:
            df = pd.DataFrame(historical_data[1:11])
            print(df)
            #   stat                 time       ssboe     into     inth     intl     intc  intvwap   intv intoi        v oi
            #     0   Ok  27-10-2023 15:28:00  1698400680  1379.10  1381.15  1379.00  1381.00  1379.96  15852     0  4626587  0
            #     1   Ok  27-10-2023 15:27:00  1698400620  1381.75  1381.90  1379.00  1379.30  1379.96  36371     0  4610735  0
            #     2   Ok  27-10-2023 15:26:00  1698400560  1381.65  1382.00  1381.65  1381.90  1381.31  33586     0  4574364  0
            #     3   Ok  27-10-2023 15:25:00  1698400500  1381.65  1381.70  1381.55  1381.70  1381.36  31865     0  4540778  0
            #     4   Ok  27-10-2023 15:24:00  1698400440  1381.70  1381.85  1381.65  1381.70  1381.74  24837     0  4508913  0
            #     5   Ok  27-10-2023 15:23:00  1698400380  1381.60  1381.90  1381.60  1381.80  1382.74  31611     0  4484076  0
            #     6   Ok  27-10-2023 15:22:00  1698400320  1380.75  1381.85  1380.75  1381.65  1381.38  29984     0  4452465  0
            #     7   Ok  27-10-2023 15:21:00  1698400260  1380.70  1380.95  1380.25  1380.95  1379.90  28085     0  4422481  0
            #     8   Ok  27-10-2023 15:20:00  1698400200  1381.00  1381.70  1380.25  1380.90  1381.08  72837     0  4394396  0
            #     9   Ok  27-10-2023 15:19:00  1698400140  1380.35  1381.05  1380.30  1381.05  1381.44  27441     0  4321559  0
            
            risk_per_trade = int(sym_config["Risk per trade"])
            capital_allocated = int(sym_config["Capital_allocated_in_lac"]) * 1_00_000
            margin_required = int(sym_config["Margin required"])
            
            allowable_quantity_as_per_capital = capital_allocated / margin_required
            if sym_config["action"] == "SELL":
                high_of_last_10_candles = df['inth'].max()
                resp = broker.scriptinfo(sym_config["exchange"], token)
                ltp = int(resp["lp"])
                stop_loss = high_of_last_10_candles - ltp
                allowable_quantity_as_per_risk = risk_per_trade / stop_loss
                traded_quantity = min(allowable_quantity_as_per_risk, allowable_quantity_as_per_capital)
                if traded_quantity == 1:
                    sell_quantity = 1
                else:
                    temp = int(int(traded_quantity/45) * 45) 
                    sell_quantity = int(int(temp/2) *2)
                # place_order("SELL")
            else:
                lowest_of_last_10_candles = df['inth'].max()
                resp = broker.scriptinfo(sym_config["exchange"], token)
                ltp = int(resp["lp"])
                stop_loss = ltp - lowest_of_last_10_candles
                allowable_quantity_as_per_risk = risk_per_trade / stop_loss
                traded_quantity = min(allowable_quantity_as_per_risk, allowable_quantity_as_per_capital)
                if traded_quantity == 1:
                    buy_quantity = 1
                else:
                    temp = int(int(traded_quantity/45) * 45) 
                    buy_quantity = int(int(temp/2) *2)
                # place_order("BUY")


    # get_ltp()


if __name__ == "__main__":
    configuration_details = load_config_to_list_of_dicts(
        csv_file_path=dir_path + "buy_sell_config.csv"
    )
    print(configuration_details)
    instrument_names = get_all_instrument_names(configuration_details)
    print(instrument_names)

    from omspy_brokers.finvasia import Finvasia
    

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
        configuration_details, broker
    )  # do the initial buy or sell and store the value in config by mutation

    # while True:
    #     for config in configuration_details:
    #         execute_strategy(
    #             config, broker
    #         )  # check for the ltp value and re-enter or buy/sell as per req
    # print(resp)
    # ws.close()
    # Add a delay or perform other operations here

    # When done, close the WebSocket connection

