"""
Utility functions for simple arithmetic operations.

Provides basic calculator functionality: add, subtract, multiply, and divide.
Includes a convenience `calculate` function that dispatches based on an
operation string or symbol.
"""
from typing import Callable, Union

Number = Union[int, float]


def add(a: Number, b: Number) -> Number:
    """Return the sum of a and b."""
    return a + b


def subtract(a: Number, b: Number) -> Number:
    """Return the difference of a and b (a - b)."""
    return a - b


def multiply(a: Number, b: Number) -> Number:
    """Return the product of a and b."""
    return a * b


def divide(a: Number, b: Number) -> Number:
    """Return the quotient of a and b (a / b).

    Raises ZeroDivisionError if b is zero.
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b


_OPERATION_MAP: dict[str, Callable[[Number, Number], Number]] = {
    "add": add,
    "+": add,
    "subtract": subtract,
    "-": subtract,
    "multiply": multiply,
    "*": multiply,
    "×": multiply,
    "divide": divide,
    "/": divide,
    "÷": divide,
}


def calculate(a: Number, b: Number, operation: str) -> Number:
    """Perform a calculation on a and b using the given operation.

    Operation can be one of: 'add', 'subtract', 'multiply', 'divide' or the
    corresponding symbols '+', '-', '*', '/'.

    Raises:
        KeyError: if the operation is not recognized.
        ZeroDivisionError: if division by zero is attempted.
    """
    op = operation.strip().lower()
    if op not in _OPERATION_MAP:
        raise KeyError(
            f"Unsupported operation: {operation!r}. Supported operations are: "
            ", ".join(sorted(set(_OPERATION_MAP.keys())))
        )
    return _OPERATION_MAP[op](a, b)


__all__ = [
    "add",
    "subtract",
    "multiply",
    "divide",
    "calculate",
]
