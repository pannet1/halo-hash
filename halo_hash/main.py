from omspy_brokers.finvasia import Finvasia
from calculate import entry_quantity
from wserver import Wserver
from datetime import datetime, timedelta, date
import pandas as pd  # pip install pandas
from candle import Candle
import numpy as np
import pendulum  # pip install pendulum
import csv
import time

# globals are mostly imported only once and are
# in CAPS, only exception is the custom logging
from constants import CRED, STGY, SECDIR, TGRAM, logging


headers_str = "strategy,symbol,exchange,action,intermediate_Candle_timeframe_in_minutes,exit_Candle_timeframe_in_minutes,capital_in_thousand,Risk per trade,Margin required,strategy_entry_time,strategy_exit_time,lot_size,product,token,exchange|token,is_in_position_book,strategy_started,stop_loss,quantity,side"

roll_over_occurred_today = False
"""
need to place positions in a common
place for all strategies away from git
"""
local_position_book = STGY + "positions.csv"


def load_config_to_list_of_dicts(csv_file_path):
    """
    output example:
    [
        {'action': 'SELL', 'symbol': 'INFY-EQ', 'exchange': 'NSE', 'Candle_timeframe': '5m', 'capital_in_thousand': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'INFY_EEEE', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '1'},
        {'action': 'SELL', 'symbol': 'SBIN-EQ', 'exchange': 'NSE', 'Candle_timeframe': '15m', 'capital_in_thousand': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'SNIN-EQQQQ', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '2'},
        {'action': 'BUY', 'symbol': 'INFY-EQ', 'exchange': 'NSE', 'Candle_timeframe': '5m', 'capital_in_thousand': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'INFY_EEEE', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '3'},
        {'action': 'BUY', 'symbol': 'SBIN-EQ', 'exchange': 'NSE', 'Candle_timeframe': '15m', 'capital_in_thousand': '1', 'Risk per trade': '10000', 'Margin required': '5000', 'Rollover_symbol_name': 'SNIN-EQQQQ', 'rollover_date_time': '21-NOV-23-10:00:00', 'strategy_entry_time': '9:16:00', 'strategy_exit_time': '15:15:00', 'lot_size': '4'}
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
#             i["symbol"] = i["Rollover_symbol_name"]
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
    yesterday = datetime.now() - timedelta(days=30)
    yesterday_time_string = yesterday.strftime("%d-%m-%Y") + " 00:00:00"
    time_obj = time.strptime(yesterday_time_string, "%d-%m-%Y %H:%M:%S")
    start_time = time.mktime(time_obj)
    historical_data: list[dict] | None = broker.historical(
        sym_config["exchange"], sym_config["token"], start_time, None, str(
            interval)
    )
    if historical_data is not None:
        historical_data_df = pd.DataFrame(historical_data)
        num_columns = ["intc", "intv", "inth", "into", "intl", "intvwap"]
        historical_data_df[num_columns] = historical_data_df[num_columns].apply(
            pd.to_numeric, errors="coerce"
        )
        if not is_hieken_ashi:
            return historical_data_df
        heiken_aishi_df = ohlc_to_ha(historical_data_df)
        return heiken_aishi_df

    return pd.DataFrame()


def is_order_completed(broker, order_id):
    # fields are from
    # https://pypi.org/project/NorenRestApiPy/#md-get_orderbook
    # https://pypi.org/project/NorenRestApiPy/#md-place_order

    orders = broker.orders
    for order in orders:
        if order["order_id"] == order_id and order["status"] == "COMPLETE":
            return True
    return False


def save_to_local_position_book(content_to_save):
    with open(local_position_book, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers_str.split(","))
        writer.writerow(content_to_save)
        # f.write(",".join(list(content_to_save.values())) + "\n")
        # f.write(content_to_save + "\n")


def place_order_with_params(sym_config, historical_data_df, broker, ws):
    historical_data_df = historical_data_df.iloc[
        1:11
    ]  # take only 10 rows excluding the first row
    """
        moved to calc module
    risk_per_trade = int(sym_config["Risk per trade"])
    capital_allocated = int(sym_config["capital_in_thousand"]) * 1_00_0
    margin_required = int(sym_config["Margin required"])
    lot_size = int(sym_config["lot_size"])
    allowable_quantity_as_per_capital = int(capital_allocated / margin_required) # 1000 / 1
    """

    if sym_config["action"] == "S":
        high_of_last_10_candles = float(historical_data_df["inth"].max())
        ltp = float(ws.ltp.get(sym_config["exchange|token"]))
        stop_loss = high_of_last_10_candles - ltp
        sym_config["stop_loss"] = stop_loss
        """
        # moved to calc module

        allowable_quantity_as_per_risk = risk_per_trade / stop_loss
        traded_quantity = int(min(
            allowable_quantity_as_per_risk / ltp, allowable_quantity_as_per_capital
        ))
        if traded_quantity == 0:
            return sym_config
        elif traded_quantity == 1:
            sell_quantity = 1
        else:
            temp = int(int(traded_quantity / lot_size) * lot_size)
            sell_quantity = int(int(temp / 2) * 2)
        """
        sell_quantity = entry_quantity(**sym_config)
        if sell_quantity == 0:
            return sym_config

        # add all params to sym_config, this is required to manage the placed order
        args = dict(
            side="S",
            product=sym_config["product"],  # for NRML
            exchange=sym_config["exchange"],
            quantity=int(sell_quantity),
            disclosed_quantity=int(sell_quantity),
            order_type="MKT",
            symbol=sym_config["symbol"],
            # price=prc, # in case of LMT order
            tag="entry",
        )
        TGRAM.send_msg(args)
        resp = broker.order_place(**args)
        print(resp)
        logging.debug(resp)
        if resp and is_order_completed(broker, resp):
            sym_config["is_in_position_book"] = True
            sym_config["side"] = "S"
            sym_config["quantity"] = int(sell_quantity)
            sym_config["strategy_started"] = True
            save_to_local_position_book(sym_config)
            TGRAM.send_msg(resp)
    else:
        lowest_of_last_10_candles = float(historical_data_df["intl"].min())
        logging.debug(f"{lowest_of_last_10_candles=}")
        ltp = float(ws.ltp.get(sym_config["exchange|token"]))
        logging.debug(f"{ltp=}")
        stop_loss = ltp - lowest_of_last_10_candles
        sym_config["stop_loss"] = stop_loss
        # risk_per_trade = 100 / 10 ( for example) 10
        # allowable_quantity_as_per_capital =
        # capital 1000 / margin 1 / 50 ltp (200)
        """
        moved to calc
        allowable_quantity_as_per_risk = risk_per_trade / stop_loss
        traded_quantity = int(min(
            allowable_quantity_as_per_risk / ltp, allowable_quantity_as_per_capital
        ))
        if traded_quantity == 0:
            return sym_config
        elif traded_quantity == 1:
            buy_quantity = 1
        else:
            temp = int(int(traded_quantity / lot_size) * lot_size)
            buy_quantity = int(int(temp / 2) * 2)
        """
        buy_quantity = entry_quantity(**sym_config)
        if buy_quantity == 0:
            return sym_config
        args = dict(
            side="B",
            product=sym_config["product"],  # for NRML
            exchange=sym_config["exchange"],
            quantity=buy_quantity,
            disclosed_quantity=buy_quantity,
            order_type="MKT",
            symbol=sym_config["symbol"],
            # price=prc, # in case of LMT order
            tag="entry",
        )
        TGRAM.send_msg(args)
        resp = broker.order_place(**args)
        logging.debug(resp)
        if resp and is_order_completed(broker, resp):
            sym_config["is_in_position_book"] = True
            sym_config["side"] = "B"
            # details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"B","M",'
            sym_config["quantity"] = buy_quantity
            sym_config["strategy_started"] = True
            save_to_local_position_book(sym_config)
            TGRAM.send_msg(resp)
    return sym_config


def place_first_order_for_strategy(sym_config, broker, ws):
    if sym_config.get(
        "is_in_position_book", False
    ):  # if this is already in position book
        return sym_config
    print(
        f"==> Not in position book so checking for entry signal {sym_config} <==")
    historical_data_df = get_historical_data(sym_config, broker, 1)
    if historical_data_df.empty:
        return sym_config

    if is_entry_signal(sym_config, broker):
        # if 1 == 1:
        return place_order_with_params(sym_config, historical_data_df, broker, ws)
    return sym_config


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
    if "quantity" in sym_config and sym_config["quantity"] == 0:
        return
    historical_data_df = get_historical_data(
        sym_config, broker, int(
            sym_config["intermediate_Candle_timeframe_in_minutes"])
    )
    latest_record = historical_data_df.iloc[[0]]
    condition_1 = latest_record["intc"].item() < latest_record["into"].item()
    condition_2 = latest_record["into"].item() == latest_record["inth"].item()
    condition_3 = latest_record["intc"].item() > latest_record["into"].item()
    condition_4 = latest_record["into"].item() == latest_record["intl"].item()
    exit_historical_data_df = get_historical_data(
        sym_config, broker, int(sym_config["exit_Candle_timeframe_in_minutes"])
    )
    exit_latest_record = exit_historical_data_df.iloc[[0]]
    if sym_config["action"] == "B":
        exit_condition_1 = (
            exit_latest_record["intc"].item(
            ) < exit_latest_record["into"].item()
        )
        exit_condition_2 = (
            exit_latest_record["into"].item(
            ) == exit_latest_record["inth"].item()
        )
        print("ACTION IS B")
        print(f"Exit conditions for {sym_config['symbol']}==> ")
        print(
            f'{exit_latest_record["intc"].item()} < {exit_latest_record["into"].item()} and {exit_latest_record["into"].item()} == {exit_latest_record["inth"].item()} -> exit all'
        )
        print(
            f'{latest_record["intc"].item()} < {latest_record["into"].item()} and {latest_record["into"].item()} == {latest_record["inth"].item()} -> exit_50_perc'
        )
        print(
            f'{latest_record["intc"].item()} > {latest_record["into"].item()} and {latest_record["into"].item()} == {latest_record["intl"].item()} -> reenter'
        )
        print("<==")
        if (
            exit_condition_1 and exit_condition_2
        ):
            # if 1 == 1: # dummy condition to trigger exit_50_perc
            print("exit_all")
            # exit all quantities
            # sym_config["quantity"] =  update quantity after placing order
            args = dict(
                side="S",  # since exiting, B will give S
                product=sym_config["product"],  # for NRML
                exchange=sym_config["exchange"],
                quantity=sym_config["quantity"],
                disclosed_quantity=sym_config["quantity"],
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="exit_all",
            )
            TGRAM.send_msg(args)
            resp = broker.order_place(**args)
            TGRAM.send_msg(resp)
            logging.debug(resp)
            if resp and is_order_completed(broker, resp):
                # details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S","M",'
                sym_config["is_in_position_book"] = True
                sym_config["side"] = "S"
                save_to_local_position_book(sym_config)

        elif condition_1 and condition_2:
            # elif 1 == 1: # dummy condition to trigger exit_50_perc
            print("exit_50_perc")
            exit_quantity = int(int(sym_config["quantity"]) / 2)
            args = dict(
                side="S",  # since exiting, B will give S
                product=sym_config["product"],  # for NRML
                exchange=sym_config["exchange"],
                quantity=exit_quantity,
                disclosed_quantity=exit_quantity,
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="exit_50_perc",
            )
            TGRAM.send_msg(args)
            resp = broker.order_place(**args)
            TGRAM.send_msg(resp)
            logging.debug(resp)
            if resp and is_order_completed(broker, resp):
                # details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S","M",'
                sym_config["is_in_position_book"] = True
                sym_config["side"] = "S"
                sym_config["quantity"] = exit_quantity
                save_to_local_position_book(sym_config)

        elif condition_3 and condition_4:
            # reenter / add quantity
            # Check the account balance to determine, the quantity to be added
            # TODO @pannet1:
            print("Reentering")
            """
            args = dict(
                side="B",  # since re-enter,
                product=sym_config["product"],  #  for NRML
                exchange=sym_config["exchange"],
                quantity=abs(sym_config["quantity"]),
                disclosed_quantity=abs(sym_config["quantity"]),
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="reenter",
            )
            TGRAM.send_msg(args)
            resp = broker.order_place(**args)
            TGRAM.send_msg(resp)
            logging.debug(resp)
            if resp and is_order_completed(broker, resp):
                # details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"B","M",'
                sym_config["is_in_position_book"] = True
                sym_config["side"] = "B"
                save_to_local_position_book(sym_config)
            """
            pass
    else:
        exit_condition_1 = (
            exit_latest_record["intc"].item(
            ) > exit_latest_record["into"].item()
        )
        exit_condition_2 = (
            exit_latest_record["into"].item(
            ) == exit_latest_record["intl"].item()
        )
        if (
            exit_condition_1 and exit_condition_2
        ):
            buy_quantity = int(sym_config["quantity"])
            # exit all quantities
            args = dict(
                side="B",  # since exiting, S will give B
                product=sym_config["product"],  # for NRML
                exchange=sym_config["exchange"],
                quantity=buy_quantity,
                disclosed_quantity=buy_quantity,
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="exit_all",
            )
            TGRAM.send_msg(args)
            resp = broker.order_place(**args)
            TGRAM.send_msg(resp)
            logging.debug(resp)
            if resp and is_order_completed(broker, resp):
                # details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"B","M",'
                sym_config["is_in_position_book"] = True
                sym_config["side"] = "B"
                sym_config["quantity"] = buy_quantity
                save_to_local_position_book(sym_config)

            TGRAM.send_msg(
                f"Exiting all quantities for {sym_config['symbol']}")
        elif condition_3 and condition_4:
            # Exit 50% quantity
            exit_quantity = int(int(sym_config["quantity"]) / 2)
            args = dict(
                side="B",  # since exiting, S will give B
                product=sym_config["product"],  # for NRML
                exchange=sym_config["exchange"],
                quantity=exit_quantity,
                disclosed_quantity=exit_quantity,
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="exit_50_perc",
            )
            TGRAM.send_msg(args)
            resp = broker.order_place(**args)
            TGRAM.send_msg(resp)
            logging.debug(resp)
            if resp and is_order_completed(broker, resp):
                # details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"B","M",'
                sym_config["is_in_position_book"] = True
                sym_config["side"] = "B"
                sym_config["quantity"] = exit_quantity
                save_to_local_position_book(sym_config)
                # TODO: entry price = ltp

        elif (condition_1 and condition_2) or (
            float(ws.ltp[sym_config["exchange|token"]]
                  ) >= sym_config["stop_loss"]
        ):  # TODO @pannet1: is this correct - ltp reaches stop loss
            # reenter / add quantity # Check the account balance to determine, the quantity to be added
            # you have the capital for this strategy which is for every trade of this strategy.
            # you know the ltp when you ltp, so based on that we can calculate the margin required
            # for a trade.
            """
            exit_quantity = abs(sym_config["quantity"])
            args = dict(
                side="S",  # since re-enter,
                product=sym_config["product"],  #  for NRML
                exchange=sym_config["exchange"],
                quantity=exit_quantity,
                disclosed_quantity=exit_quantity,
                order_type="MKT",
                symbol=sym_config["symbol"],
                # price=prc, # in case of LMT order
                tag="reenter",
            )
            TGRAM.send_msg(args)
            resp = broker.order_place(**args)
            logging.debug(resp)
            TGRAM.send_msg(resp)
            if resp and is_order_completed(broker, resp):
                # details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S","M",'
                sym_config["is_in_position_book"] = True
                sym_config["side"] = "S"
                sym_config["quantity"] = exit_quantity
                save_to_local_position_book(sym_config)

            """
            pass


def execute_strategy(sym_config, broker, ws):
    if not sym_config.get("strategy_started", None):
        # strategy is not started, so start it
        # by checking if the start time has reached or not
        if not is_time_reached(sym_config["strategy_entry_time"]):
            # start time has not reached, so wait for the next loop
            return sym_config
        # start time has reached, so proceed
        sym_config["strategy_started"] = False
        sym_config = place_first_order_for_strategy(sym_config, broker, ws)
        if not sym_config.get("strategy_started", None):
            return sym_config
    # strategy is started, so manage it
    manage_strategy(sym_config, broker, ws)


def read_strategies(config) -> list[dict]:
    strategy_name = config["strategy"]
    csv_data = []
    path = f"{STGY}{strategy_name}/short_listed.csv"
    today_date = date.today()
    with open(path, "r") as csv_file:
        csv_reader = csv.reader(csv_file)

        # Iterate through each row in the CSV file
        for row in csv_reader:
            parsed_date = datetime.strptime(row[0], "%Y-%m-%d").date()
            if parsed_date == today_date:
                dct = dict(strategy=strategy_name,
                           symbol=row[1], exchange=row[2])
                # Append the row as a list to csv_data
                dct.update(config)
                csv_data.append(dct)
    return csv_data


def is_available_in_position_book(open_positions, config):
    # set this to True sym_config["is_in_position_book"]
    quantity = 0
    desired_position = {}
    for position in open_positions:
        if config["symbol"] == position["symbol"]:  # Add strategy name here
            dir = 1 if position["side"] == "B" else -1
            quantity += int(position["quantity"]) * dir
    for value in open_positions[::-1]:
        if config["symbol"] == value["symbol"]:  # Add strategy name here
            desired_position = value
            break
    return (quantity, desired_position)


def is_entry_signal(
    sym_config,
    broker,
) -> bool:
    """
    any of the following conditions should match
    """
    historical_data_df = get_historical_data(
        sym_config, broker, int(
            sym_config["intermediate_Candle_timeframe_in_minutes"])
    )
    inputs = {
        "time": historical_data_df.index.tolist(),
        "open": np.array(historical_data_df["into"].tolist()),
        "high": np.array(historical_data_df["inth"].tolist()),
        "low": np.array(historical_data_df["intl"].tolist()),
        "close": np.array(historical_data_df["intc"].tolist()),
        "vwap": np.array(historical_data_df["intvwap"].tolist()),
    }
    candle_data = Candle("")
    candle_data.inputs = inputs
    rsi_time_period = 14
    rsi_conditions = any(
        [candle_data.rsi(rsi_time_period, pos) < 50 for pos in range(-6, -1)]
    )
    heiken_aishi_df = ohlc_to_ha(historical_data_df)
    inputs = {
        "time": heiken_aishi_df.index.tolist(),
        "open": np.array(heiken_aishi_df["ha_open"].tolist()),
        "high": np.array(heiken_aishi_df["ha_high"].tolist()),
        "low": np.array(heiken_aishi_df["ha_low"].tolist()),
        "close": np.array(heiken_aishi_df["ha_close"].tolist()),
    }
    ha_candle_data = Candle("")
    ha_candle_data.inputs = inputs
    ema_time_period = 200
    ema_conditions = any(
        [
            ha_candle_data.low(pos) < candle_data.ema(ema_time_period, pos)
            for pos in range(-6, -1)
        ]
    )
    all_conditions = [
        rsi_conditions,
        ema_conditions,
        candle_data.close(-1) > candle_data.vwap(-1),
        candle_data.close(-1) > candle_data.sma(20, -1),
    ]
    if any(all_conditions):
        return True
    return False


def read_and_get_updated_details(broker, configuration_details):
    symbols_and_config = []
    for config in configuration_details:
        symbols_and_config += read_strategies(config)
    print(symbols_and_config)

    open_positions = []
    with open(local_position_book, "r") as csv_file:
        headers = headers_str.split(",")
        csv_reader = csv.DictReader(csv_file, fieldnames=headers)

        # Iterate through each row in the CSV file
        for row in csv_reader:
            open_positions.append(row)
    print("=====Open Positions - Start======")
    for pos in open_positions:
        print(pos)
    print("=====Open Positions - End========")
    # Check for today's shortlisted symbols
    for i, sym_config in enumerate(symbols_and_config):
        sym_config["token"] = broker.instrument_symbol(
            sym_config["exchange"], sym_config["symbol"]
        )
        logging.debug(f"token: {sym_config['token']}")
        sym_config["exchange|token"] = (
            sym_config["exchange"] + "|" + sym_config["token"]
        )
        # https://github.com/Shoonya-Dev/ShoonyaApi-py?tab=readme-ov-file#-get_quotesexchange-token
        sym_config["lot_size"] = broker.scriptinfo(
            sym_config["exchange"], sym_config["token"]).get("ls")
        quantity, position = is_available_in_position_book(
            open_positions, sym_config
        )
        if position:  # available in position book
            symbols_and_config[i].update(position)
            symbols_and_config[i]["quantity"] = quantity

    # Check for older shortlisted symbols to manage
    for pos in open_positions:
        if (pos["strategy"], pos["symbol"]) not in [(i["strategy"], i["symbol"]) for i in symbols_and_config]:
            quantity, position = is_available_in_position_book(
                open_positions, {"symbol": pos["symbol"]}
            )
            if position and quantity != 0:  # available in position book
                sym_config = {"symbol": pos["symbol"]}
                sym_config["token"] = broker.instrument_symbol(
                    pos["exchange"], pos["symbol"]
                )
                logging.debug(f"token: {sym_config['token']}")
                sym_config["exchange|token"] = (
                    pos["exchange"] + "|" + pos["token"]
                )
                sym_config.update(position)
                sym_config["quantity"] = quantity
                symbols_and_config.append(sym_config)

    print("=====Updated symbols_and_config - Start======")
    for pos in symbols_and_config:
        print(pos)
    print("=====Updated symbols_and_config - End========")
    return symbols_and_config


if __name__ == "__main__":
    # position is {resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S",
    # TODO: check position book at start to validate if they are still valid or canceled/closed by eod process yesterday
    # TODO: when to clear this temp position book? can we do it at SOD daily? and not do it intermittently?
    # Clear position book and update it as per position book today
    # @mahesh please see above todo.
    # record each transaction. load transaction at the beginning of run.

    configuration_details = load_config_to_list_of_dicts(
        STGY + "buy_sell_config.csv")
    logging.debug(f"configuration_details: {configuration_details}")

    BROKER = Finvasia
    broker = BROKER(**CRED)
    if broker.authenticate():
        print("login successful")
    symbols_and_config = read_and_get_updated_details(
        broker, configuration_details)

    instruments_for_ltp = list(
        (sym_config["exchange|token"] for sym_config in symbols_and_config)
    )
    print(instruments_for_ltp)

    ws = Wserver(broker, instruments_for_ltp)

    while True:
        ws.tokens = instruments_for_ltp
        print(ws.ltp)
        time.sleep(3)
        for config in symbols_and_config:
            execute_strategy(
                config, broker, ws
            )  # check for the ltp value and re-enter or buy/sell as per req
        symbols_and_config = read_and_get_updated_details(
            broker, configuration_details)
        instruments_for_ltp = list(
            (sym_config["exchange|token"] for sym_config in symbols_and_config)
        )
        print(instruments_for_ltp)

