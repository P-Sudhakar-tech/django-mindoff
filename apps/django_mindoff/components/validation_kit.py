from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, Literal
from .helper_kit import mo_helper_kit


# ----------------
# Classes
# ----------------
class MindoffValidationError(Exception):
    def __init__(
        self,
        *,
        message: str = "Validation Failed",
        code: str = "VALIDATION_ERR",
        category: str = "danger",
        data: Optional[Dict[str, Any]] = None,
    ):
        if data is not None and not isinstance(data, (dict, list)):
            raise TypeError(f"'data' must be dict or list, got {type(data).__name__}")
        self.message = message
        self.code = code
        self.category = category
        self.data = data or {}
        super().__init__(message)


class ValidationError(Exception):
    """Fallback exception for validation failures."""


class MindoffValidator:
    def __init__(self) -> None:
        self._errors: List[_ErrorItem] = []

    # Equality & Comparison
    def ensure_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            if (
                hasattr(left, "__iter__")
                and hasattr(right, "__iter__")
                and not isinstance(left, (str, bytes, dict))
                and not isinstance(right, (str, bytes, dict))
            ):
                ok = list(left) == list(right)
            else:
                ok = left == right
            exc = ValueError
            default_message = f"Expected equal: {left!r} vs {right!r}"
        except Exception:
            ok = False
            exc = TypeError
            default_message = f"Comparison failed: {left!r} vs {right!r}"

        message = msg or default_message
        return self._record_or_raise(
            ok=ok,
            fn="ensure_equal",
            exc_type=exc,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_not_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        ok = left != right
        message = msg or f"Expected {left!r} != {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_equal",
            exc_type=ValueError,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_same(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        ok = left is right
        message = msg or f"Expected {left!r} is {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_is",
            exc_type=ValueError,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_not_same(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        ok = left is not right
        message = msg or f"Expected {left!r} is not {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_is",
            exc_type=ValueError,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_greater(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = left > right
            exc = ValueError
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Expected {left!r} > {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_greater",
            exc_type=exc,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_greater_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = left >= right
            exc = ValueError
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Expected {left!r} >= {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_greater_equal",
            exc_type=exc,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_lesser(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = left < right
            exc = ValueError
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Expected {left!r} < {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_lesser",
            exc_type=exc,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_lesser_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = left <= right
            exc = ValueError
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Expected {left!r} <= {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_lesser_equal",
            exc_type=exc,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_in_range(
        self,
        value: float,
        min_value: float,
        max_value: float,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = min_value <= value <= max_value
            exc = ValueError
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Expected {value!r} in range [{min_value}, {max_value}]"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_in_range",
            exc_type=exc,
            message=message,
            context={"value": value, "min_value": min_value, "max_value": max_value},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_not_in_range(
        self,
        value: float,
        min_value: float,
        max_value: float,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = not (min_value <= value <= max_value)
            exc = ValueError
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Expected {value!r} not in range [{min_value}, {max_value}]"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_in_range",
            exc_type=exc,
            message=message,
            context={"value": value, "min_value": min_value, "max_value": max_value},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_almost_equal(
        self,
        left: float,
        right: float,
        tol: float = 1e-6,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = math.isclose(left, right, abs_tol=tol)
            exc = ValueError
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Expected {left!r} ≈ {right!r} (tol={tol})"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_almost_equal",
            exc_type=exc,
            message=message,
            context={"left": left, "right": right, "tol": tol},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_not_almost_equal(
        self,
        left: float,
        right: float,
        tol: float = 1e-6,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = not math.isclose(left, right, abs_tol=tol)
            exc = ValueError
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Expected {left!r} not ≈ {right!r} (tol={tol})"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_almost_equal",
            exc_type=exc,
            message=message,
            context={"left": left, "right": right, "tol": tol},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    # Truthiness

    def ensure_falsey(
        self,
        value: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        ok = not bool(value)
        message = msg or f"Condition failed: expected truthy, got {value!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_falsey",
            exc_type=ValueError,
            message=message,
            context={"condition": value},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_truthy(
        self,
        value: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        ok = bool(value)
        message = msg or f"Condition failed: expected falsy, got {value!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_truthy",
            exc_type=ValueError,
            message=message,
            context={"condition": value},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    # Types & Classes

    def ensure_type(
        self,
        value: Any,
        typ: type,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        ok = isinstance(value, typ)
        message = (
            msg
            or f"Expected type {getattr(typ, '__name__', typ)!r}, got {type(value).__name__!r}"
        )
        return self._record_or_raise(
            ok=ok,
            fn="ensure_type",
            exc_type=TypeError,
            message=message,
            context={"value": value, "typ": getattr(typ, "__name__", str(typ))},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_not_type(
        self,
        value: Any,
        typ: type,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        ok = not isinstance(value, typ)
        message = msg or f"Expected not type {getattr(typ, '__name__', typ)!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_type",
            exc_type=TypeError,
            message=message,
            context={"value": value, "typ": getattr(typ, "__name__", str(typ))},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_subclass(
        self,
        cls: type,
        parent: type,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = issubclass(cls, parent)
            exc = TypeError
        except Exception:
            ok = False
            exc = TypeError
        message = (
            msg
            or f"{getattr(cls, '__name__', cls)!r} is not subclass of {getattr(parent, '__name__', parent)!r}"
        )
        return self._record_or_raise(
            ok=ok,
            fn="ensure_subclass",
            exc_type=exc,
            message=message,
            context={
                "cls": getattr(cls, "__name__", str(cls)),
                "parent": getattr(parent, "__name__", str(parent)),
            },
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_not_subclass(
        self,
        cls: type,
        parent: type,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            ok = not issubclass(cls, parent)
            exc = TypeError
        except Exception:
            ok = False
            exc = TypeError
        message = (
            msg
            or f"{getattr(cls, '__name__', cls)!r} is a subclass of {getattr(parent, '__name__', parent)!r}"
        )
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_subclass",
            exc_type=exc,
            message=message,
            context={
                "cls": getattr(cls, "__name__", str(cls)),
                "parent": getattr(parent, "__name__", str(parent)),
            },
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    # Containers & Collections

    def ensure_in(
        self,
        value: Any,
        container: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        # Autodetect: dict -> KeyError, others -> LookupError
        exc = KeyError if isinstance(container, dict) else LookupError
        try:
            ok = value in container
        except Exception:
            ok = False
            exc = TypeError
            msg = msg or "Container is not iterable or does not support membership test"
        message = msg or f"Expected {value!r} in {container!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_in",
            exc_type=exc,
            message=message,
            context={"value": value, "container": container},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_not_in(
        self,
        value: Any,
        container: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        exc = KeyError if isinstance(container, dict) else LookupError
        try:
            ok = value not in container
        except Exception:
            ok = False
            exc = TypeError
            msg = msg or "Container is not iterable or does not support membership test"
        message = msg or f"Expected {value!r} not in {container!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_in",
            exc_type=exc,
            message=message,
            context={"value": value, "container": container},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_count_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            from collections import Counter

            ok = Counter(left) == Counter(right)
            exc = ValueError
        except TypeError:
            ok = False
            exc = TypeError  # unhashable elements
            msg = msg or "Elements must be hashable for ensure_count_equal"
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Counts not equal: {left!r} vs {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_count_equal",
            exc_type=exc,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_count_not_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        try:
            from collections import Counter

            ok = Counter(left) != Counter(right)
            exc = ValueError
        except TypeError:
            ok = False
            exc = TypeError  # unhashable elements
            msg = msg or "Elements must be hashable for ensure_count_not_equal"
        except Exception:
            ok = False
            exc = TypeError
        message = msg or f"Counts unexpectedly equal: {left!r} vs {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_count_not_equal",
            exc_type=exc,
            message=message,
            context={"left": left, "right": right},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    # Numeric / Regex / File

    def ensure_finite(
        self,
        value: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        if not isinstance(value, (int, float)):
            return self._record_or_raise(
                ok=False,
                fn="ensure_finite",
                exc_type=TypeError,
                message=msg or f"Expected number, got {type(value).__name__}",
                context={"value": value},
                is_exception=is_exception,
                is_aggregate=is_aggregate,
                code=code,
            )
        ok = math.isfinite(value)
        message = msg or f"Expected finite number, got {value!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_finite",
            exc_type=ValueError,
            message=message,
            context={"value": value},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_regex(
        self,
        value: Any,
        pattern: str,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        if not isinstance(value, str):
            return self._record_or_raise(
                ok=False,
                fn="ensure_regex",
                exc_type=TypeError,
                message=msg or f"Expected str to match, got {type(value).__name__}",
                context={"value": value, "pattern": pattern},
                is_exception=is_exception,
                is_aggregate=is_aggregate,
                code=code,
            )
        ok = bool(re.fullmatch(pattern, value))
        message = msg or f"String {value!r} does not match {pattern!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_regex",
            exc_type=ValueError,
            message=message,
            context={"value": value, "pattern": pattern},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_not_regex(
        self,
        value: Any,
        pattern: str,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        if not isinstance(value, str):
            return self._record_or_raise(
                ok=False,
                fn="ensure_not_regex",
                exc_type=TypeError,
                message=msg or f"Expected str to test, got {type(value).__name__}",
                context={"value": value, "pattern": pattern},
                is_exception=is_exception,
                is_aggregate=is_aggregate,
                code=code,
            )
        ok = not bool(re.fullmatch(pattern, value))
        message = msg or f"String {value!r} matches {pattern!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_regex",
            exc_type=ValueError,
            message=message,
            context={"value": value, "pattern": pattern},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_path(
        self,
        path: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        p = Path(path)
        ok = p.exists()
        message = msg or f"Path exists (but should not): {p}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_path",
            exc_type=FileNotFoundError,
            message=message,
            context={"path": str(p)},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure_not_path(
        self,
        path: Any,
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        p = Path(path)
        ok = not p.exists()
        message = msg or f"Path does not exist: {p}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_path",
            exc_type=FileExistsError,
            message=message,
            context={"path": str(p)},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def ensure(
        self,
        check: Union[bool, Callable[[], bool]],
        *,
        msg: Optional[str] = None,
        code: str = "VALIDATION_ERR",
        is_exception: bool = False,
        is_aggregate: bool = False,
        exc_type: type[Exception] = ValidationError,
    ):
        try:
            ok = bool(check() if callable(check) else check)
        except Exception as e:
            ok = False
            msg = msg or f"ensure check error: {e}"
        message = msg or "ensure check failed"
        return self._record_or_raise(
            ok=ok,
            fn="ensure",
            exc_type=exc_type,
            message=message,
            is_exception=is_exception,
            is_aggregate=is_aggregate,
            code=code,
        )

    def finalize(
        self,
        *,
        code: str = "VALIDATION_ERR",
        message: str = "Aggregated Validation Failed",
        return_mode: Literal["list", "error", "exception"] = "error",
    ):
        try:
            has_errors = bool(self._errors)

            if not has_errors:
                return {
                    "list": [],
                    "error": None,
                    "exception": None,
                }[return_mode]

            if return_mode == "exception":
                raise ValidationError(
                    "\n".join(
                        f"[{e.type}] [{e.code}] {e.message} {e.traceback}"
                        for e in self._errors
                    )
                )

            error_data = [
                {
                    "type": e.type,
                    "code": e.code,
                    "message": e.message,
                    "context": e.context,
                }
                for e in self._errors
            ]

            if return_mode == "list":
                return error_data

            raise MindoffValidationError(
                message=message,
                code=code,
                data=error_data,
            )
        finally:
            self.reset()

    def reset(self):
        self._errors.clear()

    def _record_or_raise(
        self,
        *,
        ok: bool,
        fn: str,
        exc_type: type[BaseException],
        message: str,
        context: Optional[Dict[str, Any]] = None,
        is_exception: bool = False,
        is_aggregate: bool = False,
        code: str = "VALIDATION_ERR",
    ):
        context = context or {}
        if ok:
            return True

        tb_text = mo_helper_kit.get_exact_traceback(skip=3)
        item = _ErrorItem(
            fn=fn,
            type=exc_type.__name__,
            message=message,
            context=context,
            traceback=tb_text,
            code=code,
        )

        if is_aggregate:
            self._errors.append(item)
            return None

        if is_exception:
            exc = exc_type(message)
            setattr(exc, "code", code)
            raise exc

        raise MindoffValidationError(
            code=code,
            message=message,
            data={
                "type": item.type,
                "message": item.message,
                "context": item.context,
            },
        )


# ----------------
# Helper Classes
# ----------------
@dataclass
class _ErrorItem:
    fn: str
    type: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: str = ""
    code: str = "VALIDATION_ERR"


# ----------------
# Entry Point
# ----------------
mo_validation_kit = MindoffValidator()
