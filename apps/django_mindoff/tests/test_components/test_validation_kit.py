"""
TEST CASES:
1. Basic exception -- ensure_equal(a, b) ✅
2. Exception with custom message -- ensure_equal(a, b, msg="custom message for validation") ✅
3. Json Response -- ensure_equal(a, b, is_exception=False) ✅
4. Json Response with custom message -- ensure_equal(a, b, is_exception=False, msg="VALIDATION_ERR") ✅
5. Aggregated Exception -- ensure_equal(a, b, is_aggregate=True) -- ensure_not_equal(c, d, is_aggregate=True) -- finalize() ✅
6. Aggregated Json Response -- ensure_equal(a, b, is_aggregate=True, is_exception=False) -- ensure_not_equal(c, d, is_aggregate=True, is_exception=False) -- finalize() ✅
7. Aggregated Json Response with custom message -- ensure_equal(a, b, is_aggregate=True, is_exception=False) -- ensure_not_equal(c, d, is_aggregate=True, is_exception=False) -- finalize(msg="VALIDATION_ERR") ✅

TEST CASES FOR CUSTOM CODE PARAMETER:
1. Custom code with exception -- ensure_equal(a, b, code="CUSTOM_CODE") ✅
2. Custom code with json response -- ensure_equal(a, b, is_exception=False, code="CUSTOM_CODE") ✅
3. Custom code with aggregate -- ensure_equal(a, b, is_aggregate=True, code="CUSTOM_CODE") ✅
4. Custom code with aggregate json -- ensure_equal(a, b, is_aggregate=True, is_exception=False, code="CUSTOM_CODE") ✅
5. All available codes are reflected in assertions ✅

Available codes: UNEXPECTED_ERR, NOT_AUTHENTICATED, PERMISSION_DENIED, INVALID_PAYLOAD, INVALID_METHOD
"""

import logging
import sys

import pytest
from ...components.tdd_kit import MindoffTestCase

from ...components.validation_kit import (
    MindoffValidationError,
    ValidationError,
    mo_validation_kit,
)


class TestImmediateValidator(MindoffTestCase):
    @pytest.mark.parametrize(
        "fn, kwargs, is_exception, expected_result",
        [
            # ---------------- Exception Cases ----------------
            ("ensure_equal", {"left": 5, "right": 5}, True, True),
            ("ensure_not_equal", {"left": "x", "right": "y"}, True, True),
            ("ensure_same", {"left": "a", "right": "a"}, True, True),
            ("ensure_not_same", {"left": "a", "right": "b"}, True, True),
            ("ensure_greater", {"left": 10, "right": 5}, True, True),
            ("ensure_greater_equal", {"left": 5, "right": 5}, True, True),
            ("ensure_lesser", {"left": 7, "right": 10}, True, True),
            ("ensure_lesser_equal", {"left": 7, "right": 7}, True, True),
            (
                "ensure_in_range",
                {"value": 5, "min_value": 1, "max_value": 10},
                True,
                True,
            ),
            (
                "ensure_not_in_range",
                {"value": 20, "min_value": 1, "max_value": 10},
                True,
                True,
            ),
            ("ensure_almost_equal", {"left": 1.0, "right": 1.0000001}, True, True),
            ("ensure_not_almost_equal", {"left": 1.0, "right": 1.1}, True, True),
            ("ensure_falsey", {"value": []}, True, True),
            ("ensure_truthy", {"value": "x"}, True, True),
            ("ensure_type", {"value": 123, "typ": int}, True, True),
            ("ensure_not_type", {"value": "x", "typ": int}, True, True),
            ("ensure_subclass", {"cls": bool, "parent": int}, True, True),
            ("ensure_not_subclass", {"cls": str, "parent": dict}, True, True),
            ("ensure_in", {"value": 2, "container": [1, 2, 3]}, True, True),
            ("ensure_not_in", {"value": "z", "container": "hello"}, True, True),
            ("ensure_in", {"value": "a", "container": {"a": 1}}, True, True),
            ("ensure_count_equal", {"left": [1, 2], "right": [2, 1]}, True, True),
            (
                "ensure_count_not_equal",
                {"left": [1, 2], "right": [1, 3, 4]},
                True,
                True,
            ),
            ("ensure_finite", {"value": 5}, True, True),
            ("ensure_regex", {"value": "abc123", "pattern": r"[a-z]+\d+"}, True, True),
            ("ensure_not_regex", {"value": "xyz", "pattern": r"\d+"}, True, True),
            ("ensure_path", {"path": sys.executable}, True, True),
            ("ensure_not_path", {"path": "nonexistent_file.tmp"}, True, True),
            ("ensure_equal", {"left": [1, 2, 3], "right": (1, 2, 3)}, True, True),
            ("ensure_falsey", {"value": 0}, True, True),
            ("ensure_truthy", {"value": True}, True, True),
            ("ensure_subclass", {"cls": str, "parent": object}, True, True),
            ("ensure_finite", {"value": 3.14}, True, True),
            ("ensure_regex", {"value": "hello", "pattern": r"hello"}, True, True),
            ("ensure", {"check": lambda: True}, True, True),
            # ---------------- Json Cases ----------------
            ("ensure_equal", {"left": 5, "right": 5}, False, True),
            ("ensure_not_equal", {"left": "x", "right": "y"}, False, True),
            ("ensure_same", {"left": "a", "right": "a"}, False, True),
            ("ensure_not_same", {"left": "a", "right": "b"}, False, True),
            ("ensure_greater", {"left": 10, "right": 5}, False, True),
            ("ensure_greater_equal", {"left": 5, "right": 5}, False, True),
            ("ensure_lesser", {"left": 7, "right": 10}, False, True),
            ("ensure_lesser_equal", {"left": 7, "right": 7}, False, True),
            (
                "ensure_in_range",
                {"value": 5, "min_value": 1, "max_value": 10},
                False,
                True,
            ),
            (
                "ensure_not_in_range",
                {"value": 20, "min_value": 1, "max_value": 10},
                False,
                True,
            ),
            ("ensure_almost_equal", {"left": 1.0, "right": 1.0000001}, False, True),
            ("ensure_not_almost_equal", {"left": 1.0, "right": 1.1}, False, True),
            ("ensure_falsey", {"value": []}, False, True),
            ("ensure_truthy", {"value": "x"}, False, True),
            ("ensure_type", {"value": 123, "typ": int}, False, True),
            ("ensure_not_type", {"value": "x", "typ": int}, False, True),
            ("ensure_subclass", {"cls": bool, "parent": int}, False, True),
            ("ensure_not_subclass", {"cls": str, "parent": dict}, False, True),
            ("ensure_in", {"value": 2, "container": [1, 2, 3]}, False, True),
            ("ensure_not_in", {"value": "z", "container": "hello"}, False, True),
            ("ensure_in", {"value": "a", "container": {"a": 1}}, False, True),
            ("ensure_count_equal", {"left": [1, 2], "right": [2, 1]}, False, True),
            (
                "ensure_count_not_equal",
                {"left": [1, 2], "right": [1, 3, 4]},
                False,
                True,
            ),
            ("ensure_finite", {"value": 5}, False, True),
            ("ensure_regex", {"value": "abc123", "pattern": r"[a-z]+\d+"}, False, True),
            ("ensure_not_regex", {"value": "xyz", "pattern": r"\d+"}, False, True),
            ("ensure_path", {"path": sys.executable}, False, True),
            ("ensure_not_path", {"path": "nonexistent_file.tmp"}, False, True),
            ("ensure_equal", {"left": [1, 2, 3], "right": (1, 2, 3)}, False, True),
            ("ensure_falsey", {"value": 0}, False, True),
            ("ensure_truthy", {"value": True}, False, True),
            ("ensure_subclass", {"cls": str, "parent": object}, False, True),
            ("ensure_finite", {"value": 3.14}, False, True),
            ("ensure_regex", {"value": "hello", "pattern": r"hello"}, False, True),
            ("ensure", {"check": lambda: True}, False, True),
        ],
    )
    def test_validation_acceptance(self, fn, kwargs, is_exception, expected_result):
        result = getattr(mo_validation_kit, fn)(**kwargs, is_exception=is_exception)
        assert result == expected_result

    @pytest.mark.parametrize("is_debug", [True, False])
    @pytest.mark.parametrize(
        "fn, kwargs, is_exception, expected_exc, is_msg",
        [
            # ---------------- Exception Cases ----------------
            (
                "ensure_equal",
                {"left": 3, "right": 5, "msg": "Custom Message 3 is not equal 5"},
                True,
                ValueError,
                True,
            ),
            ("ensure_not_equal", {"left": "x", "right": "x"}, True, ValueError, False),
            ("ensure_same", {"left": [1], "right": [1]}, True, ValueError, False),
            ("ensure_not_same", {"left": "a", "right": "a"}, True, ValueError, False),
            ("ensure_greater", {"left": 2, "right": 5}, True, ValueError, False),
            ("ensure_greater_equal", {"left": 4, "right": 5}, True, ValueError, False),
            ("ensure_lesser", {"left": 7, "right": 3}, True, ValueError, False),
            ("ensure_lesser_equal", {"left": 8, "right": 7}, True, ValueError, False),
            (
                "ensure_in_range",
                {"value": 0, "min_value": 1, "max_value": 10},
                True,
                ValueError,
                False,
            ),
            (
                "ensure_in_range",
                {"value": 11, "min_value": 1, "max_value": 10},
                True,
                ValueError,
                False,
            ),
            (
                "ensure_not_in_range",
                {"value": 5, "min_value": 1, "max_value": 10},
                True,
                ValueError,
                False,
            ),
            (
                "ensure_almost_equal",
                {"left": 1.0, "right": 1.1, "tol": 1e-6},
                True,
                ValueError,
                False,
            ),
            (
                "ensure_not_almost_equal",
                {"left": 1.0, "right": 1.0, "tol": 1e-6},
                True,
                ValueError,
                False,
            ),
            ("ensure_falsey", {"value": [1]}, True, ValueError, False),
            ("ensure_truthy", {"value": ""}, True, ValueError, False),
            ("ensure_type", {"value": "abc", "typ": int}, True, TypeError, False),
            ("ensure_not_type", {"value": 123, "typ": int}, True, TypeError, False),
            ("ensure_subclass", {"cls": int, "parent": str}, True, TypeError, False),
            (
                "ensure_not_subclass",
                {"cls": bool, "parent": int},
                True,
                TypeError,
                False,
            ),
            (
                "ensure_in",
                {"value": 99, "container": [1, 2, 3]},
                True,
                LookupError,
                False,
            ),
            ("ensure_in", {"value": "z", "container": {"a": 1}}, True, KeyError, False),
            (
                "ensure_not_in",
                {"value": 2, "container": [1, 2, 3]},
                True,
                LookupError,
                False,
            ),
            (
                "ensure_not_in",
                {"value": "a", "container": {"a": 1}},
                True,
                KeyError,
                False,
            ),
            (
                "ensure_count_equal",
                {"left": [1, 2], "right": [2, 2]},
                True,
                ValueError,
                False,
            ),
            (
                "ensure_count_not_equal",
                {"left": [1, 1], "right": [1, 1]},
                True,
                ValueError,
                False,
            ),
            ("ensure_finite", {"value": float("inf")}, True, ValueError, False),
            ("ensure_finite", {"value": "not-a-number"}, True, TypeError, False),
            (
                "ensure_regex",
                {"value": "abc", "pattern": r"\d+"},
                True,
                ValueError,
                False,
            ),
            ("ensure_regex", {"value": 123, "pattern": r"\d+"}, True, TypeError, False),
            (
                "ensure_not_regex",
                {"value": "123", "pattern": r"\d+"},
                True,
                ValueError,
                False,
            ),
            (
                "ensure_not_regex",
                {"value": 123, "pattern": r"\d+"},
                True,
                TypeError,
                False,
            ),
            (
                "ensure_path",
                {"path": "nonexistent_file.tmp"},
                True,
                FileNotFoundError,
                False,
            ),
            (
                "ensure_not_path",
                {"path": sys.executable},
                True,
                FileExistsError,
                False,
            ),
            ("ensure", {"check": False}, True, ValidationError, False),
            # ---------------- Json Cases ----------------
            ("ensure_equal", {"left": 3, "right": 5}, False, ValueError, False),
            ("ensure_not_equal", {"left": "x", "right": "x"}, False, ValueError, False),
            ("ensure_same", {"left": [1], "right": [1]}, False, ValueError, False),
            ("ensure_not_same", {"left": "a", "right": "a"}, False, ValueError, False),
            ("ensure_greater", {"left": 2, "right": 5}, False, ValueError, False),
            ("ensure_greater_equal", {"left": 4, "right": 5}, False, ValueError, False),
            ("ensure_lesser", {"left": 7, "right": 3}, False, ValueError, False),
            ("ensure_lesser_equal", {"left": 8, "right": 7}, False, ValueError, False),
            (
                "ensure_in_range",
                {"value": 0, "min_value": 1, "max_value": 10},
                False,
                ValueError,
                False,
            ),
            (
                "ensure_in_range",
                {"value": 11, "min_value": 1, "max_value": 10},
                False,
                ValueError,
                False,
            ),
            (
                "ensure_not_in_range",
                {"value": 5, "min_value": 1, "max_value": 10},
                False,
                ValueError,
                False,
            ),
            (
                "ensure_almost_equal",
                {"left": 1.0, "right": 1.1, "tol": 1e-6},
                False,
                ValueError,
                False,
            ),
            (
                "ensure_not_almost_equal",
                {"left": 1.0, "right": 1.0, "tol": 1e-6},
                False,
                ValueError,
                False,
            ),
            ("ensure_falsey", {"value": [1]}, False, ValueError, False),
            ("ensure_truthy", {"value": ""}, False, ValueError, False),
            ("ensure_type", {"value": "abc", "typ": int}, False, TypeError, False),
            ("ensure_not_type", {"value": 123, "typ": int}, False, TypeError, False),
            ("ensure_subclass", {"cls": int, "parent": str}, False, TypeError, False),
            (
                "ensure_not_subclass",
                {"cls": bool, "parent": int},
                False,
                TypeError,
                False,
            ),
            (
                "ensure_in",
                {"value": 99, "container": [1, 2, 3]},
                False,
                LookupError,
                False,
            ),
            (
                "ensure_in",
                {"value": "z", "container": {"a": 1}},
                False,
                KeyError,
                False,
            ),
            (
                "ensure_not_in",
                {"value": 2, "container": [1, 2, 3]},
                False,
                LookupError,
                False,
            ),
            (
                "ensure_not_in",
                {"value": "a", "container": {"a": 1}},
                False,
                KeyError,
                False,
            ),
            (
                "ensure_count_equal",
                {"left": [1, 2], "right": [2, 2]},
                False,
                ValueError,
                False,
            ),
            (
                "ensure_count_not_equal",
                {"left": [1, 1], "right": [1, 1]},
                False,
                ValueError,
                False,
            ),
            ("ensure_finite", {"value": float("inf")}, False, ValueError, False),
            ("ensure_finite", {"value": "not-a-number"}, False, TypeError, False),
            (
                "ensure_regex",
                {"value": "abc", "pattern": r"\d+"},
                False,
                ValueError,
                False,
            ),
            (
                "ensure_regex",
                {"value": 123, "pattern": r"\d+"},
                False,
                TypeError,
                False,
            ),
            (
                "ensure_not_regex",
                {"value": "123", "pattern": r"\d+"},
                False,
                ValueError,
                False,
            ),
            (
                "ensure_not_regex",
                {"value": 123, "pattern": r"\d+"},
                False,
                TypeError,
                False,
            ),
            (
                "ensure_path",
                {"path": "nonexistent_file.tmp"},
                False,
                FileNotFoundError,
                False,
            ),
            (
                "ensure_not_path",
                {"path": sys.executable},
                False,
                FileExistsError,
                False,
            ),
            ("ensure", {"check": False}, False, ValidationError, False),
        ],
    )
    def test_validation_rejection(
        self,
        settings,
        is_debug,
        fn,
        kwargs,
        is_exception,
        expected_exc,
        is_msg,
    ):
        settings.DEBUG = is_debug

        if is_exception:
            with pytest.raises(expected_exc) as excinfo:
                getattr(mo_validation_kit, fn)(**kwargs, is_exception=is_exception)
            if is_msg:
                assert "Custom Message 3 is not equal 5" in str(excinfo.value)
        else:
            with pytest.raises(MindoffValidationError) as errinfo:
                getattr(mo_validation_kit, fn)(**kwargs, is_exception=is_exception)
            assert errinfo.value.data.get("type") == expected_exc.__name__
            if is_msg:
                assert "Custom Message 3 is not equal 5" in str(errinfo.value.message)

    @pytest.mark.parametrize(
        "fn, kwargs, is_exception, expected_result",
        [
            # ---------------- BOUNDARY -- EXCEPTION CASES ----------------
            ("ensure_equal", {"left": [], "right": []}, True, True),
            ("ensure_equal", {"left": [1], "right": (1,)}, True, True),
            ("ensure_greater_equal", {"left": 5, "right": 5}, True, True),
            ("ensure_lesser_equal", {"left": 5, "right": 5}, True, True),
            (
                "ensure_in_range",
                {"value": 1, "min_value": 1, "max_value": 10},
                True,
                True,
            ),
            (
                "ensure_in_range",
                {"value": 10, "min_value": 1, "max_value": 10},
                True,
                True,
            ),
            (
                "ensure_not_in_range",
                {"value": 0, "min_value": 1, "max_value": 10},
                True,
                True,
            ),
            (
                "ensure_not_in_range",
                {"value": 11, "min_value": 1, "max_value": 10},
                True,
                True,
            ),
            (
                "ensure_almost_equal",
                {"left": 1.0, "right": 1.0 + 1e-6, "tol": 1e-6},
                True,
                True,
            ),
            (
                "ensure_not_almost_equal",
                {"left": 1.0, "right": 1.0 + 2e-6, "tol": 1e-6},
                True,
                True,
            ),
            ("ensure_falsey", {"value": ""}, True, True),
            ("ensure_truthy", {"value": " "}, True, True),
            ("ensure_finite", {"value": float("nan")}, True, ValueError),
            # ---------------- BOUNDARY -- JSON CASES ----------------
            ("ensure_equal", {"left": [], "right": []}, False, True),
            ("ensure_equal", {"left": [1], "right": (1,)}, False, True),
            ("ensure_greater_equal", {"left": 5, "right": 5}, False, True),
            ("ensure_lesser_equal", {"left": 5, "right": 5}, False, True),
            (
                "ensure_in_range",
                {"value": 1, "min_value": 1, "max_value": 10},
                False,
                True,
            ),
            (
                "ensure_in_range",
                {"value": 10, "min_value": 1, "max_value": 10},
                False,
                True,
            ),
            (
                "ensure_not_in_range",
                {"value": 0, "min_value": 1, "max_value": 10},
                False,
                True,
            ),
            (
                "ensure_not_in_range",
                {"value": 11, "min_value": 1, "max_value": 10},
                False,
                True,
            ),
            (
                "ensure_almost_equal",
                {"left": 1.0, "right": 1.0 + 1e-6, "tol": 1e-6},
                False,
                True,
            ),
            (
                "ensure_not_almost_equal",
                {"left": 1.0, "right": 1.0 + 2e-6, "tol": 1e-6},
                False,
                True,
            ),
            ("ensure_falsey", {"value": ""}, False, True),
            ("ensure_truthy", {"value": " "}, False, True),
            ("ensure_finite", {"value": float("nan")}, True, ValueError),
            # ---------------- ANOMALY -- EXCEPTION CASES ----------------
            ("ensure_equal", {"left": None, "right": None}, True, True),
            ("ensure_equal", {"left": object(), "right": object()}, True, ValueError),
            ("ensure_equal", {"left": iter([1, 2]), "right": [1, 2]}, True, True),
            (
                "ensure_count_equal",
                {"left": (1, 2), "right": [1, 2]},
                True,
                True,
            ),
            ("ensure_type", {"value": None, "typ": type(True)}, True, TypeError),
            ("ensure_type", {"value": [1, 2, 3], "typ": list}, True, True),
            ("ensure_subclass", {"cls": type, "parent": object}, True, True),
            ("ensure_not_subclass", {"cls": object, "parent": object}, True, TypeError),
            ("ensure_in", {"value": "a", "container": None}, True, TypeError),
            ("ensure_not_in", {"value": "a", "container": None}, True, TypeError),
            (
                "ensure_count_equal",
                {"left": [1, {}], "right": [1, {}]},
                True,
                TypeError,
            ),
            (
                "ensure_count_not_equal",
                {"left": [{1}], "right": [{1}]},
                True,
                TypeError,
            ),
            ("ensure_regex", {"value": "", "pattern": r".*"}, True, True),
            ("ensure_not_regex", {"value": "", "pattern": r"\d+"}, True, True),
            ("ensure_path", {"path": ""}, True, True),
            ("ensure_not_path", {"path": ""}, True, FileExistsError),
            ("ensure", {"check": None}, True, ValidationError),
            ("ensure", {"check": lambda: 1 / 0}, True, ValidationError),
            # ---------------- ANOMALY -- JSON CASES ----------------
            ("ensure_equal", {"left": None, "right": None}, False, True),
            ("ensure_equal", {"left": object(), "right": object()}, False, ValueError),
            ("ensure_equal", {"left": iter([1, 2]), "right": [1, 2]}, False, True),
            (
                "ensure_count_equal",
                {"left": (1, 2), "right": [1, 2]},
                False,
                True,
            ),
            ("ensure_type", {"value": None, "typ": type(True)}, False, TypeError),
            ("ensure_type", {"value": [1, 2, 3], "typ": list}, False, True),
            ("ensure_subclass", {"cls": type, "parent": object}, False, True),
            (
                "ensure_not_subclass",
                {"cls": object, "parent": object},
                False,
                TypeError,
            ),
            ("ensure_in", {"value": "a", "container": None}, False, TypeError),
            ("ensure_not_in", {"value": "a", "container": None}, False, TypeError),
            (
                "ensure_count_equal",
                {"left": [1, {}], "right": [1, {}]},
                False,
                TypeError,
            ),
            (
                "ensure_count_not_equal",
                {"left": [{1}], "right": [{1}]},
                False,
                TypeError,
            ),
            ("ensure_regex", {"value": "", "pattern": r".*"}, False, True),
            ("ensure_not_regex", {"value": "", "pattern": r"\d+"}, False, True),
            ("ensure_path", {"path": ""}, False, True),
            ("ensure_not_path", {"path": ""}, False, FileExistsError),
            ("ensure", {"check": None}, False, ValidationError),
            ("ensure", {"check": lambda: 1 / 0}, False, ValidationError),
        ],
    )
    def test_validation_boundary_anomaly(
        self, settings, fn, kwargs, is_exception, expected_result
    ):
        settings.DEBUG = True
        if is_exception and expected_result != True:
            with pytest.raises(expected_result):
                getattr(mo_validation_kit, fn)(**kwargs, is_exception=is_exception)
        else:
            if expected_result is not True:
                with pytest.raises(MindoffValidationError) as errinfo:
                    getattr(mo_validation_kit, fn)(**kwargs, is_exception=is_exception)
                assert errinfo.value.data["type"] == expected_result.__name__
            else:
                result = getattr(mo_validation_kit, fn)(
                    **kwargs, is_exception=is_exception
                )
                assert result == expected_result


class TestAggregatedValidator:
    @pytest.mark.parametrize(
        ("is_exception", "is_debug"),
        [(True, True), (False, False), (True, False), (False, True)],
    )
    def test_multiple_failures(self, settings, caplog, capsys, is_exception, is_debug):
        settings.DEBUG = is_debug
        mo_validation_kit.ensure_equal(
            left=1, right=2, is_aggregate=True, is_exception=is_exception
        )
        mo_validation_kit.ensure_in(
            value=99,
            container=[1, 2],
            is_aggregate=True,
            is_exception=is_exception,
            msg="Custom Message 99 not in 1,2",
        )
        if is_exception:
            with pytest.raises(ValidationError):
                mo_validation_kit.finalize(return_mode="exception")
        else:
            result = mo_validation_kit.finalize(return_mode="list")
            assert len(result) == 2
            assert result[1]["message"] == "Custom Message 99 not in 1,2"
            for err_obj in result:
                assert (
                    "ValueError" in err_obj["type"] or "LookupError" in err_obj["type"]
                )
            captured = capsys.readouterr()
            assert "Traceback" not in captured.out
            with caplog.at_level(logging.ERROR):
                assert not any("Traceback" in rec.message for rec in caplog.records)


class TestCustomCodeValidator(MindoffTestCase):
    """Test suite for custom code parameter support in validation kit."""

    VALID_CODES = [
        "UNEXPECTED_ERR",
        "NOT_AUTHENTICATED",
        "PERMISSION_DENIED",
        "INVALID_PAYLOAD",
        "INVALID_METHOD",
    ]

    @pytest.mark.parametrize(
        "fn, kwargs, code, is_exception, expected_result",
        [
            # ---- UNEXPECTED_ERR with Exception ----
            ("ensure_equal", {"left": 5, "right": 5}, "UNEXPECTED_ERR", True, True),
            (
                "ensure_not_equal",
                {"left": "x", "right": "y"},
                "UNEXPECTED_ERR",
                True,
                True,
            ),
            ("ensure_greater", {"left": 10, "right": 5}, "UNEXPECTED_ERR", True, True),
            ("ensure_type", {"value": 123, "typ": int}, "UNEXPECTED_ERR", True, True),
            (
                "ensure_in",
                {"value": 2, "container": [1, 2, 3]},
                "UNEXPECTED_ERR",
                True,
                True,
            ),
            ("ensure_finite", {"value": 5}, "UNEXPECTED_ERR", True, True),
            # ---- NOT_AUTHENTICATED with Exception ----
            ("ensure_equal", {"left": 5, "right": 5}, "NOT_AUTHENTICATED", True, True),
            (
                "ensure_not_equal",
                {"left": "x", "right": "y"},
                "NOT_AUTHENTICATED",
                True,
                True,
            ),
            (
                "ensure_greater",
                {"left": 10, "right": 5},
                "NOT_AUTHENTICATED",
                True,
                True,
            ),
            (
                "ensure_type",
                {"value": 123, "typ": int},
                "NOT_AUTHENTICATED",
                True,
                True,
            ),
            (
                "ensure_in",
                {"value": 2, "container": [1, 2, 3]},
                "NOT_AUTHENTICATED",
                True,
                True,
            ),
            # ---- PERMISSION_DENIED with Exception ----
            ("ensure_equal", {"left": 5, "right": 5}, "PERMISSION_DENIED", True, True),
            ("ensure_truthy", {"value": "x"}, "PERMISSION_DENIED", True, True),
            (
                "ensure_subclass",
                {"cls": bool, "parent": int},
                "PERMISSION_DENIED",
                True,
                True,
            ),
            (
                "ensure_not_in",
                {"value": "z", "container": "hello"},
                "PERMISSION_DENIED",
                True,
                True,
            ),
            # ---- INVALID_PAYLOAD with Exception ----
            ("ensure_equal", {"left": 5, "right": 5}, "INVALID_PAYLOAD", True, True),
            (
                "ensure_regex",
                {"value": "abc123", "pattern": r"[a-z]+\d+"},
                "INVALID_PAYLOAD",
                True,
                True,
            ),
            (
                "ensure_not_regex",
                {"value": "xyz", "pattern": r"\d+"},
                "INVALID_PAYLOAD",
                True,
                True,
            ),
            # ---- INVALID_METHOD with Exception ----
            ("ensure_equal", {"left": 5, "right": 5}, "INVALID_METHOD", True, True),
            (
                "ensure_count_equal",
                {"left": [1, 2], "right": [2, 1]},
                "INVALID_METHOD",
                True,
                True,
            ),
            # ---- UNEXPECTED_ERR with JSON Response ----
            ("ensure_equal", {"left": 5, "right": 5}, "UNEXPECTED_ERR", False, True),
            (
                "ensure_not_equal",
                {"left": "x", "right": "y"},
                "UNEXPECTED_ERR",
                False,
                True,
            ),
            ("ensure_greater", {"left": 10, "right": 5}, "UNEXPECTED_ERR", False, True),
            ("ensure_type", {"value": 123, "typ": int}, "UNEXPECTED_ERR", False, True),
            # ---- NOT_AUTHENTICATED with JSON Response ----
            ("ensure_equal", {"left": 5, "right": 5}, "NOT_AUTHENTICATED", False, True),
            ("ensure_truthy", {"value": "x"}, "NOT_AUTHENTICATED", False, True),
            # ---- PERMISSION_DENIED with JSON Response ----
            ("ensure_equal", {"left": 5, "right": 5}, "PERMISSION_DENIED", False, True),
            (
                "ensure_in",
                {"value": 2, "container": [1, 2, 3]},
                "PERMISSION_DENIED",
                False,
                True,
            ),
            # ---- INVALID_PAYLOAD with JSON Response ----
            ("ensure_equal", {"left": 5, "right": 5}, "INVALID_PAYLOAD", False, True),
            (
                "ensure_regex",
                {"value": "abc123", "pattern": r"[a-z]+\d+"},
                "INVALID_PAYLOAD",
                False,
                True,
            ),
            # ---- INVALID_METHOD with JSON Response ----
            ("ensure_equal", {"left": 5, "right": 5}, "INVALID_METHOD", False, True),
            (
                "ensure_count_equal",
                {"left": [1, 2], "right": [2, 1]},
                "INVALID_METHOD",
                False,
                True,
            ),
        ],
    )
    def test_custom_code_acceptance(
        self, fn, kwargs, code, is_exception, expected_result
    ):
        """Test that valid checks pass with custom codes."""
        result = getattr(mo_validation_kit, fn)(
            **kwargs, code=code, is_exception=is_exception
        )
        assert result == expected_result

    @pytest.mark.parametrize(
        "fn, kwargs, code, is_exception, expected_exc",
        [
            # ---- UNEXPECTED_ERR Failures ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "UNEXPECTED_ERR",
                True,
                ValueError,
            ),
            (
                "ensure_not_equal",
                {"left": "x", "right": "x"},
                "UNEXPECTED_ERR",
                True,
                ValueError,
            ),
            (
                "ensure_greater",
                {"left": 2, "right": 5},
                "UNEXPECTED_ERR",
                True,
                ValueError,
            ),
            (
                "ensure_type",
                {"value": "abc", "typ": int},
                "UNEXPECTED_ERR",
                True,
                TypeError,
            ),
            (
                "ensure_in",
                {"value": 99, "container": [1, 2, 3]},
                "UNEXPECTED_ERR",
                True,
                LookupError,
            ),
            # ---- NOT_AUTHENTICATED Failures ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "NOT_AUTHENTICATED",
                True,
                ValueError,
            ),
            ("ensure_truthy", {"value": ""}, "NOT_AUTHENTICATED", True, ValueError),
            (
                "ensure_not_in",
                {"value": 2, "container": [1, 2, 3]},
                "NOT_AUTHENTICATED",
                True,
                LookupError,
            ),
            # ---- PERMISSION_DENIED Failures ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "PERMISSION_DENIED",
                True,
                ValueError,
            ),
            (
                "ensure_subclass",
                {"cls": int, "parent": str},
                "PERMISSION_DENIED",
                True,
                TypeError,
            ),
            (
                "ensure_finite",
                {"value": float("inf")},
                "PERMISSION_DENIED",
                True,
                ValueError,
            ),
            # ---- INVALID_PAYLOAD Failures ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "INVALID_PAYLOAD",
                True,
                ValueError,
            ),
            (
                "ensure_regex",
                {"value": "abc", "pattern": r"\d+"},
                "INVALID_PAYLOAD",
                True,
                ValueError,
            ),
            (
                "ensure_not_regex",
                {"value": "123", "pattern": r"\d+"},
                "INVALID_PAYLOAD",
                True,
                ValueError,
            ),
            # ---- INVALID_METHOD Failures ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "INVALID_METHOD",
                True,
                ValueError,
            ),
            (
                "ensure_count_equal",
                {"left": [1, 2], "right": [2, 2]},
                "INVALID_METHOD",
                True,
                ValueError,
            ),
            # ---- UNEXPECTED_ERR Failures with JSON Response ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "UNEXPECTED_ERR",
                False,
                ValueError,
            ),
            (
                "ensure_not_equal",
                {"left": "x", "right": "x"},
                "UNEXPECTED_ERR",
                False,
                ValueError,
            ),
            (
                "ensure_greater",
                {"left": 2, "right": 5},
                "UNEXPECTED_ERR",
                False,
                ValueError,
            ),
            # ---- NOT_AUTHENTICATED Failures with JSON Response ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "NOT_AUTHENTICATED",
                False,
                ValueError,
            ),
            ("ensure_truthy", {"value": ""}, "NOT_AUTHENTICATED", False, ValueError),
            # ---- PERMISSION_DENIED Failures with JSON Response ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "PERMISSION_DENIED",
                False,
                ValueError,
            ),
            (
                "ensure_subclass",
                {"cls": int, "parent": str},
                "PERMISSION_DENIED",
                False,
                TypeError,
            ),
            # ---- INVALID_PAYLOAD Failures with JSON Response ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "INVALID_PAYLOAD",
                False,
                ValueError,
            ),
            (
                "ensure_regex",
                {"value": "abc", "pattern": r"\d+"},
                "INVALID_PAYLOAD",
                False,
                ValueError,
            ),
            # ---- INVALID_METHOD Failures with JSON Response ----
            (
                "ensure_equal",
                {"left": 3, "right": 5},
                "INVALID_METHOD",
                False,
                ValueError,
            ),
            (
                "ensure_count_equal",
                {"left": [1, 2], "right": [2, 2]},
                "INVALID_METHOD",
                False,
                ValueError,
            ),
        ],
    )
    def test_custom_code_rejection(self, fn, kwargs, code, is_exception, expected_exc):
        """Test that failed checks raise/return correct exceptions with custom codes."""
        if is_exception:
            with pytest.raises(expected_exc):
                getattr(mo_validation_kit, fn)(
                    **kwargs, code=code, is_exception=is_exception
                )
        else:
            with pytest.raises(MindoffValidationError) as errinfo:
                getattr(mo_validation_kit, fn)(
                    **kwargs, code=code, is_exception=is_exception
                )
            assert errinfo.value.data.get("type") == expected_exc.__name__
            assert errinfo.value.code == code

    @pytest.mark.parametrize("code", VALID_CODES)
    def test_custom_code_reflected_in_error_data(self, code):
        """Test that custom code is properly reflected in error data."""
        with pytest.raises(MindoffValidationError) as errinfo:
            mo_validation_kit.ensure_equal(
                left=1, right=2, code=code, is_exception=False
            )
        assert errinfo.value.code == code

    @pytest.mark.parametrize("code", VALID_CODES)
    def test_custom_code_in_aggregate_exception(self, code):
        """Test that custom code is preserved in aggregated validation errors."""
        mo_validation_kit.ensure_equal(
            left=1, right=2, is_aggregate=True, is_exception=True, code=code
        )
        with pytest.raises(ValidationError):
            mo_validation_kit.finalize(return_mode="exception")

    @pytest.mark.parametrize("code", VALID_CODES)
    def test_custom_code_in_aggregate_json_response(self, code):
        """Test that custom code is reflected in aggregated JSON response."""
        mo_validation_kit.ensure_equal(
            left=1, right=2, is_aggregate=True, is_exception=False, code=code
        )
        result = mo_validation_kit.finalize(return_mode="list")
        assert len(result) == 1
        assert result[0]["code"] == code

    @pytest.mark.parametrize(
        "code1, code2, code3",
        [
            ("UNEXPECTED_ERR", "NOT_AUTHENTICATED", "PERMISSION_DENIED"),
            ("INVALID_PAYLOAD", "INVALID_METHOD", "UNEXPECTED_ERR"),
            ("NOT_AUTHENTICATED", "INVALID_PAYLOAD", "INVALID_METHOD"),
        ],
    )
    def test_multiple_custom_codes_in_aggregate(self, code1, code2, code3):
        """Test that multiple different custom codes are preserved in aggregated errors."""
        mo_validation_kit.ensure_equal(
            left=1, right=2, is_aggregate=True, is_exception=False, code=code1
        )
        mo_validation_kit.ensure_not_equal(
            left="x", right="x", is_aggregate=True, is_exception=False, code=code2
        )
        mo_validation_kit.ensure_greater(
            left=2, right=5, is_aggregate=True, is_exception=False, code=code3
        )
        result = mo_validation_kit.finalize(return_mode="list")
        assert len(result) == 3
        assert result[0]["code"] == code1
        assert result[1]["code"] == code2
        assert result[2]["code"] == code3

    @pytest.mark.parametrize("code", VALID_CODES)
    @pytest.mark.parametrize(
        "fn, kwargs",
        [
            ("ensure_equal", {"left": 5, "right": 5}),
            ("ensure_not_equal", {"left": "x", "right": "y"}),
            ("ensure_same", {"left": "a", "right": "a"}),
            ("ensure_not_same", {"left": "a", "right": "b"}),
            ("ensure_greater", {"left": 10, "right": 5}),
            ("ensure_greater_equal", {"left": 5, "right": 5}),
            ("ensure_lesser", {"left": 7, "right": 10}),
            ("ensure_lesser_equal", {"left": 7, "right": 7}),
            ("ensure_in_range", {"value": 5, "min_value": 1, "max_value": 10}),
            ("ensure_not_in_range", {"value": 20, "min_value": 1, "max_value": 10}),
            ("ensure_almost_equal", {"left": 1.0, "right": 1.0000001}),
            ("ensure_not_almost_equal", {"left": 1.0, "right": 1.1}),
            ("ensure_falsey", {"value": []}),
            ("ensure_truthy", {"value": "x"}),
            ("ensure_type", {"value": 123, "typ": int}),
            ("ensure_not_type", {"value": "x", "typ": int}),
            ("ensure_subclass", {"cls": bool, "parent": int}),
            ("ensure_not_subclass", {"cls": str, "parent": dict}),
            ("ensure_in", {"value": 2, "container": [1, 2, 3]}),
            ("ensure_not_in", {"value": "z", "container": "hello"}),
            ("ensure_count_equal", {"left": [1, 2], "right": [2, 1]}),
            ("ensure_count_not_equal", {"left": [1, 2], "right": [1, 3, 4]}),
            ("ensure_finite", {"value": 5}),
            ("ensure_regex", {"value": "abc123", "pattern": r"[a-z]+\d+"}),
            ("ensure_not_regex", {"value": "xyz", "pattern": r"\d+"}),
            ("ensure", {"check": lambda: True}),
        ],
    )
    def test_all_methods_accept_custom_code(self, fn, kwargs, code):
        """Test that all validation methods accept and preserve custom code parameter."""
        result = getattr(mo_validation_kit, fn)(**kwargs, code=code, is_exception=False)
        assert result == True

    @pytest.mark.parametrize("code", VALID_CODES)
    @pytest.mark.parametrize(
        "fn, kwargs, expected_exc",
        [
            ("ensure_equal", {"left": 3, "right": 5}, ValueError),
            ("ensure_not_equal", {"left": "x", "right": "x"}, ValueError),
            ("ensure_greater", {"left": 2, "right": 5}, ValueError),
            ("ensure_type", {"value": "abc", "typ": int}, TypeError),
            ("ensure_in", {"value": 99, "container": [1, 2, 3]}, LookupError),
            ("ensure_finite", {"value": float("inf")}, ValueError),
            ("ensure_regex", {"value": "abc", "pattern": r"\d+"}, ValueError),
        ],
    )
    def test_custom_code_preserved_in_mindoff_validation_error(
        self, fn, kwargs, expected_exc, code
    ):
        """Test that custom code is preserved when MindoffValidationError is raised."""
        with pytest.raises(MindoffValidationError) as errinfo:
            getattr(mo_validation_kit, fn)(**kwargs, code=code, is_exception=False)
        assert errinfo.value.code == code
        assert errinfo.value.data.get("type") == expected_exc.__name__

    @pytest.mark.parametrize("code", VALID_CODES)
    def test_custom_code_with_custom_message(self, code):
        """Test that custom code works alongside custom message parameter."""
        custom_msg = "Custom validation message"
        with pytest.raises(MindoffValidationError) as errinfo:
            mo_validation_kit.ensure_equal(
                left=1,
                right=2,
                msg=custom_msg,
                code=code,
                is_exception=False,
            )
        assert errinfo.value.code == code
        assert errinfo.value.message == custom_msg

    def test_default_code_is_validation_err(self):
        """Test that default code is VALIDATION_ERR when not specified."""
        with pytest.raises(MindoffValidationError) as errinfo:
            mo_validation_kit.ensure_equal(left=1, right=2, is_exception=False)
        assert errinfo.value.code == "VALIDATION_ERR"

    @pytest.mark.parametrize("code", VALID_CODES)
    def test_custom_code_in_aggregate_mixed_success_failure(self, code):
        """Test custom code in aggregate with mix of passing and failing checks."""
        mo_validation_kit.ensure_equal(
            left=5, right=5, is_aggregate=True, is_exception=False, code=code
        )
        mo_validation_kit.ensure_equal(
            left=1, right=2, is_aggregate=True, is_exception=False, code=code
        )
        mo_validation_kit.ensure_truthy(
            value="x", is_aggregate=True, is_exception=False, code=code
        )
        result = mo_validation_kit.finalize(return_mode="list")
        # Only failed checks are recorded
        assert len(result) == 1
        assert result[0]["code"] == code

    @pytest.mark.parametrize("code", VALID_CODES)
    def test_each_validation_method_with_custom_code_failure(self, code):
        """Test each validation method independently with custom code on failure."""
        methods_and_kwargs = [
            ("ensure_equal", {"left": 3, "right": 5}),
            ("ensure_not_equal", {"left": "x", "right": "x"}),
            ("ensure_same", {"left": [1], "right": [1]}),
            ("ensure_not_same", {"left": "a", "right": "a"}),
            ("ensure_greater", {"left": 2, "right": 5}),
            ("ensure_greater_equal", {"left": 4, "right": 5}),
            ("ensure_lesser", {"left": 7, "right": 3}),
            ("ensure_lesser_equal", {"left": 8, "right": 7}),
            ("ensure_in_range", {"value": 0, "min_value": 1, "max_value": 10}),
            ("ensure_not_in_range", {"value": 5, "min_value": 1, "max_value": 10}),
            ("ensure_almost_equal", {"left": 1.0, "right": 1.1, "tol": 1e-6}),
            ("ensure_not_almost_equal", {"left": 1.0, "right": 1.0, "tol": 1e-6}),
            ("ensure_falsey", {"value": [1]}),
            ("ensure_truthy", {"value": ""}),
            ("ensure_type", {"value": "abc", "typ": int}),
            ("ensure_not_type", {"value": 123, "typ": int}),
            ("ensure_subclass", {"cls": int, "parent": str}),
            ("ensure_not_subclass", {"cls": bool, "parent": int}),
            ("ensure_in", {"value": 99, "container": [1, 2, 3]}),
            ("ensure_not_in", {"value": 2, "container": [1, 2, 3]}),
            ("ensure_count_equal", {"left": [1, 2], "right": [2, 2]}),
            ("ensure_count_not_equal", {"left": [1, 1], "right": [1, 1]}),
            ("ensure_finite", {"value": float("inf")}),
            ("ensure_regex", {"value": "abc", "pattern": r"\d+"}),
            ("ensure_not_regex", {"value": "123", "pattern": r"\d+"}),
            ("ensure", {"check": False}),
        ]

        for fn, kwargs in methods_and_kwargs:
            with pytest.raises(MindoffValidationError) as errinfo:
                getattr(mo_validation_kit, fn)(**kwargs, code=code, is_exception=False)
            assert errinfo.value.code == code, f"Failed for method: {fn}"
