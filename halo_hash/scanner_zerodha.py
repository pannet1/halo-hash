from prettytable import PrettyTable
import numpy
from io import BytesIO
import requests
from datetime import datetime
from candle import Candle
from time import sleep
import traceback
import pandas as pd
import pendulum
import ast
import warnings
import os
import numpy as np
from constants import FUTL, CRED_ZERODHA, SECDIR
from omspy_brokers.bypass import Bypass
from toolkit.logger import Logger

logging = Logger(30)


current_date = datetime.now()
formatted_date = current_date.strftime("%Y-%m-%d")
exchange = "NSE"


"""
https://kite.trade/docs/connect/v3/historical/
Zerodha supported values

· minute
· day
· 3minute
· 5minute
· 10minute
· 15minute
· 30minute
· 60minute

We need 

monthly
weekly
daily
hour
15 min
"""
time_intervals = [
    "day",
    "15minute",
    "60minute",
    "M",
    "W",
]  # keep the unsupported formats at last
# follow pandas sampling keywords in case of missing time intervals
# https://kite.trade/forum/discussion/7756/python-client-is-failing-to-get-continuous-historical-data-for-instrument
allowed_time_intervals = {
    "day": pendulum.now().subtract(days=2000).to_datetime_string(),
    "15minute": pendulum.now().subtract(days=100).to_datetime_string(),
    "60minute": pendulum.now().subtract(days=400).to_datetime_string(),
    "minute": pendulum.now().subtract(days=60).to_datetime_string(),
}


def remove_token():
    tokpath = SECDIR + CRED_ZERODHA["userid"] + ".txt"
    with open(tokpath, "w") as tp:
        tp.write("")


def get_instrument_token(option_name, df):
    tokens = df[df["tradingsymbol"] ==
                option_name]["instrument_token"].to_list()
    return tokens[0] if len(tokens) >= 1 else 0


class Instruments:

    def get(self):
        url = "https://api.kite.trade/instruments"
        r = requests.get(url, allow_redirects=True)
        # open('instruments.csv', 'wb').write(r.content)
        return pd.read_csv(BytesIO(r.content))


def get_kite():
    try:
        enctoken = None
        tokpath = SECDIR + CRED_ZERODHA["userid"] + ".txt"
        if not FUTL.is_file_not_2day(tokpath):
            try:
                with open(tokpath, "r") as tf:
                    enctoken = tf.read()
                    print(f"{tokpath=} has {enctoken=}")
            except FileNotFoundError:
                enctoken = None
        else:
            enctoken = None
        bypass = Bypass(
            CRED_ZERODHA["userid"],
            CRED_ZERODHA["password"],
            CRED_ZERODHA["totp"],
            tokpath,
            enctoken,
        )
        if not bypass.authenticate():
            remove_token()
            raise ValueError("unable to authenticate")
    except Exception as e:
        logging.error(f"unable to create bypass object  {e}")
        remove_token()
    else:
        return bypass


broker = get_kite()


def update_inputs(symbol):
    minute_ca.inputs = csv_to_vector(symbol, "15minute")
    minute_ca.symbol = symbol
    hour_ca.inputs = csv_to_vector(symbol, "60minute")
    hour_ca.symbol = symbol
    day_ca.inputs = csv_to_vector(symbol, "day")
    day_ca.symbol = symbol
    week_ca.inputs = csv_to_vector(symbol, "W")
    week_ca.symbol = symbol
    month_ca.inputs = csv_to_vector(symbol, "M")
    month_ca.symbol = symbol

    minute_ha.inputs = ha(symbol, "15minute")
    minute_ha.symbol = symbol
    hour_ha.inputs = ha(symbol, "60minute")
    hour_ha.symbol = symbol
    day_ha.inputs = ha(symbol, "day")
    day_ha.symbol = symbol
    week_ha.inputs = ha(symbol, "W")
    week_ha.symbol = symbol
    month_ha.inputs = ha(symbol, "M")
    month_ha.symbol = symbol


def csv_to_vector(symbol, str_time):
    ifile = f"data/{symbol}_{str_time}.csv"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        df = pd.read_csv(ifile, index_col="time",
                         parse_dates=True, dayfirst=True)
    inputs = {
        "time": df.index.tolist(),
        "open": np.array(df["open"].tolist()),
        "high": np.array(df["high"].tolist()),
        "low": np.array(df["low"].tolist()),
        "close": np.array(df["close"].tolist()),
    }
    return inputs


def ha(symbol, str_time):
    df = pd.read_csv(f"data/{symbol}_{str_time}.csv")
    if len(df) > 1:
        df["c"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
        df["o"] = ((df["open"] + df["close"]) / 2).shift(1)
        df.iloc[0, -1] = df["o"].iloc[1]
        df["h"] = df[["high", "o", "c"]].max(axis=1)
        df["l"] = df[["low", "o", "c"]].min(axis=1)
        df["open"], df["high"], df["low"], df["close"] = (
            df["o"],
            df["h"],
            df["l"],
            df["c"],
        )
        df.drop(["o", "h", "l", "c"], axis=1, inplace=True)
        inputs = {
            "time": df["time"].tolist(),
            "open": np.array(df["open"].tolist()),
            "high": np.array(df["high"].tolist()),
            "low": np.array(df["low"].tolist()),
            "close": np.array(df["close"].tolist()),
        }
        df = pd.DataFrame(
            inputs)
        if len(df) > 0:
            df.to_csv(f"data/{symbol}_{str_time}_ha.csv", index=False)
        return inputs


def resample(symbol, ifile, str_time):
    ofile = f"data/{symbol}_{str_time}.csv"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        df = pd.read_csv(ifile, parse_dates=True, dayfirst=True)
    ohlc = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df = df.sort_index()
    df = df.resample(str_time, origin="start").apply(ohlc)
    # df = df.drop(df[df.open.isnull()].index)
    df.to_csv(ofile)
    inputs = {
        "time": df.index.tolist(),
        "open": np.array(df["open"].tolist()),
        "high": np.array(df["high"].tolist()),
        "low": np.array(df["low"].tolist()),
        "close": np.array(df["close"].tolist()),
    }
    return inputs


def download_data(symbol):
    try:
        tkn = get_instrument_token(symbol, instrument_details)
        print(f"{tkn=}")
        for time_interval in time_intervals:
            flag = False
            filepath = f"data/{symbol}_{time_interval}.csv"
            if FUTL.is_file_not_2day(filepath) or os.path.getsize(filepath) == 0:
                logging.debug(f"{filepath} modified today")
                df_price = pd.DataFrame()
                sleep(1)
                if tkn and time_interval in allowed_time_intervals:
                    to = pendulum.now().to_datetime_string()
                    resp = broker.kite.historical_data(
                        tkn, allowed_time_intervals[time_interval], to, time_interval)
                    # print(resp)
                    """
                        - `instrument_token` is the instrument identifier (retrieved from the instruments()) call.
                        - `from_date` is the From date (datetime object or string in format of yyyy-mm-dd HH:MM:SS.
                        - `to_date` is the To date (datetime object or string in format of yyyy-mm-dd HH:MM:SS).
                        - `interval` is the candle interval (minute, day, 5 minute etc.).
            
                    """
                    if resp is not None:
                        lst_price = []
                        for ret in resp:
                            dct = {
                                "time": ret["date"],
                                "open": ret["open"],
                                "high": ret["high"],
                                "low": ret["low"],
                                "close": ret["close"],
                                "volume": ret["volume"],
                            }
                            lst_price.append(dct)
                        # sort DataFrame in descending order
                        df_price = pd.DataFrame(
                            lst_price).sort_index(ascending=False)
                        if len(df_price) > 0:
                            df_price.to_csv(filepath, index=False)
                            flag = True
                    else:
                        flag = False
                elif time_interval not in allowed_time_intervals:
                    # resample based on time_interval
                    if time_interval == "M" or time_interval == "W":
                        # read day and save it resampled
                        ifile = f"data/{symbol}_day.csv"
                        _ = resample(symbol, ifile, time_interval)

            else:
                logging.debug(f"using {filepath} already modified today")
                flag = True
    except Exception as e:
        print(traceback.format_exc())
        logging.debug(f"{e} while downloading data")
        flag = False
    finally:
        return flag


class Strategy:
    def __init__(self, folder_path, strategy_name):
        self.folder_path = folder_path
        self.strategy_name = strategy_name
        self.short_listed_file = (
            f"{self.folder_path}{self.strategy_name}/short_listed.csv"
        )

    def validate_expression(self, expression):
        try:
            # Parse the expression to an talib Syntax Tree (AST)
            parsed_expression = ast.parse(expression)

            # Extract names (identifiers) from the expression
            names = [
                node.id
                for node in ast.walk(parsed_expression)
                if isinstance(node, ast.Name)
            ]

            # Check if the names correspond to valid classes or functions
            valid_names = all(name in globals() for name in names)

            if valid_names:
                return True
            else:
                logging.error(
                    f"Invalid names in expression: {expression.strip()}")
                return False
        except SyntaxError as e:
            logging.error(
                f"Syntax error in expression: {expression.strip()} - {str(e)}"
            )
            return False

    def is_valid_file(self, filepath):
        try:
            if FUTL.is_file_exists(filepath):
                with open(filepath) as file:
                    expression = file.read().replace("\n", " ")
                    # Validate each expression before evaluating:
                    if self.validate_expression(expression):
                        return expression
        except Exception as e:
            logging.error(f"{e} while checking validity of file {filepath}")

    def print_expressions(self, expressions, symbol, signal):
        conditions = [condition.strip()
                      for condition in expressions.split(' and ')]
        print_values = {"symbol": [symbol, symbol]}
        print_values.update({condition: [condition, False]
                            for condition in conditions})
        for i, condition in enumerate(conditions):
            try:
                variables = condition.split(
                    '<') if '<' in condition else condition.split('>')
                for variable in variables:
                    variable_name = variable.strip()
                    value = eval(variable)
                    print_values[condition][0] = print_values[condition][0].replace(
                        variable_name, np.array2string(value) if isinstance(value, numpy.float64) else str(value))
                print_values[condition][1] = eval(print_values[condition][0])
            except Exception as e:
                print(f"Error evaluating {condition}: {e}")
        table = PrettyTable()
        # # Horizontal table
        # table.field_names = list(print_values.keys())
        # table.add_row(list(print_values.values()))
        # Vertical table
        table.field_names = [f"{symbol=}", "condition", f"{signal=}"]
        for key, value in print_values.items():
            table.add_row([key, value[0], value[1]])
        print(table)

    def is_signal(self, expressions, symbol):
        try:
            signal = eval(expressions)
            self.print_expressions(expressions, symbol, signal)
            logging.info(f"{signal=}")
            return signal
        except Exception as e:
            print(traceback.format_exc())
            logging.error(f"error {str(e)} while generating buy signal")

    def get_symbols(self):
        try:
            self.symbols = []
            symbol_file = f"{self.folder_path}{self.strategy_name}/symbols.csv"
            if FUTL.is_file_exists(symbol_file):
                logging.debug(f"{symbol_file} exists")
                df = pd.read_csv(symbol_file)
                if df is not None and df.shape[0] > 0:
                    self.symbols = df["Symbol"].tolist()
                else:
                    logging.debug(f"{symbol_file} is empty")
            else:
                logging.debug(f"{symbol_file} does not exist")
        except Exception as e:
            print(traceback.format_exc())
            logging.error(f"{e} while getting symbols")

    def set_expressions(self):
        self.get_symbols()
        if any(self.symbols):
            # dummy test symbol
            self.buy_sell = {}
            symbol = "INFY"
            download_data(symbol)
            update_inputs(symbol)
            # buy
            self.buy_sell[
                "buy_path"
            ] = f"{self.folder_path}{self.strategy_name}/buy_conditions.txt"
            xpres = obj_strgy.is_valid_file(self.buy_sell["buy_path"])
            if xpres:
                self.buy_sell["buy_xpres"] = xpres

            # sell
            self.buy_sell[
                "sell_path"
            ] = f"{self.folder_path}{self.strategy_name}/sell_conditions.txt"
            xpres = obj_strgy.is_valid_file(self.buy_sell["sell_path"])
            if xpres:
                self.buy_sell["sell_xpress"] = xpres


instrument_details = Instruments().get()
month_ca = Candle("1M")
week_ca = Candle("1W")
day_ca = Candle("1D")
hour_ca = Candle("1H")
minute_ca = Candle("1Min")

month_ha = Candle("1M")
week_ha = Candle("1W")
day_ha = Candle("1D")
hour_ha = Candle("1H")
minute_ha = Candle("1Min")

folder_path = "strategies/"
lst_strategies = FUTL.on_subfolders(folder_path)
for strategy in lst_strategies:
    obj_strgy = Strategy(folder_path, strategy)
    obj_strgy.set_expressions()

    for symbol in obj_strgy.symbols:
        try:
            download_data(symbol)
            update_inputs(symbol)
            if obj_strgy.buy_sell.get("buy_xpres"):
                is_buy = obj_strgy.is_signal(
                    obj_strgy.buy_sell["buy_xpres"], symbol)
                if is_buy:
                    with open(f"{symbol}.log", "a") as log_file:
                        log_file.write(
                            f'{datetime.now().time()},buy,obj_strgy.buy_sell["buy_xpres"] is {obj_strgy.buy_sell["buy_xpres"]}\n')
                    # append buy signal, symbol to csv
                    with open(obj_strgy.short_listed_file, "a") as buy_file:
                        buy_file.write(
                            f"{formatted_date},{symbol},{exchange}\n")
            if obj_strgy.buy_sell.get("sell_xpress"):
                is_sell = obj_strgy.is_signal(
                    obj_strgy.buy_sell["sell_xpress"], symbol)
                if is_sell:
                    with open(f"{symbol}.log", "a") as log_file:
                        log_file.write(
                            f'{datetime.now().time()},sell,obj_strgy.buy_sell["sell_xpress"] is {obj_strgy.buy_sell["sell_xpress"]}\n')
                    # append sell signal, symbol to csv
                    with open(obj_strgy.short_listed_file, "a") as sell_file:
                        sell_file.write(
                            f"{formatted_date},{symbol},{exchange}\n")
        except Exception as e:
            logging.debug(f"{e} in getting data for {symbol}")
            sleep(1)
        continue
