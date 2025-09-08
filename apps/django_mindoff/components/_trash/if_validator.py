"""
Validate_errors.py
Minimalist validation raiser with semantic names, native exceptions,
and 4 modes: raise, response, agg_raise, agg_response.
"""

from __future__ import annotations
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class ValidationError(Exception):
    """Fallback exception for validation failures."""


class MindoffValidator:
    """
    mode:
      - 'raise'         -> raise immediately (Single Exception)
      - 'response'      -> return _ValidationResponse immediately (Single Response)
      - 'agg_raise'     -> collect errors, raise once at finalize (Aggregated Exception)
      - 'agg_response'  -> collect errors, return response at finalize (Aggregated Response)
    """

    def __init__(self, mode: str = "raise") -> None:
        if mode not in {"raise", "response", "agg_raise", "agg_response"}:
            raise ValueError(
                "mode must be one of: raise, response, agg_raise, agg_response"
            )
        self.mode = mode
        self._errors: List[_ErrorItem] = []

    # Equality & Comparison

    def ensure_equal(self, left: Any, right: Any, *, msg: Optional[str] = None):
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
        )

    def ensure_not_equal(self, left: Any, right: Any, *, msg: Optional[str] = None):
        ok = left != right
        message = msg or f"Expected {left!r} != {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_equal",
            exc_type=ValueError,
            message=message,
            context={"left": left, "right": right},
        )

    def ensure_same(self, left: Any, right: Any, *, msg: Optional[str] = None):
        ok = left is right
        message = msg or f"Expected {left!r} is {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_is",
            exc_type=ValueError,
            message=message,
            context={"left": left, "right": right},
        )

    def ensure_not_same(self, left: Any, right: Any, *, msg: Optional[str] = None):
        ok = left is not right
        message = msg or f"Expected {left!r} is not {right!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_is",
            exc_type=ValueError,
            message=message,
            context={"left": left, "right": right},
        )

    def ensure_greater(self, left: Any, right: Any, *, msg: Optional[str] = None):
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
        )

    def ensure_greater_equal(self, left: Any, right: Any, *, msg: Optional[str] = None):
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
        )

    def ensure_lesser(self, left: Any, right: Any, *, msg: Optional[str] = None):
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
        )

    def ensure_lesser_equal(self, left: Any, right: Any, *, msg: Optional[str] = None):
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
        )

    def ensure_in_range(
        self,
        value: float,
        min_value: float,
        max_value: float,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_not_in_range(
        self,
        value: float,
        min_value: float,
        max_value: float,
        *,
        msg: Optional[str] = None,
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
        )

    def ensure_almost_equal(
        self, left: float, right: float, tol: float = 1e-6, *, msg: Optional[str] = None
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
        )

    def ensure_not_almost_equal(
        self, left: float, right: float, tol: float = 1e-6, *, msg: Optional[str] = None
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
        )

    # Truthiness

    def ensure_falsey(self, value: Any, *, msg: Optional[str] = None):
        ok = not bool(value)
        message = msg or f"Condition failed: expected truthy, got {value!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_truthy",
            exc_type=ValueError,
            message=message,
            context={"condition": value},
        )

    def ensure_truthy(self, value: Any, *, msg: Optional[str] = None):
        ok = bool(value)
        message = msg or f"Condition failed: expected falsy, got {value!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_falsy",
            exc_type=ValueError,
            message=message,
            context={"condition": value},
        )

    # Types & Classes

    def ensure_type(self, value: Any, typ: type, *, msg: Optional[str] = None):
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
        )

    def ensure_not_type(self, value: Any, typ: type, *, msg: Optional[str] = None):
        ok = not isinstance(value, typ)
        message = msg or f"Expected not type {getattr(typ, '__name__', typ)!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_type",
            exc_type=TypeError,
            message=message,
            context={"value": value, "typ": getattr(typ, "__name__", str(typ))},
        )

    def ensure_subclass(self, cls: type, parent: type, *, msg: Optional[str] = None):
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
        )

    def ensure_not_subclass(
        self,
        cls: type,
        parent: type,
        *,
        msg: Optional[str] = None,
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
        )

    # Containers & Collections

    def ensure_in(self, value: Any, container: Any, *, msg: Optional[str] = None):
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
        )

    def ensure_not_in(self, value: Any, container: Any, *, msg: Optional[str] = None):
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
        )

    def ensure_count_equal(self, left: Any, right: Any, *, msg: Optional[str] = None):
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
        )

    def ensure_count_not_equal(
        self, left: Any, right: Any, *, msg: Optional[str] = None
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
        )

    # Numeric / Regex / File

    def ensure_finite(self, value: Any, *, msg: Optional[str] = None):
        if not isinstance(value, (int, float)):
            return self._record_or_raise(
                ok=False,
                fn="ensure_finite",
                exc_type=TypeError,
                message=msg or f"Expected number, got {type(value).__name__}",
                context={"value": value},
            )
        ok = math.isfinite(value)
        message = msg or f"Expected finite number, got {value!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_finite",
            exc_type=ValueError,
            message=message,
            context={"value": value},
        )

    def ensure_regex(self, value: Any, pattern: str, *, msg: Optional[str] = None):
        if not isinstance(value, str):
            return self._record_or_raise(
                ok=False,
                fn="ensure_regex",
                exc_type=TypeError,
                message=msg or f"Expected str to match, got {type(value).__name__}",
                context={"value": value, "pattern": pattern},
            )
        ok = bool(re.fullmatch(pattern, value))
        message = msg or f"String {value!r} does not match {pattern!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_regex",
            exc_type=ValueError,
            message=message,
            context={"value": value, "pattern": pattern},
        )

    def ensure_not_regex(self, value: Any, pattern: str, *, msg: Optional[str] = None):
        if not isinstance(value, str):
            return self._record_or_raise(
                ok=False,
                fn="ensure_not_regex",
                exc_type=TypeError,
                message=msg or f"Expected str to test, got {type(value).__name__}",
                context={"value": value, "pattern": pattern},
            )
        ok = not bool(re.fullmatch(pattern, value))
        message = msg or f"String {value!r} matches {pattern!r}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_regex",
            exc_type=ValueError,
            message=message,
            context={"value": value, "pattern": pattern},
        )

    def ensure_exists(self, path: Any, *, msg: Optional[str] = None):
        p = Path(path)
        ok = p.exists()
        message = msg or f"Path exists (but should not): {p}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_exists",
            exc_type=FileNotFoundError,
            message=message,
            context={"path": str(p)},
        )

    def ensure_not_exists(self, path: Any, *, msg: Optional[str] = None):
        p = Path(path)
        ok = not p.exists()
        message = msg or f"Path does not exist: {p}"
        return self._record_or_raise(
            ok=ok,
            fn="ensure_not_exists",
            exc_type=FileExistsError,
            message=message,
            context={"path": str(p)},
        )

    # Custom

    def custom(
        self,
        check: Union[bool, Callable[[], bool]],
        *,
        msg: Optional[str] = None,
        exc_type: type[Exception] = ValidationError,
    ):
        try:
            ok = bool(check() if callable(check) else check)
        except Exception as e:
            ok = False
            msg = msg or f"Custom check error: {e}"
        message = msg or "Custom check failed"
        return self._record_or_raise(
            ok=ok, fn="custom", exc_type=exc_type, message=message
        )

    def finalize(self) -> Optional[_ValidationResponse]:
        """
        Finalize aggregated modes.
        - agg_raise: raise one combined exception (same type if all equal, else ValidationError).
        - agg_response: return _ValidationResponse with all errors.
        - other modes: return None.
        """
        if self.mode == "agg_raise":
            if self._errors:
                types = {e.type for e in self._errors}
                # Compose combined message
                combined = "\n".join(f"[{e.fn}] {e.message}" for e in self._errors)
                if len(types) == 1:
                    # All errors share the same native type; raise that.
                    etype = getattr(__builtins__, next(iter(types)), ValidationError)
                    raise etype(combined)
                # Mixed types → fall back to ValidationError
                raise ValidationError(combined)
            return None

        if self.mode == "agg_response":
            r = _ValidationResponse(success=(len(self._errors) == 0))
            for e in self._errors:
                r.add_error(e)
            return r

        return None

    # ---- internals ----
    def _record_or_raise(
        self,
        *,
        ok: bool,
        fn: str,
        exc_type: type[BaseException],
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Handle the failure according to the selected mode.
        - In 'raise': raise the given exc_type immediately.
        - In 'response': return a _ValidationResponse with a single error (or success).
        - In aggregated modes: store the error and return False (or True if ok).
        """
        context = context or {}
        if ok:
            if self.mode == "response":
                return _ValidationResponse(success=True)
            return True

        item = _ErrorItem(
            fn=fn, type=exc_type.__name__, message=message, context=context
        )

        if self.mode == "raise":
            raise exc_type(message)

        if self.mode == "response":
            r = _ValidationResponse(success=False)
            r.add_error(item)
            return r

        # aggregated modes
        self._errors.append(item)
        return False


@dataclass
class _ErrorItem:
    fn: str
    type: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _ValidationResponse:
    success: bool = True
    errors: List[_ErrorItem] = field(default_factory=list)

    def add_error(self, item: _ErrorItem) -> None:
        self.success = False
        self.errors.append(item)

    def to_json(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "errors": [
                {
                    "fn": e.fn,
                    "type": e.type,
                    "message": e.message,
                    "context": e.context,
                }
                for e in self.errors
            ],
        }
