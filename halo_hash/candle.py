import logging
import talib
import ta as bta

class Candle:
    """
    for examples of ta lib search for programcreek
    """

    def __init__(self, period: str):
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

    def open(self, candle_number=-2):
        value = self.inputs["open"][candle_number]
        logging.debug(f"open[{candle_number}]: {value}")
        return value

    def high(self, candle_number=-2):
        value = self.inputs["high"][candle_number]
        logging.debug(f"high[{candle_number}]: {value}")
        return value

    def low(self, candle_number=-2):
        value = self.inputs["low"][candle_number]
        logging.debug(f"close[{candle_number}]: {value}")
        return value

    def close(self, candle_number=-2):
        if len(self.inputs) >= candle_number:
            value = self.inputs["close"][candle_number]
            logging.debug(f"close[{candle_number}]: {value}")
            return value

    def volume(self, candle_number=-2):
        value = self.inputs["volume"][candle_number]
        logging.debug(f"volume{candle_number}: {value}")
        return value
    
    def vwap(self, candle_number=-2):
        value = self.inputs["vwap"][candle_number]
        logging.debug(f"vwap{candle_number}: {value}")
        return value

    def adx(self, timeperiod=5, candle_number=-2):
        """
        Calculate the Average Directional Index (ADX) for a given candle.

        Parameters:
        - timeperiod (int): The time period for ADX calculation.
        - candle_number (int): The candle number for which to calculate ADX.
          A negative value indicates counting from the most recent candle.

        Returns:
        - float: The ADX value for the specified candle.
        """
        value = talib.ADX(
            self.inputs["high"],
            self.inputs["low"],
            self.inputs["close"],
            timeperiod=timeperiod,
        )
        self.write_col_to_csv("adx", value)
        logging.debug(f"adx[{candle_number}]: {value[candle_number]}")
        return value[candle_number]

    def plusdi(self, timeperiod=5, candle_number=-2):
        """
        Calculate the Plus Directional Indicator (PLUS_DI) for a given candle.

        Parameters:
        - timeperiod (int): The time period for PLUS_DI calculation.
        - candle_number (int): The candle number for which to calculate PLUS_DI.
                              A negative value indicates counting from the most recent candle.

        Returns:
        - float: The PLUS_DI value for the specified candle.
        """
        value = talib.PLUS_DI(
            self.inputs["high"],
            self.inputs["low"],
            self.inputs["close"],
            timeperiod=timeperiod,
        )
        self.write_col_to_csv("plusdi", value)
        logging.debug(f"plusdi: {value[candle_number]}")
        return value[candle_number]

    def minusdi(self, timeperiod=5, candle_number=-2):
        """
        Calculate the Minus Directional Indicator (MINUS_DI) for a given candle.

        Parameters:
        - timeperiod (int): The time period for MINUS_DI calculation.
        - candle_number (int): The candle number for which to calculate MINUS_DI.
                              A negative value indicates counting from the most recent candle.

        Returns:
        - float: The MINUS_DI value for the specified candle.
        """
        value = talib.MINUS_DI(
            self.inputs["high"],
            self.inputs["low"],
            self.inputs["close"],
            timeperiod=timeperiod,
        )
        self.write_col_to_csv("minusdi", value)
        logging.debug(f"minusdi: {value[candle_number]}")
        return value[candle_number]

    def bbands(self, timeperiod=5, nbdev=2, matype=0, candle_number=-2, band="lower"):
        """
        Calculate Bollinger Bands (BBANDS) for a given candle.

        Parameters:
        - timeperiod (int): The time period for BBANDS calculation.
        - nbdev (float): The number of standard deviations to use.
        - matype (int): The type of moving average to use.
        - candle_number (int): The candle number for which to calculate BBANDS.
                              A negative value indicates counting from the most recent candle.
        - band (str): The type of band to calculate ('upper', 'middle', or 'lower').

        Returns:
        - float: The specified BBANDS value for the specified candle.
        """
        nbdev = nbdev * 1.00
        ub, mb, lb = talib.BBANDS(
            self.inputs["close"],
            timeperiod=timeperiod,
            nbdevup=nbdev,
            nbdevdn=nbdev,
            matype=matype,
        )

        if band == "upper":
            self.write_col_to_csv("bbands_upper", ub)
            logging.debug(f"bbands {band}[{candle_number}]: {ub[candle_number]}")
            return ub[candle_number]
        elif band == "middle":
            self.write_col_to_csv("bbands_middle", mb)
            logging.debug(f"bbands {band}[{candle_number}]: {mb[candle_number]}")
            return mb[candle_number]
        else:
            self.write_col_to_csv("bbands_lower", lb)
            logging.debug(f"bbands {band}[{candle_number}]: {lb[candle_number]}")
            return lb[candle_number]

    def sma(self, timeperiod=5, candle_number=-1):
        """
        Calculate the simple Moving Average (SMA) for a given candle.

        Parameters:
        - timeperiod (int): The time period for SMA calculation.
        - candle_number (int): The candle number for which to calculate SMA.
                              A negative value indicates counting from the most recent candle.

        Returns:
        - float: The SMA value for the specified candle.
        """
        try:
            result = talib.SMA(self.inputs, timeperiod=timeperiod)
            self.write_col_to_csv("sma", result)
            logging.debug(f"sma[{candle_number}]: {result[candle_number]}")
            return result[candle_number]
        except Exception as e:
            logging.error(e)

    def ema(self, timeperiod=5, candle_number=-1):
        """
        Calculate the Exponential Moving Average (EMA) for a given candle.

        Parameters:
        - timeperiod (int): The time period for EMA calculation.
        - candle_number (int): The candle number for which to calculate EMA.
                              A negative value indicates counting from the most recent candle.

        Returns:
        - float: The EMA value for the specified candle.
        """
        try:
            result = talib.EMA(self.inputs, timeperiod=timeperiod)
            self.write_col_to_csv("ema", result)
            logging.debug(f"ema[{candle_number}]: {result[candle_number]}")
            return result[candle_number]
        except Exception as e:
            logging.error(e)

    def macd(
        self, fastperiod=5, slowperiod=5, signalperiod=5, candle_number=-2, which="hist"
    ):
        """
        Calculate Moving Average Convergence Divergence (MACD) values for a given candle.

        Parameters:
        - fastperiod (int): The time period for fast EMA calculation.
        - slowperiod (int): The time period for slow EMA calculation.
        - signalperiod (int): The time period for the signal line calculation.
        - candle_number (int): The candle number for which to calculate MACD values.
                              A negative value indicates counting from the most recent candle.
        - which (str): The component of MACD to retrieve ('line', 'signal', or 'hist').

        Returns:
        - float: The specified MACD component value for the specified candle.
        """
        try:
            line, signal, hist = talib.MACD(
                self.inputs["close"],
                fastperiod=fastperiod,
                slowperiod=slowperiod,
                signalperiod=signalperiod,
            )
            self.write_col_to_csv("macd_line", line)
            self.write_col_to_csv("macd_signal", signal)
            self.write_col_to_csv("macd_hist", hist)
            logging.debug(
                f"macd: line[{candle_number}]: {line[candle_number]} "
                f"signal[{candle_number}]: {signal[candle_number]} "
                f"hist[{candle_number}]: {hist[candle_number]}"
            )
            if which == "line":
                return line[candle_number]
            elif which == "signal":
                return signal[candle_number]
            else:
                return hist[candle_number]
        except Exception as e:
            logging.error(f"error {e} in macd")

    def rsi(self, timeperiod, candle_number=-1):
        """
        Calculate the Relative Strength Index (RSI) for a given candle.

        Parameters:
        - timeperiod (int): The time period for RSI calculation.
        - candle_number (int): The candle number for which to calculate RSI.
                              A negative value indicates counting from the most recent candle.

        Returns:
        - float: The RSI value for the specified candle.
        """
        value = talib.RSI(self.inputs["close"], timeperiod=timeperiod)
        self.write_col_to_csv("rsi", value)
        logging.debug(f"rsi[{candle_number}]: {value[candle_number]}")
        return value[candle_number]

    def stoch(
        self,
        fastk_period=5,
        slowk_period=3,
        slowk_matype=0,
        slowd_period=3,
        slowd_matype=0,
        candle_number=-2,
    ):
        """
        Calculate the Stochastic Oscillator (STOCH) values for a given candle.

        Parameters:
        - fastk_period (int): The time period for fast %K calculation.
        - slowk_period (int): The time period for slow %K calculation.
        - slowk_matype (int): The type of moving average to use for slow %K.
        - slowd_period (int): The time period for %D calculation.
        - slowd_matype (int): The type of moving average to use for %D.
        - candle_number (int): The candle number for which to calculate STOCH values.
                              A negative value indicates counting from the most recent candle.

        Returns:
        - float: The specified STOCH value for the specified candle.
        """
        slowk, slowd = talib.STOCH(
            self.inputs["high"],
            self.inputs["low"],
            self.inputs["close"],
            fastk_period=fastk_period,
            slowk_period=slowk_period,
            slowk_matype=slowk_matype,
            slowd_period=slowd_period,
            slowd_matype=slowd_matype,
        )
        self.write_col_to_csv("stoch_slowk", slowk)
        self.write_col_to_csv("stoch_slowd", slowd)
        return slowk[candle_number], slowd[candle_number]

    def stochsrsi(
        self,
        timeperiod=14,
        fastk_period=5,
        fastd_period=3,
        fastd_matype=0,
        candle_number=-2,
        which="fastk",
    ):
        """
        Calculate Stochastic RSI (STOCHRSI) values for a given candle.

        Parameters:
        - timeperiod (int): The time period for RSI calculation.
        - fastk_period (int): The time period for fast %K calculation.
        - fastd_period (int): The time period for fast %D calculation.
        - fastd_matype (int): The type of moving average to use for fast %D.
        - candle_number (int): The candle number for which to calculate STOCHRSI values.
          A negative value indicates counting from the most recent candle.
        - which (str): The component of STOCHRSI to retrieve ('fastk' or 'fastd').

        Returns:
        - float: The specified STOCHRSI component value for the specified candle.
        """
        fastk, fastd = talib.STOCHRSI(
            self.inputs,
            timeperiod=timeperiod,
            fastk_period=fastk_period,
            fastd_period=fastd_period,
            fastd_matype=fastd_matype,
        )
        self.write_col_to_csv("stochrsi_fastk", fastk)
        self.write_col_to_csv("stochrsi_fastd", fastd)
        logging.debug(f" stockrsi: {fastk=} {fastd=}")
        if which == "fastk":
            return fastk[candle_number]
        else:
            return fastd[candle_number]
