import ast
from talib import abstract
import numpy as np
from constants import futils, logging, SECDIR, CRED
from omspy_brokers.finvasia import Finvasia
import pendulum
import pandas as pd


def login_and_get_token():
    try:
        api = Finvasia(**CRED)
        if api.authenticate():
            print("Login Successfull")
            return api
    except Exception as e:
        print(e)


class Candle():

    def __init__(self):
        self.inputs = []  # Use the shared data

    def close(self, period=-2):
        close = self.inputs['close'][period]
        logging.info(f"{close=} : {period=}")
        return close

    def high(self, period=-2):
        high = self.inputs['high'][period]
        logging.info(f"{high=} : {period}")
        return high

    def low(self, period=-2):
        low = self.inputs['low'][period]
        logging.info(f"{low=} : {period=}")
        return low

    def volume(self, period=-2):
        volume = self.inputs['volume'][period]
        logging.info(f"{volume=} : {period=}")
        return volume

    def macd(self, fastperiod, slowperiod, signalperiod):
        try:
            _, macdsignal, _ = abstract.MACD(self.inputs,
                                             fastperiod=fastperiod,
                                             slowperiod=slowperiod,
                                             signalperiod=signalperiod)
            logging.debug(f"macd: {macdsignal[-1]}")
            return macdsignal[-1]
        except Exception as e:
            logging.warning(f"error {e} in macd")

    def ema(self, timeperiod):
        try:
            result = abstract.EMA(
                self.inputs,
                timeperiod=timeperiod)
            logging.debug(f"ema: {result[-1]}")
            return result[-1]
        except Exception as e:
            logging.error(e)


def resample(symbol, str_time):
    df = pd.read_csv('data/' + symbol + '.csv',
                     index_col='time',
                     parse_dates=True,
                     dayfirst=True
                     )
    ohlc = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    df = df.resample(str_time, origin='start').apply(ohlc)
    df = df.drop(df[df.open.isnull()].index)
    df.to_csv(f"data/{symbol}_{str_time}.csv")
    inputs = {
        'open': np.array(df['open'].tolist()),
        'high': np.array(df['high'].tolist()),
        'low': np.array(df['low'].tolist()),
        'close': np.array(df['close'].tolist()),
    }
    return inputs


def validate_expression(expression):
    try:
        # Parse the expression to an Abstract Syntax Tree (AST)
        parsed_expression = ast.parse(expression)

        # Extract names (identifiers) from the expression
        names = [node.id for node in ast.walk(
            parsed_expression) if isinstance(node, ast.Name)]

        # Check if the names correspond to valid classes or functions
        valid_names = all(name in globals() for name in names)

        if valid_names:
            return True
        else:
            logging.info(f"Invalid names in expression: {expression.strip()}")
            return False
    except SyntaxError as e:
        logging.error(
            f"Syntax error in expression: {expression.strip()} - {str(e)}")
        return False


def is_valid_file(expression, filepath):
    try:
        # Validate each expression before evaluating:
        if not validate_expression(expression):
            logging.info(f" error in {expression} ")
            valid = False
        valid = True
        logging.info(f"Is {filepath} {valid =}?")
        return valid
    except Exception as e:
        logging.error(f"{e} while checking validity of file {filepath}")


def download_data(sym):
    df_price = pd.DataFrame()
    tkn = api.instrument_symbol("NSE", sym)
    lastBusDay = pendulum.now()
    fromBusDay = lastBusDay.subtract(months=3)
    lastBusDay = lastBusDay.replace(
        hour=0, minute=0, second=0, microsecond=0)
    fromBusDay = fromBusDay.replace(
        hour=0, minute=0, second=0, microsecond=0)
    resp = api.finvasia.get_time_price_series(
        exchange='NSE', token=tkn, starttime=fromBusDay.timestamp(),
        endtime=lastBusDay.timestamp(), interval=1
    )
    if resp is not None:
        lst_price = []
        for ret in resp:
            dct = {
                'time': ret['time'],
                'open': ret['into'],
                'high': ret['inth'],
                'low': ret['intl'],
                'close': ret['intc'],
                'volume': ret['v'],
            }
            lst_price.append(dct)
        # sort DataFrame in descending order
        df_price = pd.DataFrame(lst_price).sort_index(ascending=False)
        df_price.to_csv("data/" + sym + ".csv", index=False)
        return True
    else:
        logging.debug(f"no data for {sym}")
        return False


def update_inputs(symbol):
    month_ca.inputs = resample(symbol, '1M')
    week_ca.inputs = resample(symbol, '1W')
    day_ca.inputs = resample(symbol, '1D')
    hour_ca.inputs = resample(symbol, '1H')
    minute_ca.inputs = resample(symbol, '1Min')


def is_buy_signal(expressions):
    try:
        buy_signal = eval(expressions)
        logging.info(f"{buy_signal=}")
        return buy_signal
    except Exception as e:
        logging.error(f"error {str(e)} while generating buy signal")


month_ca = Candle()
week_ca = Candle()
day_ca = Candle()
hour_ca = Candle()
minute_ca = Candle()

api = login_and_get_token()


buy_conditions = "buy_conditions.txt"
with open(buy_conditions, 'r') as file:
    expressions = file.read().replace("/n", " ")
if is_valid_file(expressions, buy_conditions):
    symbol_list = ["PFC"]  # Add your symbols here
    for symbol in symbol_list:
        if api:
            download_data(symbol)
        update_inputs(symbol)
        is_buy_signal(expressions)
