import time
from wserver import Wserver
from datetime import datetime, timedelta
import pandas as pd  # pip install pandas
import pendulum  # pip install pendulum
import requests  # pip install requests
import yaml  # pip install pyyaml

dir_path = "../../"
roll_over_occurred_today = False
local_position_book = "../../temp_position_book.csv" # TODO: change name and location

def send_msg_to_telegram(message):
    with open(dir_path + "config2.yaml", "r") as f:
        config = yaml.safe_load(f)["telegram"]
        print(config)
    url = f"https://api.telegram.org/bot{config['bot_api_token']}/sendMessage?chat_id={config['chat_id']}&text={message}"
    print(requests.get(url).json())


def load_config_to_list_of_dicts(csv_file_path, shortlisted_strategies):
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
    shortlisted_list_of_dicts = []
    for d in list_of_dicts:
        if (d["action"], d["Instrument_name"]) in shortlisted_strategies:
            shortlisted_list_of_dicts.append(d)
    return shortlisted_list_of_dicts


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


def ohlc_to_ha(df):
    ha_df = pd.DataFrame()
    ha_df["ha_close"] = (df["into"] + df["inth"] + df["intl"] + df["intc"]) / 4
    ha_df["ha_open"] = ((df["into"] + df["intc"]) / 2).shift(1)
    ha_df["ha_high"] = df[["inth", "into", "intc"]].max(axis=1)
    ha_df["ha_low"] = df[["intl", "into", "intc"]].min(axis=1)
    ha_df.loc[0, "ha_open"] = df["into"].iloc[1]
    return ha_df


def get_historical_data(sym_config, broker, interval=1, is_hieken_ashi=False):
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_time_string = yesterday.strftime("%d-%m-%Y") + " 00:00:00"
    time_obj = time.strptime(yesterday_time_string, "%d-%m-%Y %H:%M:%S")
    start_time = time.mktime(time_obj)
    historical_data: list[dict] | None = broker.historical(
        sym_config["exchange"], sym_config["token"], start_time, None, interval
    )
    if historical_data is not None:
        historical_data_df = pd.DataFrame(historical_data)
        if not is_hieken_ashi:
            return historical_data_df
        heiken_aishi_df = ohlc_to_ha(historical_data_df)
        return heiken_aishi_df

    return pd.DataFrame()


def is_order_completed(broker, order_id):
    # fields are from 
    # https://pypi.org/project/NorenRestApiPy/#md-get_orderbook
    # https://pypi.org/project/NorenRestApiPy/#md-place_order

    orders = broker.orders()
    for order in orders:
        if (
            order["norenordno"] == order_id 
            and order["status"] == "COMPLETE"
        ):
            return True
    return False

def save_to_local_position_book(content_to_save):
    with open(
        local_position_book, "a"
    ) as f:  
        f.write(content_to_save + "\n")


def place_order_with_params(sym_config, historical_data_df, broker, ws):
    historical_data_df = historical_data_df.iloc[
        1:11
    ]  # take only 10 rows excluding the first row
    risk_per_trade = int(sym_config["Risk per trade"])
    capital_allocated = int(sym_config["Capital_allocated_in_lac"]) * 1_00_000
    margin_required = int(sym_config["Margin required"])
    lot_size = int(sym_config["lot_size"])
    allowable_quantity_as_per_capital = capital_allocated / margin_required

    if sym_config["action"] == "SELL":
        high_of_last_10_candles = float(historical_data_df["inth"].max())
        ltp = float(ws.ltp.get(sym_config["exchange|token"]))
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
        sym_config["quantity"] = sell_quantity
        # add all params to sym_config, this is required to manage the placed order
        args = dict(
            side="S",
            product="M",  #  for NRML
            exchange=sym_config["exchange"],
            quantity=abs(sym_config["quantity"]),
            disclosed_quantity=abs(sym_config["quantity"]),
            order_type="MKT",
            symbol=sym_config["symbol"],
            # price=prc, # in case of LMT order
            tag="halo_hash",
        )
        resp = broker.order_place(**args)
        print(resp)
        if resp and "norenordno" in resp and is_order_completed(broker, resp["norenordno"]):
            details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S","M",'
            save_to_local_position_book(details)
            
    else:
        lowest_of_last_10_candles = float(historical_data_df["intl"].min())
        ltp = float(ws.ltp.get(sym_config["exchange|token"]))
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
        sym_config["quantity"] = buy_quantity
        args = dict(
            side="B",
            product="M",  #  for NRML
            exchange=sym_config["exchange"],
            quantity=abs(sym_config["quantity"]),
            disclosed_quantity=abs(sym_config["quantity"]),
            order_type="MKT",
            symbol=sym_config["symbol"],
            # price=prc, # in case of LMT order
            tag="halo_hash",
        )
        resp = broker.order_place(**args)
        print(resp)
        if resp and "norenordno" in resp and is_order_completed(broker, resp["norenordno"]):
            details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"B","M",'
            save_to_local_position_book(details)
    return sym_config


def place_first_order_for_strategy(sym_config, broker, ws):
    historical_data_df = get_historical_data(sym_config, broker, 1)
    if historical_data_df.empty:
        sym_config["strategy_started"] = False
        return sym_config
    return place_order_with_params(sym_config, historical_data_df, broker, ws)


def is_time_reached(time_in_config):
    # check if current time is greater than time as per configuration
    # and return True or False
    entry_time = time_in_config.split(":")
    current_time = pendulum.now()
    target_time = current_time.replace(
        hour=int(entry_time[0]), minute=int(entry_time[1]), second=0, microsecond=0
    )
    return False if current_time < target_time else True


def manage_strategy(sym_config, broker, ws):
    historical_data_df = get_historical_data(
        sym_config, broker, int(sym_config["intermediate_Candle_timeframe_in_minutes"])
    )
    latest_record = historical_data_df.iloc[[0]]
    condition_1 = latest_record["intc"] < latest_record["into"]
    condition_2 = latest_record["into"] == latest_record["inth"]
    condition_3 = latest_record["intc"] > latest_record["into"]
    condition_4 = latest_record["into"] == latest_record["intl"]
    exit_historical_data_df = get_historical_data(
        sym_config, broker, int(sym_config["exit_Candle_timeframe_in_minutes"])
    )
    exit_latest_record = exit_historical_data_df.iloc[[0]]
    if sym_config["action"] == "BUY":
        exit_condition_1 = exit_latest_record["intc"] < exit_latest_record["into"]
        exit_condition_2 = exit_latest_record["into"] == exit_latest_record["inth"]
        if is_time_reached(sym_config["strategy_exit_time"]) or (
            exit_condition_1 and exit_condition_2
        ):
            # exit all quantities
            # sym_config["quantity"] =  update quantity after placing order
            args = dict(
                side="S",  # since exiting, B will give S
                product="M",  #  for NRML
                exchange=sym_config["exchange"],
                quantity=abs(sym_config["quantity"]),
                disclosed_quantity=abs(sym_config["quantity"]),
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="halo_hash",
            )
            resp = broker.order_place(**args)
            print(resp)
            if resp and "norenordno" in resp and is_order_completed(broker, resp["norenordno"]):
                details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S","M",'
                save_to_local_position_book(details)
            
            sym_config["quantity"] = 0
            send_msg_to_telegram(
                f"Exiting all quantities for {sym_config['Instrument_name']}"
            )
        if condition_1 and condition_2:
            exit_quantity = abs(abs(sym_config["quantity"]) / 2)
            args = dict(
                side="S",  # since exiting, B will give S
                product="M",  #  for NRML
                exchange=sym_config["exchange"],
                quantity=exit_quantity,
                disclosed_quantity=exit_quantity,
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="halo_hash",
            )
            resp = broker.order_place(**args)
            print(resp)
            if resp and "norenordno" in resp and is_order_completed(broker, resp["norenordno"]):
                details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S","M",'
                save_to_local_position_book(details)
            
            sym_config["quantity"] = exit_quantity
            send_msg_to_telegram(
                f"Exiting 50% quantity for {sym_config['Instrument_name']}"
            )
        elif condition_3 and condition_4:
            # reenter / add quantity 
            # Check the account balance to determine, the quantity to be added 
            # TODO @pannet1:
            args = dict(
                side="B",  # since re-enter,
                product="M",  #  for NRML
                exchange=sym_config["exchange"],
                quantity=abs(sym_config["quantity"]),
                disclosed_quantity=abs(sym_config["quantity"]),
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="halo_hash",
            )
            resp = broker.order_place(**args)
            print(resp)
            if resp and "norenordno" in resp and is_order_completed(broker, resp["norenordno"]):
                details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"B","M",'
                save_to_local_position_book(details)
            
            send_msg_to_telegram(
                f"re-entering / add quantity for {sym_config['Instrument_name']}"
            )
    else:
        exit_condition_1 = exit_latest_record["intc"] > exit_latest_record["into"]
        exit_condition_2 = exit_latest_record["into"] == exit_latest_record["intl"]
        if is_time_reached(sym_config["strategy_exit_time"]) or (
            exit_condition_1 and exit_condition_2
        ):
            # exit all quantities
            args = dict(
                side="B",  # since exiting, S will give B
                product="M",  #  for NRML
                exchange=sym_config["exchange"],
                quantity=abs(sym_config["quantity"]),
                disclosed_quantity=abs(sym_config["quantity"]),
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="halo_hash",
            )
            resp = broker.order_place(**args)
            print(resp)
            if resp and "norenordno" in resp and is_order_completed(broker, resp["norenordno"]):
                details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"B","M",'
                save_to_local_position_book(details)
            
            sym_config["quantity"] = 0
            send_msg_to_telegram(
                f"Exiting all quantities for {sym_config['Instrument_name']}"
            )
        elif condition_3 and condition_4:
            # Exit 50% quantity
            exit_quantity = abs(abs(sym_config["quantity"]) / 2)
            args = dict(
                side="B",  # since exiting, S will give B
                product="M",  #  for NRML
                exchange=sym_config["exchange"],
                quantity=exit_quantity,
                disclosed_quantity=exit_quantity,
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="halo_hash",
            )
            resp = broker.order_place(**args)
            # check order status from the below gist
            # https://gist.github.com/pannet1/53773f6e4e67f74311024e1e25f92a10
            # read the position book once in the 1st run and keep overwritting with current
            # positions every 15 minutes or so. this way when the program terminates abruptly
            # we will have a continuity
            #
            # we keep entering all the transactions both entry and exit in this file.
            # so when we aggregate we know the current position on hand. you may need to
            # add the date also
            print(resp)
            if resp and "norenordno" in resp and is_order_completed(broker, resp["norenordno"]):
                details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"B","M",'
                save_to_local_position_book(details)
            
            sym_config["quantity"] = exit_quantity
            send_msg_to_telegram(
                f"Exiting 50% quantity for {sym_config['Instrument_name']}"
            )
        elif (condition_1 and condition_2) or (
            float(ws.ltp[sym_config["exchange|token"]]) >= sym_config["stop_loss"]
        ):  # TODO @pannet1: is this correct - ltp reaches stop loss
            # reenter / add quantity # Check the account balance to determine, the quantity to be added
            # you have the capital for this strategy which is for every trade of this strategy.
            # you know the ltp when you ltp, so based on that we can calculate the margin required
            # for a trade.
            args = dict(
                side="S",  # since re-enter,
                product="M",  #  for NRML
                exchange=sym_config["exchange"],
                quantity=abs(sym_config["quantity"]),
                disclosed_quantity=abs(sym_config["quantity"]),
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="halo_hash",
            )
            resp = broker.order_place(**args)
            print(resp)
            if resp and "norenordno" in resp and is_order_completed(broker, resp["norenordno"]):
                details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S","M",'
                save_to_local_position_book(details)
            send_msg_to_telegram(
                f"re-entering / add quantity for {sym_config['Instrument_name']}"
            )


def execute_strategy(sym_config, broker, ws):
    if not sym_config.get("strategy_started", None):
        # strategy is not started, so start it
        # by checking if the start time has reached or not
        if not is_time_reached(sym_config["strategy_entry_time"]):
            # start time has not reached, so wait for the next loop
            return sym_config
        # start time has reached, so proceed
        sym_config["strategy_started"] = True
        sym_config = place_first_order_for_strategy(sym_config, broker, ws)
        if not sym_config.get("strategy_started", None):
            return sym_config
    # strategy is started, so manage it
    manage_strategy(sym_config, broker, ws)


def read_strategies(path):
    shortlisted_strategies = []
    with open(path) as f:
        strategies = f.readlines()

    for line in strategies:
        shortlisted_strategies.append(line.split(","))
    return shortlisted_strategies


# def update_local_position_book(broker, open_positions):
#     orders_from_position_book = broker.positions()
#     new_details = set()
#     for open_position in open_positions:
#         detail = 
#         position = open_position.split(",")
#         ins_name = position[3]
#         product_type = position[6]


#         for orders in orders_from_position_book:



if __name__ == "__main__":
    strategy_path = "strategies/"
    with open(local_position_book) as f:
        open_positions = f.readlines()
    open_positions = [
        (position.split(",")[2], position.split(",")[3]) for position in open_positions
    ]
    # position is {resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S",
    # TODO: check position book at start to validate if they are still valid or canceled/closed by eod process yesterday
    # TODO: when to clear this temp position book? can we do it at SOD daily? and not do it intermittently?
    # Clear position book and update it as per position book today
    # @mahesh please see above todo.
    # record each transaction. load transaction at the beginning of run.

    shortlisted_strategies = read_strategies(
        strategy_path + "1_strategy/short_listed.csv"
    )
    configuration_details = load_config_to_list_of_dicts(
        strategy_path + "buy_sell_config.csv", shortlisted_strategies + open_positions
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
        sym_config["exchange|token"] = (
            sym_config["exchange"] + "|" + sym_config["token"]
        )

    instruments_for_ltp = list(
        (sym_config["exchange|token"] for sym_config in configuration_details)
    )
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

