"""
Validation utilities for input sanitization, type checking, and schema-based
validation with rich error handling.

This module provides:
- Sanitizers for strings, numerics, and collections
- A robust runtime type checker supporting typing constructs (Optional, Union,
  List, Dict, Set, Tuple, Literal)
- Declarative schema validation with per-field sanitizers and validators
- Helpful exceptions with error codes and data paths
- A decorator to validate and sanitize function arguments

Example
-------
from xcode.validation import (
    FieldSpec, validate_schema, sanitize_string, in_range, one_of
)

schema = {
    "name": FieldSpec(str, sanitizer=lambda s: sanitize_string(s, max_length=64),
                       validators=[lambda v: v or (_ for _ in ()).throw(ValueError("empty"))]),
    "age": FieldSpec(int, allow_none=False, validators=[in_range(min=0, max=120)]),
    "role": FieldSpec(str, validators=[one_of({"user", "admin"})], required=False, default="user"),
}

clean = validate_schema({"name": "  Ada  ", "age": "33"}, schema)
# {'name': 'Ada', 'age': 33, 'role': 'user'}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Type, Union, Set, get_args, get_origin
import re
import unicodedata

__all__ = [
    "ValidationError",
    "AggregateValidationError",
    "TypeValidationError",
    "SanitizationError",
    "FieldSpec",
    "sanitize_string",
    "sanitize_numeric",
    "sanitize_collection",
    "validate_type",
    "validate_schema",
    "matches_regex",
    "in_range",
    "length_between",
    "one_of",
    "non_empty",
    "validate_args",
    "coerce_bool",
]


class ValidationError(Exception):
    """Base validation error with helpful context.

    Attributes
    - message: Human-readable error description
    - path: Dot/bracket path to the value within nested data structures
    - code: Machine-readable error code (e.g., 'type_error', 'missing_field')
    - cause: Optional underlying exception
    """

    def __init__(self, message: str, path: Optional[str] = None, code: Optional[str] = None, cause: Optional[BaseException] = None):
        super().__init__(message)
        self.message = message
        self.path = path
        self.code = code
        self.cause = cause

    def __str__(self) -> str:  # pragma: no cover - straightforward formatting
        p = f" at {self.path}" if self.path else ""
        c = f" (code={self.code})" if self.code else ""
        return f"{self.message}{p}{c}"


class AggregateValidationError(ValidationError):
    """Aggregates multiple validation errors for schema validation."""

    def __init__(self, errors: Sequence[ValidationError], path: Optional[str] = None, message: str = "Multiple validation errors"):
        super().__init__(message=message, path=path, code="multiple_errors")
        self.errors = list(errors)

    def __str__(self) -> str:  # pragma: no cover - formatting
        header = super().__str__()
        details = "\n".join(f" - {e}" for e in self.errors)
        return f"{header}\n{details}" if details else header


# --------------------
# Sanitizers
# --------------------
class SanitizationError(ValidationError):
    pass


def sanitize_string(
    value: Any,
    *,
    strip: bool = True,
    collapse_whitespace: bool = True,
    normalize: Optional[str] = "NFKC",
    remove_control: bool = True,
    max_length: Optional[int] = None,
    allow_newlines: bool = False,
) -> str:
    """Convert an arbitrary value to a clean string.

    - Converts value to str
    - Unicode normalizes (default NFKC)
    - Strips and collapses internal whitespace
    - Removes control characters by default
    - Optionally enforces a maximum length
    - Optionally forbids newlines
    """
    try:
        s = str(value)
    except Exception as exc:  # pragma: no cover - defensive
        raise SanitizationError("cannot convert to string", code="sanitization_error", cause=exc)

    if normalize:
        s = unicodedata.normalize(normalize, s)

    if remove_control:
        # Remove most C0/C1 controls except acceptable whitespace (space/newline optionally)
        def _keep(ch: str) -> bool:
            if ch == "\n" and allow_newlines:
                return True
            if ch.isspace() and ch != "\n":
                return True
            cat = unicodedata.category(ch)
            return not cat.startswith("C")

        s = "".join(ch for ch in s if _keep(ch))

    if strip:
        s = s.strip()

    if collapse_whitespace:
        pattern = "\s+" if allow_newlines else "[\s\u00A0]+"
        s = re.sub(pattern, " ", s, flags=re.UNICODE).strip()

    if not allow_newlines and ("\n" in s or "\r" in s):
        s = s.replace("\r", " ").replace("\n", " ")
        s = re.sub("\s+", " ", s).strip()

    if max_length is not None and len(s) > max_length:
        s = s[:max_length]

    return s


def coerce_bool(value: Any) -> bool:
    """Coerce common truthy/falsey representations to a bool.

    Accepts: True/False, 1/0, 'true'/'false', 'yes'/'no', 'y'/'n', 'on'/'off'
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if value is None:
        return False
    s = sanitize_string(value).lower()
    truthy = {"true", "1", "yes", "y", "on"}
    falsy = {"false", "0", "no", "n", "off"}
    if s in truthy:
        return True
    if s in falsy:
        return False
    raise SanitizationError(f"cannot coerce '{value}' to bool", code="sanitization_error")


def sanitize_numeric(
    value: Any,
    *,
    coerce: bool = True,
    allow_float: bool = False,
    minimum: Optional[float] = None,
    maximum: Optional[float] = None,
) -> Union[int, float]:
    """Sanitize numeric input.

    If coerce is True, parses strings like '42', '3.14'.
    Enforces optional min/max constraints.
    """
    original = value

    if isinstance(value, bool):  # bools are ints in Python, but usually undesired here
        value = int(value)

    if isinstance(value, (int, float)):
        num: Union[int, float] = value
    elif coerce and isinstance(value, str):
        s = sanitize_string(value)
        try:
            if "." in s or "e" in s.lower():
                num = float(s)
            else:
                num = int(s)
        except ValueError as exc:
            raise SanitizationError(f"cannot parse number from '{original}'", code="sanitization_error", cause=exc)
    elif coerce and value is not None:
        # Try using Python's numeric conversions
        try:
            num = float(value) if allow_float else int(value)  # type: ignore[arg-type]
        except Exception as exc:  # pragma: no cover - defensive
            raise SanitizationError(f"cannot coerce '{original}' to number", code="sanitization_error", cause=exc)
    else:
        raise SanitizationError("value is not numeric", code="sanitization_error")

    if not allow_float and isinstance(num, float):
        # Ensure it's an integer-valued float if allow_float=False
        if not num.is_integer():
            raise SanitizationError("expected integer but got float", code="type_error")
        num = int(num)

    if minimum is not None and num < minimum:
        raise ValidationError(f"value {num} < minimum {minimum}", code="range_error")
    if maximum is not None and num > maximum:
        raise ValidationError(f"value {num} > maximum {maximum}", code="range_error")

    return num


def sanitize_collection(
    value: Any,
    *,
    item_sanitizer: Optional[Callable[[Any], Any]] = None,
    unique: bool = False,
    max_items: Optional[int] = None,
    as_tuple: bool = False,
) -> Union[List[Any], Tuple[Any, ...]]:
    """Sanitize a sequence.

    - Accepts lists/tuples/sets and iterables (excl. str/bytes)
    - Applies item_sanitizer to each item if provided
    - Optionally ensures uniqueness and a maximum size
    - Optionally returns a tuple
    """
    if value is None:
        seq: Iterable[Any] = []
    elif isinstance(value, (list, tuple, set)):
        seq = value
    elif isinstance(value, (str, bytes)):
        raise SanitizationError("strings are not valid sequences here", code="type_error")
    else:
        try:
            seq = list(value)  # type: ignore[arg-type]
        except Exception as exc:
            raise SanitizationError("value is not an iterable", code="type_error", cause=exc)

    items: List[Any] = []
    for idx, item in enumerate(seq):
        try:
            cleaned = item_sanitizer(item) if item_sanitizer else item
        except ValidationError as e:
            e.path = f"[{idx}]" if not e.path else f"[{idx}].{e.path}"
            raise
        items.append(cleaned)

    if unique:
        # Preserve order while removing duplicates
        seen = set()
        deduped: List[Any] = []
        for it in items:
            key = it
            try:
                if key in seen:
                    continue
                seen.add(key)
            except TypeError:  # unhashable -> fallback to slower check
                if any(it == x for x in deduped):
                    continue
            deduped.append(it)
        items = deduped

    if max_items is not None and len(items) > max_items:
        items = items[:max_items]

    return tuple(items) if as_tuple else items


# --------------------
# Type checking
# --------------------
class TypeValidationError(ValidationError):
    pass


def _is_instance_of_typing(value: Any, expected: Any) -> bool:
    """Runtime check supporting common typing constructs.

    Supports: Optional, Union, List[T], Set[T], Tuple[...], Dict[K,V], Literal
    """
    origin = get_origin(expected)
    args = get_args(expected)

    if origin is None:
        # Not a typing construct; treat as normal type
        if expected is Any:
            return True
        if isinstance(expected, tuple):  # fallback for direct tuples of types
            return isinstance(value, expected)
        if isinstance(expected, type):
            return isinstance(value, expected)
        # Literal and others might come here on older versions
        return True

    if origin is Union:
        return any(_is_instance_of_typing(value, a) for a in args)

    if origin in (list, List):
        if not isinstance(value, list):
            return False
        return True if not args else all(_is_instance_of_typing(v, args[0]) for v in value)

    if origin in (set, Set):
        if not isinstance(value, set):
            return False
        return True if not args else all(_is_instance_of_typing(v, args[0]) for v in value)

    if origin in (tuple, Tuple):
        if not isinstance(value, tuple):
            return False
        if not args:
            return True
        if len(args) == 2 and args[1] is Ellipsis:  # Tuple[T, ...]
            return all(_is_instance_of_typing(v, args[0]) for v in value)
        if len(args) != len(value):
            return False
        return all(_is_instance_of_typing(v, t) for v, t in zip(value, args))

    if origin in (dict, Dict):
        if not isinstance(value, dict):
            return False
        if not args:
            return True
        kt, vt = args
        return all(_is_instance_of_typing(k, kt) and _is_instance_of_typing(v, vt) for k, v in value.items())

    # Literal handling
    try:
        from typing import Literal  # py>=3.8
        if origin is Literal:  # type: ignore[attr-defined]
            return value in args
    except Exception:  # pragma: no cover - compatibility
        pass

    return True  # default permissive for unknown constructs


def validate_type(value: Any, expected_type: Any, *, allow_none: bool = False, path: Optional[str] = None) -> Any:
    """Validate value against expected_type; raise TypeValidationError on failure.

    Returns the value unchanged on success.
    """
    if value is None:
        if allow_none or (get_origin(expected_type) is Union and type(None) in get_args(expected_type)):
            return value
        raise TypeValidationError("value is None", path=path, code="type_error")

    if not _is_instance_of_typing(value, expected_type):
        exp = getattr(expected_type, "__name__", str(expected_type))
        raise TypeValidationError(f"expected {exp}, got {type(value).__name__}", path=path, code="type_error")
    return value


# --------------------
# Schema validation
# --------------------
class _Missing:
    pass


_MISSING = _Missing()


@dataclass
class FieldSpec:
    type_: Any
    required: bool = True
    default: Any = _MISSING
    allow_none: bool = False
    validators: List[Callable[[Any], Any]] = field(default_factory=list)
    sanitizer: Optional[Callable[[Any], Any]] = None
    description: Optional[str] = None

    def has_default(self) -> bool:
        return self.default is not _MISSING


def _compose_path(base: Optional[str], key: Any) -> str:
    if base in (None, ""):
        return str(key)
    if isinstance(key, int):
        return f"{base}[{key}]"
    return f"{base}.{key}"


def validate_schema(
    data: Mapping[str, Any],
    schema: Mapping[str, FieldSpec],
    *,
    allow_extra: bool = False,
    drop_extra: bool = False,
    path: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate and sanitize a mapping against a schema.

    - Applies per-field sanitizers before validators
    - Enforces required fields and types
    - Supports defaults when values are missing
    - Optionally allows or drops extra fields

    Returns a new dict with sanitized data, or raises AggregateValidationError.
    """
    errors: List[ValidationError] = []
    result: Dict[str, Any] = {}

    # Validate schema input type early
    if not isinstance(data, Mapping):
        raise TypeValidationError("data must be a mapping", path=path, code="type_error")

    for key, spec in schema.items():
        kpath = _compose_path(path, key)
        present = key in data
        value = data.get(key, _MISSING)

        if not present or value is _MISSING or value is None:
            if not present and spec.has_default():
                result[key] = spec.default if spec.default is not _MISSING else None
                continue
            if not present and not spec.required:
                continue
            if value is None and spec.allow_none:
                result[key] = None
                continue
            err_code = "missing_field" if not present else "null_not_allowed"
            errors.append(ValidationError("required field missing or None", path=kpath, code=err_code))
            continue

        # Sanitization
        try:
            v = spec.sanitizer(value) if spec.sanitizer else value
        except ValidationError as e:
            e.path = kpath if not e.path else f"{kpath}.{e.path}"
            errors.append(e)
            continue
        except Exception as exc:
            errors.append(ValidationError(str(exc), path=kpath, code="sanitization_error", cause=exc))
            continue

        # Type check
        try:
            validate_type(v, spec.type_, allow_none=spec.allow_none, path=kpath)
        except ValidationError as e:
            errors.append(e)
            continue

        # Custom validators
        for validator in spec.validators:
            try:
                out = validator(v)
                # Allow validators to transform the value if they return non-None
                if out is not None:
                    v = out
            except ValidationError as e:
                if not e.path:
                    e.path = kpath
                errors.append(e)
            except AssertionError as e:
                errors.append(ValidationError(str(e) or "assertion failed", path=kpath, code="assertion_failed"))
            except Exception as exc:
                errors.append(ValidationError(str(exc), path=kpath, code="value_error", cause=exc))

        result[key] = v

    if not allow_extra:
        # Identify extras
        extras = [k for k in data.keys() if k not in schema]
        if extras and not drop_extra:
            for k in extras:
                errors.append(ValidationError("unexpected field", path=_compose_path(path, k), code="unexpected_field"))
        # If drop_extra=True, ignore silently
    else:
        # Copy over extras as-is
        for k, v in data.items():
            if k not in schema:
                result[k] = v

    if errors:
        raise AggregateValidationError(errors, path=path)

    return result


# --------------------
# Built-in validators
# --------------------

def matches_regex(pattern: Union[str, re.Pattern[str]], *, flags: int = 0, message: Optional[str] = None) -> Callable[[str], None]:
    compiled = re.compile(pattern, flags) if isinstance(pattern, str) else pattern

    def _validator(value: str) -> None:
        if not isinstance(value, str):
            raise TypeValidationError("expected string for regex validation", code="type_error")
        if not compiled.search(value):
            raise ValidationError(message or f"value does not match pattern: {compiled.pattern}", code="regex_mismatch")

    return _validator


def in_range(*, min: Optional[float] = None, max: Optional[float] = None, inclusive: bool = True) -> Callable[[Union[int, float]], None]:
    def _validator(value: Union[int, float]) -> None:
        if not isinstance(value, (int, float)):
            raise TypeValidationError("expected number", code="type_error")
        if min is not None:
            if (value < min) or (not inclusive and value == min):
                raise ValidationError(f"value {value} is below minimum {min}", code="range_error")
        if max is not None:
            if (value > max) or (not inclusive and value == max):
                raise ValidationError(f"value {value} is above maximum {max}", code="range_error")

    return _validator


def length_between(*, min: Optional[int] = None, max: Optional[int] = None) -> Callable[[Sequence[Any]], None]:
    def _validator(value: Sequence[Any]) -> None:
        try:
            n = len(value)
        except Exception as exc:  # pragma: no cover - defensive
            raise TypeValidationError("value has no length", code="type_error", cause=exc)
        if min is not None and n < min:
            raise ValidationError(f"length {n} < min {min}", code="length_error")
        if max is not None and n > max:
            raise ValidationError(f"length {n} > max {max}", code="length_error")

    return _validator


def one_of(options: Iterable[Any]) -> Callable[[Any], None]:
    opts = set(options)

    def _validator(value: Any) -> None:
        if value not in opts:
            raise ValidationError(f"value must be one of {sorted(opts)!r}", code="one_of")

    return _validator


def non_empty() -> Callable[[Any], None]:
    def _validator(value: Any) -> None:
        if value is None:
            raise ValidationError("value is None", code="null")
        try:
            if len(value) == 0:  # type: ignore[arg-type]
                raise ValidationError("value is empty", code="empty")
        except TypeError:
            # Not a sized type; fallback to truthiness
            if not value:
                raise ValidationError("value is falsy", code="empty")

    return _validator


# --------------------
# Decorator for function argument validation
# --------------------
import inspect
from functools import wraps


def validate_args(
    *,
    param_types: Optional[Mapping[str, Any]] = None,
    param_validators: Optional[Mapping[str, Iterable[Callable[[Any], Any]]]] = None,
    param_sanitizers: Optional[Mapping[str, Callable[[Any], Any]]] = None,
):
    """Decorator to validate/sanitize function arguments.

    Example:
    @validate_args(
        param_types={"age": int, "name": str},
        param_sanitizers={"name": lambda s: sanitize_string(s, max_length=50)},
        param_validators={"age": [in_range(min=0)]},
    )
    def create_user(age, name):
        ...
    """

    param_types = dict(param_types or {})
    param_validators = {k: list(v) for k, v in (param_validators or {}).items()}
    param_sanitizers = dict(param_sanitizers or {})

    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        sig = inspect.signature(func)

        @wraps(func)
        def _wrapper(*args: Any, **kwargs: Any) -> Any:
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()

            # Sanitize then type-check then validate per param
            for name, value in list(bound.arguments.items()):
                ppath = name
                # Sanitize
                if name in param_sanitizers:
                    try:
                        value = param_sanitizers[name](value)
                    except ValidationError as e:
                        e.path = ppath if not e.path else f"{ppath}.{e.path}"
                        raise

                # Type check from explicit mapping if provided, else from annotations
                expected: Any = param_types.get(name, sig.parameters[name].annotation)
                if expected is not inspect._empty:  # type: ignore[attr-defined]
                    validate_type(value, expected, path=ppath)

                # Custom validators
                for validator in param_validators.get(name, []):
                    out = validator(value)
                    if out is not None:
                        value = out

                bound.arguments[name] = value

            return func(*bound.args, **bound.kwargs)

        return _wrapper

    return _decorator
