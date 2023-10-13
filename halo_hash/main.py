import ast
import talib
import numpy as np
from constants import futils, logging, CRED
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
    """
    for examples of ta lib search for programcreek
    """

    def __init__(self, period):
        self.period = period
        self.inputs = []  # Use the shared data
        self.symbol = ""

    def write_col_to_csv(self, column_name: str, column):
        try:
            pass
            """
            csv_file = "data/" + self.symbol+"_" + self.period + ".csv"
            df = pd.read_csv(csv_file).reset_index()
            df.drop(df[column_name], axis=1, inplace=True)
            df[column_name] = column
            df.to_csv(csv_file, index=False)
            """
        except Exception as e:
            print(f"while writing indicator to csv {e}")

    def open(self, idx=-2):
        value = self.inputs['open'][idx]
        logging.debug(f"open[{idx}]: {value}")
        return value

    def high(self, idx=-2):
        value = self.inputs['high'][idx]
        logging.debug(f"high[{idx}]: {value}")
        return value

    def low(self, idx=-2):
        value = self.inputs['low'][idx]
        logging.debug(f"close[{idx}]: {value}")
        return value

    def close(self, idx=-2):
        if len(self.inputs) >= idx:
            value = self.inputs['close'][idx]
            logging.debug(f"close[{idx}]: {value}")
            return value

    def volume(self, idx=-2):
        value = self.inputs['volume'][idx]
        logging.debug(f"volume{idx}: {value}")
        return value

    # Update the adx method
    def adx(self, timeperiod=5, idx=-2):
        value = talib.ADX(
            self.inputs['high'], self.inputs['low'], self.inputs['close'], timeperiod=timeperiod)
        self.write_col_to_csv("adx", value)
        logging.debug(f"adx[{idx}]: {value[idx]}")
        return value[idx]

    # Update the plusdi method
    def plusdi(self, timeperiod=5, idx=-2):
        value = talib.PLUS_DI(
            self.inputs['high'], self.inputs['low'],  self.inputs['close'], timeperiod=timeperiod)
        self.write_col_to_csv("plusdi", value)
        logging.debug(f"plusdi: {value[idx]}")
        return value[idx]

    # Update the minusdi method
    def minusdi(self, timeperiod=5, idx=-2):
        value = talib.MINUS_DI(
            self.inputs['high'], self.inputs['low'],  self.inputs['close'], timeperiod=timeperiod)
        self.write_col_to_csv("minusdi", value)
        logging.debug(f"minusdi: {value[idx]}")
        return value[idx]

    # Update the bbands method for upper, middle, and lower
    def bbands(self, timeperiod=5, nbdev=2, matype=0, idx=-2, band="lower"):
        nbdev = nbdev * 1.00
        ub, mb, lb = talib.BBANDS(
            self.inputs['close'], timeperiod=timeperiod, nbdevup=nbdev, nbdevdn=nbdev, matype=matype)

        if band == "upper":
            self.write_col_to_csv("bbands_upper", ub)
            logging.debug(f"bbands {band}[{idx}]: {ub[idx]}")
            return ub[idx]
        elif band == "middle":
            self.write_col_to_csv("bbands_middle", mb)
            logging.debug(f"bbands {band}[{idx}]: {mb[idx]}")
            return mb[idx]
        else:
            self.write_col_to_csv("bbands_lower", lb)
            logging.debug(f"bbands {band}[{idx}]: {lb[idx]}")
            return lb[idx]

    # Update the ema method
    def ema(self, timeperiod, idx=-1):
        try:
            result = talib.EMA(
                self.inputs,
                timeperiod=timeperiod)
            self.write_col_to_csv("ema", result)
            logging.debug(f"ema[{idx}]: {result[idx]}")
            return result[idx]
        except Exception as e:
            logging.error(e)

    # Update the macd method for line, signal, and hist
    def macd(self, fastperiod, slowperiod, signalperiod, idx=-2, which="hist"):
        try:
            line, signal, hist = talib.MACD(self.inputs['close'],
                                            fastperiod=fastperiod,
                                            slowperiod=slowperiod,
                                            signalperiod=signalperiod)
            self.write_col_to_csv("macd_line", line)
            self.write_col_to_csv("macd_signal", signal)
            self.write_col_to_csv("macd_hist", hist)
            logging.debug(
                f"macd: line[{idx}]: {line[idx]} "
                f"signal[{idx}]: {signal[idx]} "
                f"hist[{idx}]: {hist[idx]}"
            )
            if which == "line":
                return line[idx]
            elif which == "signal":
                return signal[idx]
            else:
                return hist[idx]
        except Exception as e:
            logging.error(f"error {e} in macd")

    # Update the rsi method
    def rsi(self, timeperiod, idx=-1):
        value = talib.RSI(self.inputs['close'], timeperiod=timeperiod)
        self.write_col_to_csv("rsi", value)
        logging.debug(f"rsi[{idx}]: {value[idx]}")
        return value[idx]

    # Update the stoch method
    def stoch(self, fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0, idx=-2):
        slowk, slowd = talib.STOCH(self.inputs['high'],
                                   self.inputs['low'],
                                   self.inputs['close'],
                                   fastk_period=fastk_period,
                                   slowk_period=slowk_period,
                                   slowk_matype=slowk_matype,
                                   slowd_period=slowd_period,
                                   slowd_matype=slowd_matype
                                   )
        self.write_col_to_csv("stoch_slowk", slowk)
        self.write_col_to_csv("stoch_slowd", slowd)
        return slowk[idx], slowd[idx]

    # Update the stochsrsi method
    def stochsrsi(self, timeperiod=14, fastk_period=5, fastd_period=3, fastd_matype=0):
        fastk, fastd = talib.STOCHRSI(
            self.inputs,
            timeperiod=timeperiod,
            fastk_period=fastk_period,
            fastd_period=fastd_period,
            fastd_matype=fastd_matype)
        self.write_col_to_csv("stochrsi_fastk", fastk)
        self.write_col_to_csv("stochrsi_fastd", fastd)
        print(f" stockrsi: {fastk=} {fastd=}")
        return fastk, fastd


def resample(symbol, str_time):
    filepath = f"data/{symbol}.csv"
    df = pd.read_csv(filepath,
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
    # df = df.drop(df[df.open.isnull()].index)
    df.to_csv(f"data/{symbol}_{str_time}.csv")
    inputs = {
        'time': df.index.tolist(),
        'open': np.array(df['open'].tolist()),
        'high': np.array(df['high'].tolist()),
        'low': np.array(df['low'].tolist()),
        'close': np.array(df['close'].tolist()),
    }
    return inputs


def ha(symbol, str_time):
    df = pd.read_csv(f"data/{symbol}_{str_time}.csv")
    print(df)
    pass


def validate_expression(expression):
    try:
        # Parse the expression to an talib Syntax Tree (AST)
        parsed_expression = ast.parse(expression)

        # Extract names (identifiers) from the expression
        names = [node.id for node in ast.walk(
            parsed_expression) if isinstance(node, ast.Name)]

        # Check if the names correspond to valid classes or functions
        valid_names = all(name in globals() for name in names)

        if valid_names:
            return True
        else:
            logging.error(f"Invalid names in expression: {expression.strip()}")
            return False
    except SyntaxError as e:
        logging.error(
            f"Syntax error in expression: {expression.strip()} - {str(e)}")
        return False


def is_valid_file(expression, filepath):
    try:
        # Validate each expression before evaluating:
        if not validate_expression(expression):
            logging.error(f" error in {expression} ")
            valid = False
        valid = True
        logging.debug(f"Is {filepath} {valid =}?")
        return valid
    except Exception as e:
        logging.error(f"{e} while checking validity of file {filepath}")


def download_data(symbol):
    filepath = f"data/{symbol}.csv"
    if not futils.is_file_not_2day(filepath):
        logging.debug(f"{filepath} modified today")
        df_price = pd.DataFrame()
        tkn = api.instrument_symbol("NSE", symbol)
        lastBusDay = pendulum.now()
        fromBusDay = lastBusDay.subtract(months=24)
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
            df_price.to_csv(filepath, index=False)
            return True
        else:
            logging.warning(f"no data for {symbol}")
            return False
    else:
        logging.debug(f"using {filepath} already modfied today")
        return True


def update_inputs(symbol):
    month_ca.inputs = resample(symbol, '1M')
    month_ca.symbol = symbol
    week_ca.inputs = resample(symbol, '1W')
    week_ca.symbol = symbol
    day_ca.inputs = resample(symbol, '1D')
    day_ca.symbol = symbol
    hour_ca.inputs = resample(symbol, '1H')
    hour_ca.symbol = symbol
    minute_ca.inputs = resample(symbol, '1Min')
    minute_ca.symbol = symbol
    month_ha.inputs = ha(symbol, '1M')


def is_buy_signal(expressions):
    try:
        buy_signal = eval(expressions)
        logging.info(f"{buy_signal=}")
        return buy_signal
    except Exception as e:
        traceback.format_exc
        logging.error(f"error {str(e)} while generating buy signal")


month_ca = Candle("1M")
week_ca = Candle("1W")
day_ca = Candle("1D")
hour_ca = Candle("1H")
minute_ca = Candle("1Min")
month_ha = Candle("1M")

api = login_and_get_token()


"""
if (
month_ca.close(-2) < month_ca.close(-3)
and month_ca.adx(3) > 5
and month_ca.rsi(3) > 30
and month_ca.bbands(5, 2, 0, -1, "upper") > month_ca.bbands(5, 2, 0, -2, "upper")
and month_ca.macd(5,8, 3, -1, "line") > month_ca.macd(5, 8, 3, -2, "line")
and month_ca.plusdi(5) > month_ca.minusdi(5)
):

    • [0] Monthly RSI(14) Greater than Number 30.
    • [0] Monthly Upper Bollinger band(20, 2) greater than 1 month ago Upper Bollinger band(20, 2)
    • [0] Monthly ADX(14) greater than Number 5
    • [0] Monthly ADX DI Positive(14) greater than[0] Monthly ADX DI Negative(14)
    • [0] Monthly MACD line(26, 12, 9) Greater than[0] Monthly signal(26, 12, 9)
    • [0] Monthly MACD line(26, 12, 9) greater than 1 month ago MACD line(26, 12, 9)
    • [0] Weekly RSI(14) Greater than Number 30
    • [0] Weekly HA close is greater than Weekly HA Open.
    • [0] Weekly ADX(14) greater than Number 5
    • [0] Weekly Close greater than Weekly EMA 200 (Weekly Close, 200)
    • [0] Weekly MACD line(26, 12, 9) greater than Number 0.
    • [0] Weekly MACD line(26, 12, 9) greater than 1 week ago MACD line(26, 12, 9)
    • 1 week ago MACD line(26, 12, 9) greater than 2 week ago MACD line(26, 12, 9)
    • [0] Daily RSI(14) less than Number 70
    • [0] Daily RSI(14) greater than number 30
    • [0] Daily StochRSI(14) less than number 20
    • [0] Daily EMA 200 greater than 1 Day ago EMA 200.
    • 1 Day ago EMA 200 greater than 2 Day ago EMA 200.
    • 2 Day ago EMA 200 greater than 3 Day ago EMA 200.
"""

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
