import ast


class Candle:
    def __init__(self, candle_type="standard"):
        self.data = []

    def macd(self, period):
        return period

    def ema(self, period):
        return period


candle = Candle()
ha = Candle("ha")


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
    # Read the expressions from the text file
    with open(filepath, 'r') as file:
        expressions = file.readlines()

    # Validate each expression before evaluating
    for idx, expression in enumerate(expressions):
        if not validate_expression(expression):
            print(f" {idx + 1}: error in {expression} ")
            return False
    return True


if is_valid_file("buy_conditions.txt"):
