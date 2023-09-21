import ast
from talib import abstract
import numpy as np
from constants import futils, logging, SECDIR, CRED
from omspy_brokers.finvasia import Finvasia
import pendulum
import pandas as pd


def login_and_get_token():
    try:
        api = None
        api = Finvasia(**CRED)
        api.login()
        if api.login():
            print("Login Successfull")
        else:
            print("Login Failed")
    except Exception as e:
        print(e)
    finally:
        return api


# api = login_and_get_token()


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
        # df_price = pd.DataFrame(lst_price).sort_index(ascending=False)
        df_price.to_csv(sym + ".csv", index=False)
    else:
        print("no data")
    return df_price


"""
cls.shared_data = {
    'open': np.random.random(100),
    'high': np.random.random(100),
    'low': np.random.random(100),
    'close': np.random.random(100),
    'volume': np.random.random(100)
}
"""


class Candle():

    def __init__(self, period='1sec'):
        self.inputs = []  # Use the shared data

    def macd(self, fastperiod, slowperiod, signalperiod):
        _, macdsignal, _ = abstract.MACD(self.inputs,
                                         fastperiod=fastperiod,
                                         slowperiod=slowperiod,
                                         signalperiod=signalperiod)
        logging.debug(f"macd: {macdsignal[-1]}")
        return macdsignal[-1]

    def ema(self, timeperiod):
        try:
            result = abstract.EMA(self.inputs['close'], timeperiod=timeperiod)
            print(f"ema: {result[-1]}")
            return result[-1]
        except Exception as e:
            logging.error(e)


month_ca = Candle("month")
week_ca = Candle("week")
day_ca = Candle("day")
hour_ca = Candle("hour")
minute_ca = Candle("minute")
second_ca = Candle("second")


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


def is_valid_file(filepath):
    try:
        # Read the expressions from the text file
        with open(filepath, 'r') as file:
            expressions = file.readlines()

        # Validate each expression before evaluating
        for idx, expression in enumerate(expressions):
            if not validate_expression(expression):
                print(f" {idx + 1}: error in {expression} ")
                return False
        return True
    except Exception as e:
        logging.error(f"{e} while checking validity of file {filepath}")


def is_buy_signal():
    try:
        filepath = "buy_conditions.txt"
        if is_valid_file(filepath):
            # Read the expressions from the text file
            with open(filepath, 'r') as file:
                expressions = file.readlines()

                # Validate each expression before evaluating
            for _, expression in enumerate(expressions):
                buy_signal = eval(expression)
                print(f"{expression} = {buy_signal}")
                if not buy_signal:
                    return False
            return True
    except Exception as e:
        logging.error(e)


# Create a list of symbols to iterate through
symbol_list = ["PFC"]  # Add your symbols here


filepath = "buy_conditions.txt"


def resample(symbol, str_time):
    df = pd.read_csv(symbol + '.csv',
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
    df.to_csv(f"{symbol}_{str_time}.csv")
    inputs = {
        'time': df.index.tolist(),
        'open': np.array(df['open'].tolist()),
        'high': np.array(df['high'].tolist()),
        'low': np.array(df['low'].tolist()),
        'close': np.array(df['close'].tolist()),
    }
    return inputs


def update_inputs(symbol):
    # download_data(symbol)
    month_ca.inputs = resample(symbol, '1M')
    week_ca.inputs = resample(symbol, '1W')
    day_ca.inputs = resample(symbol, '1D')
    hour_ca.inputs = resample(symbol, '1H')
    minute_ca.inputs = resample(symbol, '1Min')
    second_ca.inputs = resample(symbol, '1S')


def get_buy_signal_for_symbol():
    if is_valid_file(filepath):
        # Read the expressions from the text file
        with open(filepath, 'r') as file:
            expressions = file.readlines()
        # Update the data in the week_ca instance for the given symbol
        for symbol in symbol_list:
            update_inputs(symbol)
            # Validate each expression before evaluating
            for _, expression in enumerate(expressions):
                buy_signal = eval(expression)
                print(f"{expression} = {buy_signal}")

    return buy_signal


get_buy_signal_for_symbol()


"""

        # Define your buy condition expression
        buy_condition_expression = "week_ca.macd(26, 12, 9) > week_ca.macd(14, 12, 6) and week_ca.ema(20) > week_ca.ema(12)"

        # Evaluate the buy condition expression for the given symbol
        buy_signal = eval(buy_condition_expression)
        buy_signal = get_buy_signal_for_symbol(symbol)
        print(f"{symbol}: Buy Signal = {buy_signal}")
"""
