"""
Basic math operations utilities.

Provides simple arithmetic functions for integers and floats: add, subtract,
multiply, and divide. Functions are type-annotated and documented for clarity.
"""
from typing import Union

Number = Union[int, float]


def add(a: Number, b: Number) -> Number:
    """Return the sum of a and b.

    Examples:
        >>> add(2, 3)
        5
        >>> add(2.5, 0.5)
        3.0
    """
    return a + b


def subtract(a: Number, b: Number) -> Number:
    """Return the difference of a and b (a - b).

    Examples:
        >>> subtract(5, 2)
        3
        >>> subtract(1.0, 2.5)
        -1.5
    """
    return a - b


def multiply(a: Number, b: Number) -> Number:
    """Return the product of a and b.

    Examples:
        >>> multiply(4, 3)
        12
        >>> multiply(2.0, 2.5)
        5.0
    """
    return a * b


def divide(a: Number, b: Number) -> Number:
    """Return the quotient of a and b (a / b).

    Raises:
        ZeroDivisionError: If ``b`` is zero.

    Examples:
        >>> divide(10, 2)
        5.0
        >>> divide(7.5, 2.5)
        3.0
    """
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b


__all__ = [
    "add",
    "subtract",
    "multiply",
    "divide",
]
