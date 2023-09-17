import ast
from talib import abstract
import numpy as np


class Candle:
    def __init__(self, period='1sec'):
        # note that all ndarrays must be the same length!
        self.inputs = {
            'open': np.random.random(100),
            'high': np.random.random(100),
            'low': np.random.random(100),
            'close': np.random.random(100),
            'volume': np.random.random(100)
        }

    def macd(self, fastperiod, slowperiod, signalperiod):
        _, macdsignal, _ = abstract.MACD(self.inputs,
                                         fastperiod=fastperiod,
                                         slowperiod=slowperiod,
                                         signalperiod=signalperiod)
        print(macdsignal[-1])
        return macdsignal[-1]

    def ema(self, timeperiod):
        result = abstract.EMA(self.inputs['close'], timeperiod=timeperiod)
        print(result[-1])
        return result[-1]


month_ca = Candle("1Month")
week_ca = Candle("1Week")
day_ca = Candle("1Day")
hour_ca = Candle("1Hour")
minute_ca = Candle("5Minute")
second_ca = Candle("1Second")


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
            print(f"Invalid names in expression: {expression.strip()}")
            return False
    except SyntaxError as e:
        print(f"Syntax error in expression: {expression.strip()} - {str(e)}")
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
        print(f"{e} while chekcing validity of file {filepath}")


try:
    filepath = "buy_conditions.txt"
    if is_valid_file(filepath):
        with open(filepath, 'r') as file:
            expressions = file.readlines()

        for _, expression in enumerate(expressions):
            buy_signal = eval(expression)
            print(buy_signal)
except Exception as e:
    print(e)
