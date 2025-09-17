# ----------------------------------
# validation_kit.py
# ----------------------------------
"""
USAGE:
mo_validation_kit.ensure_equal(a, b, msg="optional")
mo_validation_kit.ensure_equal(a, b, is_exception=False)
mo_validation_kit.ensure_equal(a, b, is_aggregate=True)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .helper_kit import mo_helper_kit


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
        is_exception: bool = True,
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
        )

    def ensure_not_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_same(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_not_same(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_greater(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_greater_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_lesser(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_lesser_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_in_range(
        self,
        value: float,
        min_value: float,
        max_value: float,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_not_in_range(
        self,
        value: float,
        min_value: float,
        max_value: float,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_almost_equal(
        self,
        left: float,
        right: float,
        tol: float = 1e-6,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_not_almost_equal(
        self,
        left: float,
        right: float,
        tol: float = 1e-6,
        *,
        msg: Optional[str] = None,
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
        )

    # Truthiness

    def ensure_falsey(
        self,
        value: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_truthy(
        self,
        value: Any,
        *,
        msg: Optional[str] = None,
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
        )

    # Types & Classes

    def ensure_type(
        self,
        value: Any,
        typ: type,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_not_type(
        self,
        value: Any,
        typ: type,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_subclass(
        self,
        cls: type,
        parent: type,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_not_subclass(
        self,
        cls: type,
        parent: type,
        *,
        msg: Optional[str] = None,
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
        )

    # Containers & Collections

    def ensure_in(
        self,
        value: Any,
        container: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_not_in(
        self,
        value: Any,
        container: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_count_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_count_not_equal(
        self,
        left: Any,
        right: Any,
        *,
        msg: Optional[str] = None,
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
        )

    # Numeric / Regex / File

    def ensure_finite(
        self,
        value: Any,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_regex(
        self,
        value: Any,
        pattern: str,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_not_regex(
        self,
        value: Any,
        pattern: str,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_exists(
        self,
        path: Any,
        *,
        msg: Optional[str] = None,
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        p = Path(path)
        ok = p.exists()
        message = msg or f"Path exists (but should not): {p}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_exists",
            exc_type=FileNotFoundError,
            message=message,
            context={"path": str(p)},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
        )

    def ensure_not_exists(
        self,
        path: Any,
        *,
        msg: Optional[str] = None,
        is_exception: bool = False,
        is_aggregate: bool = False,
    ):
        p = Path(path)
        ok = not p.exists()
        message = msg or f"Path does not exist: {p}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_exists",
            exc_type=FileExistsError,
            message=message,
            context={"path": str(p)},
            is_exception=is_exception,
            is_aggregate=is_aggregate,
        )

    # ensure

    def ensure(
        self,
        check: Union[bool, Callable[[], bool]],
        *,
        msg: Optional[str] = None,
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
        )

    def finalize(self, *, is_exception: bool = True):
        from .response_kit import mo_response_kit

        try:
            if not self._errors:
                return True if is_exception else None

            if is_exception:
                raise ValidationError(
                    "\n".join(
                        f"[{e.type}] {e.message} {e.traceback}" for e in self._errors
                    )
                )
            response = {
                "data": [
                    {"type": e.type, "message": e.message, "context": e.context}
                    for e in self._errors
                ]
            }

            return mo_response_kit.json_response(
                "VALIDATION_ERR", category="danger", **response
            )
        finally:
            self.reset()

    def reset(self):
        self._errors.clear()

    # ---- internals ----
    def _record_or_raise(
        self,
        *,
        ok: bool,
        fn: str,
        exc_type: type[BaseException],
        message: str,
        context: Optional[Dict[str, Any]] = None,
        is_exception: bool = True,
        is_aggregate: bool = False,
    ):
        from .response_kit import mo_response_kit

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
        )

        if is_aggregate:
            self._errors.append(item)
            return False if is_exception else None

        if is_exception:
            raise exc_type(message)

        response = {
            "data": [
                {
                    "type": item.type,
                    "message": item.message,
                    "context": item.context,
                }
            ]
        }
        return mo_response_kit.json_response(
            "VALIDATION_ERR", category="danger", **response
        )


@dataclass
class _ErrorItem:
    fn: str
    type: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    traceback: str = ""


mo_validation_kit = MindoffValidator()
