import ast
import numpy as np
from constants import FUTL, logging, CRED
from omspy_brokers.finvasia import Finvasia
import pendulum
import pandas as pd
import traceback
from time import sleep
from candle import Candle


def login_and_get_token():
    try:
        api = Finvasia(**CRED)
        if api.authenticate():
            print("Login Successfull")
            return api
    except Exception as e:
        print(e)


api = login_and_get_token()


def update_inputs(symbol):
    month_ca.inputs = resample(symbol, "1M")
    month_ca.symbol = symbol
    week_ca.inputs = resample(symbol, "1W")
    week_ca.symbol = symbol
    day_ca.inputs = resample(symbol, "1D")
    day_ca.symbol = symbol
    hour_ca.inputs = resample(symbol, "1H")
    hour_ca.symbol = symbol
    minute_ca.inputs = resample(symbol, "1Min")
    minute_ca.symbol = symbol

    month_ha.inputs = ha(symbol, "1M")
    month_ha.symbol = symbol
    week_ha.inputs = ha(symbol, "1W")
    week_ha.symbol = symbol
    day_ha.inputs = ha(symbol, "1D")
    day_ha.symbol = symbol
    hour_ha.inputs = ha(symbol, "1H")
    hour_ha.symbol = symbol
    minute_ha.inputs = ha(symbol, "1Min")
    minute_ha.symbol = symbol


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
            "time": df.index.tolist(),
            "open": np.array(df["open"].tolist()),
            "high": np.array(df["high"].tolist()),
            "low": np.array(df["low"].tolist()),
            "close": np.array(df["close"].tolist()),
        }
        return inputs


def resample(symbol, str_time):
    filepath = f"data/{symbol}.csv"
    df = pd.read_csv(filepath, index_col="time", parse_dates=True, dayfirst=True)
    ohlc = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    df = df.resample(str_time, origin="start").apply(ohlc)
    # df = df.drop(df[df.open.isnull()].index)
    df.to_csv(f"data/{symbol}_{str_time}.csv")
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
        flag = False
        filepath = f"data/{symbol}.csv"
        if FUTL.is_file_not_2day(filepath):
            logging.debug(f"{filepath} modified today")
            df_price = pd.DataFrame()
            sleep(1)
            tkn = api.instrument_symbol("NSE", symbol)
            if tkn:
                lastBusDay = pendulum.now()
                fromBusDay = lastBusDay.subtract(months=24)
                lastBusDay = lastBusDay.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                fromBusDay = fromBusDay.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                resp = api.finvasia.get_time_price_series(
                    exchange="NSE",
                    token=tkn,
                    starttime=fromBusDay.timestamp(),
                    endtime=lastBusDay.timestamp(),
                    interval=1,
                )
                if resp is not None:
                    lst_price = []
                    for ret in resp:
                        dct = {
                            "time": ret["time"],
                            "open": ret["into"],
                            "high": ret["inth"],
                            "low": ret["intl"],
                            "close": ret["intc"],
                            "volume": ret["v"],
                        }
                        lst_price.append(dct)
                    # sort DataFrame in descending order
                    df_price = pd.DataFrame(lst_price).sort_index(ascending=False)
                    if len(df_price) > 0:
                        df_price.to_csv(filepath, index=False)
                        flag = True
                else:
                    flag = False
        else:
            logging.debug(f"using {filepath} already modfied today")
            flag = True
    except Exception as e:
        print(traceback.format_exc())
        logging.debug(f"{e} while download_data")
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
                logging.error(f"Invalid names in expression: {expression.strip()}")
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

    def is_signal(self, expressions):
        try:
            signal = eval(expressions)
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
        download_data(symbol)
        update_inputs(symbol)
        if obj_strgy.buy_sell.get("buy_xpres"):
            is_buy = obj_strgy.is_signal(obj_strgy.buy_sell["buy_xpres"])
            if is_buy:
                # append buy signal, symbol to csv
                with open(obj_strgy.short_listed_file, "a") as buy_file:
                    buy_file.write(f"BUY,{symbol}\n")
        if obj_strgy.buy_sell.get("sell_xpress"):
            is_sell = obj_strgy.is_signal(obj_strgy.buy_sell["sell_xpress"])
            if is_sell:
                # append sell signal, symbol to csv
                with open(obj_strgy.short_listed_file, "a") as sell_file:
                    sell_file.write(f"SHORT,{symbol}\n")
