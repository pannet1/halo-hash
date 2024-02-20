from omspy_brokers.finvasia import Finvasia
from prettytable import PrettyTable
from calculate import entry_quantity
from wserver import Wserver
from datetime import datetime, timedelta, date
import pandas as pd  # pip install pandas
from candle import Candle
import numpy as np
import pendulum  # pip install pendulum
import csv
import time
import numpy

# globals are mostly imported only once and are
# in CAPS, only exception is the custom logging
from constants import CRED, STGY, TGRAM, logging


headers_str = "strategy,symbol,exchange,action,intermediate_Candle_timeframe_in_minutes,exit_Candle_timeframe_in_minutes,capital_in_thousand,Risk per trade,Margin required,strategy_entry_time,strategy_exit_time,lot_size,product,token,exchange|token,is_in_position_book,strategy_started,stop_loss,quantity,side,is_exit_50_reached,last_transaction_time"

roll_over_occurred_today = False
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


# def rollover_symbols(configuration_details, strategies):
#     global roll_over_occurred_today
#     current_time = pendulum.now()
#     if not roll_over_occurred_today and current_time.day == 21 and current_time.hour == 10 and current_time.minute >= 0:
#         for i in configuration_details:
#             i["symbol"] = i["Rollover_symbol_name"]
#         strategies = exit_all_strategies(strategies)
#         roll_over_occurred_today = True
#     return configuration_details, strategies


# def ohlc_to_ha(df):
#     ha_df = pd.DataFrame()
#     ha_df["intc"] = (df["into"] + df["inth"] + df["intl"] + df["intc"]) / 4
#     ha_df["into"] = ((df["into"] + df["intc"]) / 2).shift(1)
#     ha_df["inth"] = df[["inth", "into", "intc"]].max(axis=1)
#     ha_df["intl"] = df[["intl", "into", "intc"]].min(axis=1)
#     ha_df.loc[0, "into"] = df["into"].iloc[1]
#     return ha_df

def ohlc_to_ha(df):
    df = df[::-1]
    heikin_ashi_df = pd.DataFrame(index=df.index.values, columns=[
                                  'into', 'inth', 'intl', 'intc'])
    heikin_ashi_df['intc'] = (
        df['into'] + df['inth'] + df['intl'] + df['intc']) / 4
    for i in range(len(df)):
        if i == 0:
            heikin_ashi_df.iat[0, 0] = df['into'].iloc[0]
        else:
            heikin_ashi_df.iat[i, 0] = (
                heikin_ashi_df.iat[i-1, 0] + heikin_ashi_df.iat[i-1, 3]) / 2
    heikin_ashi_df['inth'] = heikin_ashi_df.loc[:, [
        'into', 'intc']].join(df['inth']).max(axis=1)
    heikin_ashi_df['intl'] = heikin_ashi_df.loc[:, [
        'into', 'intc']].join(df['intl']).min(axis=1)
    heikin_ashi_df = heikin_ashi_df[::-1]
    return heikin_ashi_df


def get_historical_data(sym_config, broker, interval=1, is_hieken_ashi=False):
    yesterday = datetime.now() - timedelta(days=200)
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


def is_order_completed(broker, order_id: str):
    orders = broker.orders
    for order in orders:
        if any(order) and \
                order.get("order_id", "") == order_id and \
                order.get("status", "") == "COMPLETE":
            return True
    return False


def save_to_local_position_book(content_to_save):
    with open(local_position_book, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers_str.split(","))
        writer.writerow(content_to_save)


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
        last_10_candles = float(historical_data_df["inth"].max())
        ltp = float(ws.ltp.get(sym_config["exchange|token"]))
        calc = dict(
            last_10_candles=last_10_candles,
            ltp=ltp,
            side="B",
        )
        calc.update(sym_config)
        quantity, stop_loss = entry_quantity(**calc)
        sym_config["stop_loss"] = stop_loss
        if quantity == 0:
            return sym_config

        # add all params to sym_config, this is required to manage the placed order
        args = dict(
            side="S",
            product=sym_config["product"],  # for NRML
            exchange=sym_config["exchange"],
            quantity=quantity,
            disclosed_quantity=quantity,
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
            sym_config["quantity"] = int(quantity)
            sym_config["strategy_started"] = True
            sym_config["last_transaction_time"] = datetime.today().strftime('%d-%m-%Y')
            save_to_local_position_book(sym_config)
            TGRAM.send_msg(resp)
    else:
        last_10_candles = float(historical_data_df["intl"].min())
        ltp = float(ws.ltp.get(sym_config["exchange|token"]))
        calc = dict(
            last_10_candles=last_10_candles,
            ltp=ltp,
            side="B",
        )
        calc.update(sym_config)
        quantity, stop_loss = entry_quantity(**calc)
        sym_config["stop_loss"] = stop_loss
        if quantity == 0:
            return sym_config
        args = dict(
            side="B",
            product=sym_config["product"],  # for NRML
            exchange=sym_config["exchange"],
            quantity=quantity,
            disclosed_quantity=quantity,
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
            sym_config["quantity"] = quantity
            sym_config["strategy_started"] = True
            sym_config["last_transaction_time"] == datetime.today().strftime('%d-%m-%Y')
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

    table = PrettyTable()
    table.field_names = [f"Entry Signal - Key", "Value"]
    for key, value in sym_config.items():
        table.add_row([key, value])
    print(table)

    if is_entry_signal(sym_config, broker):
        # if 1 == 1:
        return place_order_with_params(sym_config, historical_data_df, broker, ws)
    return sym_config


def is_time_reached(time_in_config):
    # check if current time is greater than time as per configuration
    # and return True or False
    entry_time = time_in_config.split(":")
    current_time = pendulum.now(pendulum.timezone("Asia/Kolkata"))
    target_time = current_time.replace(
        hour=int(entry_time[0]), minute=int(entry_time[1]), second=0, microsecond=0
    )
    return False if current_time < target_time else True


def manage_strategy(sym_config, broker, ws):
    if "quantity" in sym_config and sym_config["quantity"] == 0:
        return
    if "last_transaction_time" in sym_config and sym_config["last_transaction_time"] == datetime.today().strftime('%d-%m-%Y'):
        return
    historical_data_ha_df = get_historical_data(
        sym_config, broker, int(
            sym_config["intermediate_Candle_timeframe_in_minutes"]), True
    )
    table = PrettyTable()
    table.field_names = [f"Manage Strategy - Key", "Value"]
    for key, value in sym_config.items():
        table.add_row([key, value])
    print(table)
    latest_record = (historical_data_ha_df.iloc[[0]].round()).astype(int)
    condition_1 = latest_record["intc"].item() < latest_record["into"].item()
    condition_2 = latest_record["into"].item() == latest_record["inth"].item()
    condition_3 = latest_record["intc"].item() > latest_record["into"].item()
    condition_4 = latest_record["into"].item() == latest_record["intl"].item()
    exit_historical_data_df = get_historical_data(
        sym_config, broker, int(sym_config["exit_Candle_timeframe_in_minutes"]), True)
    print(exit_historical_data_df)
    exit_latest_record = (
        exit_historical_data_df.iloc[[0]].round()).astype(int)
    if sym_config["action"] == "B":
        exit_condition_1 = (
            exit_latest_record["intc"].item(
            ) < exit_latest_record["into"].item()
        )
        exit_condition_2 = (
            exit_latest_record["into"].item(
            ) == exit_latest_record["inth"].item()
        )

        # Exit All
        table = PrettyTable()
        table.field_names = [f"Manage for {sym_config['symbol']}", "Value",
                             "Action", f"signal={exit_condition_1 and exit_condition_2}", ]
        table.add_row([f'{sym_config["exit_Candle_timeframe_in_minutes"]} min latest_ha_close < latest_ha_open',
                      f"{exit_latest_record['intc'].item()} < {exit_latest_record['into'].item()} ", "EXIT_ALL", exit_condition_1])
        table.add_row([f'{sym_config["exit_Candle_timeframe_in_minutes"]} min latest_ha_open == latest_ha_high',
                      f'{exit_latest_record["into"].item()} == {exit_latest_record["inth"].item()}  ', "EXIT_ALL", exit_condition_2])
        print(table)

        table = PrettyTable()
        table.field_names = [f"Manage for {sym_config['symbol']}",
                             "Value", "Action", f"signal={condition_1 and condition_2 and not sym_config['is_exit_50_reached']}", ]
        table.add_row([f'{sym_config["intermediate_Candle_timeframe_in_minutes"]} min latest_ha_close < latest_ha_open',
                      f'{latest_record["intc"].item()} < {latest_record["into"].item()}', "EXIT_50%", condition_1])
        table.add_row([f'{sym_config["intermediate_Candle_timeframe_in_minutes"]} min latest_ha_open == latest_ha_high',
                      f'{latest_record["into"].item()} == {latest_record["inth"].item()}', "EXIT_50%", condition_2])
        table.add_row(['Has Ext 50 reached already',
                      f'{sym_config["is_exit_50_reached"]}', "EXIT_50%", sym_config["is_exit_50_reached"]])
        print(table)

        table = PrettyTable()
        table.field_names = [f"Manage for {sym_config['symbol']}",
                             "Value", "Action", f"signal={condition_3 and condition_4}", ]
        table.add_row([f'{sym_config["intermediate_Candle_timeframe_in_minutes"]} min latest_ha_close > latest_ha_open',
                      f'{latest_record["intc"].item()} > {latest_record["into"].item()}', "REENTER", condition_3])
        table.add_row([f'{sym_config["intermediate_Candle_timeframe_in_minutes"]} min latest_ha_open == latest_ha_low',
                      f'{latest_record["into"].item()} == {latest_record["intl"].item()}', "REENTER", condition_4])
        print(table)

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
                sym_config["last_transaction_time"] = datetime.today().strftime('%d-%m-%Y')
                save_to_local_position_book(sym_config)

        elif condition_1 and condition_2 and not sym_config["is_exit_50_reached"]:
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
                sym_config["is_exit_50_reached"] = True
                sym_config["last_transaction_time"] = datetime.today().strftime('%d-%m-%Y')
                save_to_local_position_book(sym_config)

        elif condition_3 and condition_4:
            # reenter / add quantity
            # Check the account balance to determine, the quantity to be added
            # TODO @pannet1:
            print("reenter")
            args = dict(
                side="B",  # since reenter, B will give B
                product=sym_config["product"],  # for NRML
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
                # details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S","M",'
                sym_config["is_in_position_book"] = True
                sym_config["side"] = "B"
                sym_config["is_exit_50_reached"] = False
                sym_config["last_transaction_time"] = datetime.today().strftime('%d-%m-%Y')
                save_to_local_position_book(sym_config)
    else:
        exit_condition_1 = (
            exit_latest_record["intc"].item(
            ) > exit_latest_record["into"].item()
        )
        exit_condition_2 = (
            exit_latest_record["into"].item(
            ) == exit_latest_record["intl"].item()
        )

        # Exit All
        table = PrettyTable()
        table.field_names = [f"Manage for {sym_config['symbol']}", "Value",
                             "Action", f"signal={exit_condition_1 and exit_condition_2}", ]
        table.add_row([f'{sym_config["exit_Candle_timeframe_in_minutes"]} min latest_ha_close > latest_ha_open',
                      f'{exit_latest_record["intc"].item()} > {exit_latest_record["into"].item()}', "EXIT_ALL", exit_condition_1])
        table.add_row([f'{sym_config["exit_Candle_timeframe_in_minutes"]} min latest_ha_open == latest_ha_low',
                      f'{exit_latest_record["into"].item()} == {exit_latest_record["intl"].item()}', "EXIT_ALL", exit_condition_2])
        print(table)

        table = PrettyTable()
        table.field_names = [f"Manage for {sym_config['symbol']}",
                             "Value", "Action", f"signal={condition_3 and condition_4  and not sym_config['is_exit_50_reached']}", ]
        table.add_row([f'{sym_config["intermediate_Candle_timeframe_in_minutes"]} min latest_ha_close > latest_ha_open',
                      f'{latest_record["intc"].item()} > {latest_record["into"].item()}', "EXIT_50%", condition_3])
        table.add_row([f'{sym_config["intermediate_Candle_timeframe_in_minutes"]} min latest_ha_open == latest_ha_low',
                      f'{latest_record["into"].item()} == {latest_record["intl"].item()}', "EXIT_50%", condition_4])
        table.add_row(['Has Ext 50 reached already',
                      f'{sym_config["is_exit_50_reached"]}', "EXIT_50%", sym_config["is_exit_50_reached"]])
        print(table)

        table = PrettyTable()
        table.field_names = [f"Manage for {sym_config['symbol']}",
                             "Value", "Action", f"signal={condition_1 and condition_2}", ]
        table.add_row([f'{sym_config["intermediate_Candle_timeframe_in_minutes"]} min latest_ha_close < latest_ha_open',
                      f'{latest_record["intc"].item()} < {latest_record["into"].item()}', "EXIT_50%", condition_1])
        table.add_row([f'{sym_config["intermediate_Candle_timeframe_in_minutes"]} min latest_ha_open == latest_ha_high',
                      f'{latest_record["into"].item()} == {latest_record["inth"].item()}', "EXIT_50%", condition_2])
        print(table)

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
                sym_config["last_transaction_time"] = datetime.today().strftime('%d-%m-%Y')
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
                sym_config["is_exit_50_reached"] = True
                sym_config["last_transaction_time"] = datetime.today().strftime('%d-%m-%Y')
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
            print("reenter")
            args = dict(
                side="S",  # since reenter, S will give S
                product=sym_config["product"],  # for NRML
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
                # details = f'{resp["request_time"]},{resp["norenordno"]},{sym_config["action"]},{sym_config["instrument_name"]},{sym_config["quantity"]},"S","M",'
                sym_config["is_in_position_book"] = True
                sym_config["side"] = "S"
                sym_config["is_exit_50_reached"] = False
                sym_config["last_transaction_time"] = datetime.today().strftime('%d-%m-%Y')
                save_to_local_position_book(sym_config)


def execute_strategy(sym_config, broker, ws):
    logging.info(
        f"strategy_started is {sym_config.get('strategy_started')} and time reached is {is_time_reached(sym_config['strategy_entry_time'])}")
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
    is_exit_50_reached = False
    for position in open_positions:
        if config["symbol"] == position["symbol"]:  # Add strategy name here
            dir = 1 if position["side"] == "B" else -1
            quantity += int(position["quantity"]) * dir
    for value in open_positions[::-1]:
        if config["symbol"] == value["symbol"]:  # Add strategy name here
            desired_position = value
            break
    for value in open_positions:
        if config["symbol"] == value["symbol"]:  # Add strategy name here
            if value.get("is_exit_50_reached", False):
                is_exit_50_reached = True
    return (quantity, desired_position, is_exit_50_reached)


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
    rsi_conditions = [
        (candle_data.rsi(rsi_time_period, pos) < 50,
         f"candle_data.rsi({rsi_time_period}, {pos}) < 50")
        for pos in range(-6, -1)
    ]
    heiken_aishi_df = ohlc_to_ha(historical_data_df)
    inputs = {
        "time": heiken_aishi_df.index.tolist(),
        "open": np.array(heiken_aishi_df["into"].tolist()),
        "high": np.array(heiken_aishi_df["inth"].tolist()),
        "low": np.array(heiken_aishi_df["intl"].tolist()),
        "close": np.array(heiken_aishi_df["intc"].tolist()),
    }
    ha_candle_data = Candle("")
    ha_candle_data.inputs = inputs
    ema_time_period = 200
    ema_conditions = [
        (ha_candle_data.low(pos) < candle_data.ema(ema_time_period, pos),
         f"ha_candle_data.low({pos}) < candle_data.ema({ema_time_period}, {pos})")
        for pos in range(-6, -1)
    ]
    candle_data_conditions = [
        (candle_data.close(-1) > candle_data.vwap(-1),
         "candle_data.close(-1) > candle_data.vwap(-1)"),
        (candle_data.close(-1) > candle_data.sma(20, -1),
         "candle_data.close(-1) > candle_data.sma(20, -1)"),
    ]
    signal = any([c[0] for c in rsi_conditions +
                 ema_conditions+candle_data_conditions])
    table = PrettyTable()
    table.field_names = [
        f"Entry Signal for {sym_config['symbol']}", "Value", f"signal={signal}"]
    table_details = {}
    for (condition_signal, condition) in rsi_conditions+ema_conditions+candle_data_conditions:
        variables = condition.split(
            '<') if '<' in condition else condition.split('>')
        condition_as_str = condition
        for variable in variables:
            variable_name = variable.strip()
            value = eval(variable)
            condition_as_str = condition_as_str.replace(
                variable_name, np.array2string(value) if isinstance(value, numpy.float64) else str(value))
        table_details[condition] = [condition_as_str, condition_signal]
        table.add_row([condition, condition_as_str, condition_signal])
    print(table)

    if signal:
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
        quantity, position, is_exit_50_reached = is_available_in_position_book(
            open_positions, sym_config
        )
        if position:  # available in position book
            symbols_and_config[i].update(position)
            symbols_and_config[i]["quantity"] = quantity
            symbols_and_config[i]["is_exit_50_reached"] = is_exit_50_reached
            symbols_and_config[i]["last_transaction_time"] = position.get("last_transaction_time")

    # Check for older shortlisted symbols to manage
    for pos in open_positions:
        if (pos["strategy"], pos["symbol"]) not in [(i["strategy"], i["symbol"]) for i in symbols_and_config]:
            quantity, position, is_exit_50_reached = is_available_in_position_book(
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
                symbols_and_config[i]["is_exit_50_reached"] = is_exit_50_reached
                symbols_and_config[i]["last_transaction_time"] = position.get("last_transaction_time")
                symbols_and_config.append(sym_config)

    symbols_and_config = [config for config in symbols_and_config if config["last_transaction_time"] != datetime.today().strftime('%d-%m-%Y')]

    print("=====Updated symbols_and_config - Start======")
    for pos in symbols_and_config:
        print(pos)
    print("=====Updated symbols_and_config - End========")
    return symbols_and_config


def free_margin(broker):
    margins = broker.margins
    if isinstance(margins, dict):
        print(margins)
        return int(float(margins.get("cash", 0)))
    return 0.05


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
        MARGIN = free_margin(broker)
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
