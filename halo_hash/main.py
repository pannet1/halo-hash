import ast
from talib import abstract
import numpy as np
from constants import futils, logging, SECDIR, CRED
from omspy_brokers.finvasia import Finvasia
import pendulum
import pandas as pd
import traceback


def login_and_get_token():
    try:
        api = Finvasia(**CRED)
        if api.authenticate():
            print("Login Successfull")
            return api
    except Exception as e:
        print(e)


class Candle:

    def __init__(self):
        self.inputs = []  # Use the shared data

    def close(self, period=-2):
        if len(self.inputs) >= period:
            value = self.inputs['close']
            value = value[period]
            logging.info(f"{value=} : {period=}")
            return value

    def high(self, period=-2):
        value = self.inputs['high'][period]
        logging.info(f"{value=} : {period}")
        return value

    def low(self, period=-2):
        value = self.inputs['low'][period]
        logging.info(f"{value=} : {period=}")
        return value

    def volume(self, period=-2):
        value = self.inputs['volume'][period]
        logging.info(f"{value=} : {period=}")
        return value

    def rsi(self, timeperiod):
        real = abstract.RSI(self.inputs, timeperiod=timeperiod)
        logging.info(f"{real[-2]=}")

    def bbands(self, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0):
        upperband, middleband, lowerband = abstract.BBANDS(
            self.inputs, timeperiod=timeperiod, nbdevup=nbdevup, nbdevdn=nbdevdn, matype=matype)
        logging.info(upperband[-2], middleband[-2], lowerband[2])
        return upperband[-2], middleband[-2], lowerband[-2]

    def adx(self, timeperiod=14):
        real = abstract.ADX(
            self.inputs['high'], self.inputs['low'], self.inputs['close'], timeperiod=timperiod)
        return real[-2]

    def stoch(self, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0):
        slowk, slowd = abstract.STOCH(self.inputs['high'],
                                      self.inputs['low'],
                                      self.inputs['close'],
                                      fastk_period=fastk_period,
                                      slowk_period=slowk_period,
                                      slowk_matype=slowk_matype,
                                      slowd_period=slowd_period,
                                      slowd_matype=slowd_matype
                                      )
        return slowk[-2], slowd[-2]

    def macd(self, fastperiod, slowperiod, signalperiod):
        try:
            _, macdsignal, _ = abstract.MACD(self.inputs,
                                             fastperiod=fastperiod,
                                             slowperiod=slowperiod,
                                             signalperiod=signalperiod)
            logging.debug(f"macd: {macdsignal[-2]}")
            return macdsignal[-2]
        except Exception as e:
            logging.warning(f"error {e} in macd")

    def ema(self, timeperiod):
        try:
            result = abstract.EMA(
                self.inputs,
                timeperiod=timeperiod)
            logging.debug(f"ema: {result[-2]}")
            return result[-2]
        except Exception as e:
            logging.error(e)

    def stochsrsi(self, timeperiod=14, fastk_period=5, fastd_period=3, fastd_matype=0):
        fastk, fastd = abstract.STOCHRSI(
            self.inputs,
            timeperiod=timeperiod,
            fastk_period=fastk_period,
            fastd_period=fastd_period,
            fastd_matype=fastd_matype)
        print(f" stockrsi: {fastk=} {fastd=} ")
        return fastk, fastd


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


def ha(symbol, str_time):
    df = pd.read_csv(f"data/{symbol}_{str_time}.csv")
    print(df)
    return 100


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
    month_ha.inputs = ha(symbol, '1M')


def is_buy_signal(expressions):
    try:
        buy_signal = eval(expressions)
        logging.info(f"{buy_signal=}")
        return buy_signal
    except Exception as e:
        traceback.format_exc
        logging.error(f"error {str(e)} while generating buy signal")


month_ca = Candle()
week_ca = Candle()
day_ca = Candle()
hour_ca = Candle()
minute_ca = Candle()
month_ha = Candle()

api = login_and_get_token()


buy_conditions = "buy_conditions.txt"
with open(buy_conditions, 'r') as file:
    expressions = file.read().replace("\n", " ")

if is_valid_file(expressions, buy_conditions):
    symbol_list = ["PFC"]  # Add your symbols here
    for symbol in symbol_list:
        if api:
            download_data(symbol)
        update_inputs(symbol)
        is_buy_signal(expressions)
