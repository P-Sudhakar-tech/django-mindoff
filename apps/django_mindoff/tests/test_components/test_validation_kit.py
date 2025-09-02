"""
TEST CASES:
1. Basic exception -- ensure_equal(a, b) ✅
2. Exception with custom message -- ensure_equal(a, b, msg="cusom message for validation") ✅
3. Json Response -- ensure_equal(a, b, is_exception=False) ✅
4. Json Response with custom message -- ensure_equal(a, b, is_exception=False, msg="VALIDATION_ERR") ✅
5. Aggregated Exception -- ensure_equal(a, b, is_aggregate=True) -- ensure_not_equal(c, d, is_aggregate=True) -- finalize() ✅
6. Aggregated Json Response -- ensure_equal(a, b, is_aggregate=True, is_exception=False) -- ensure_not_equal(c, d, is_aggregate=True, is_exception=False) -- finalize() ✅
7. Aggregated Json Response with custom message -- ensure_equal(a, b, is_aggregate=True, is_exception=False) -- ensure_not_equal(c, d, is_aggregate=True, is_exception=False) -- finalize(msg="VALIDATION_ERR") ✅

"""

import pytest
import sys
import logging
from apps.django_mindoff.components.validation_kit import (
    mo_validation_kit,
    ValidationError,
)
from django_mindoff.components.helpers.tdd_fixtures import LogicTestCase


class TestImmediateValidator(LogicTestCase):
    @pytest.mark.parametrize(
        "fn, kwargs, is_exception, expected_exc",
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
            ("ensure_empty", {"value": []}, True, True),
            ("ensure_not_empty", {"value": "x"}, True, True),
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
            ("ensure_exists", {"path": sys.executable}, True, True),
            ("ensure_not_exists", {"path": "nonexistent_file.tmp"}, True, True),
            ("ensure_equal", {"left": [1, 2, 3], "right": (1, 2, 3)}, True, True),
            ("ensure_empty", {"value": 0}, True, True),
            ("ensure_not_empty", {"value": True}, True, True),
            ("ensure_subclass", {"cls": str, "parent": object}, True, True),
            ("ensure_finite", {"value": 3.14}, True, True),
            ("ensure_regex", {"value": "hello", "pattern": r"hello"}, True, True),
            ("custom", {"check": lambda: True}, True, True),
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
            ("ensure_empty", {"value": []}, False, True),
            ("ensure_not_empty", {"value": "x"}, False, True),
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
            ("ensure_exists", {"path": sys.executable}, False, True),
            ("ensure_not_exists", {"path": "nonexistent_file.tmp"}, False, True),
            ("ensure_equal", {"left": [1, 2, 3], "right": (1, 2, 3)}, False, True),
            ("ensure_empty", {"value": 0}, False, True),
            ("ensure_not_empty", {"value": True}, False, True),
            ("ensure_subclass", {"cls": str, "parent": object}, False, True),
            ("ensure_finite", {"value": 3.14}, False, True),
            ("ensure_regex", {"value": "hello", "pattern": r"hello"}, False, True),
            ("custom", {"check": lambda: True}, False, True),
        ],
    )
    def test_validation_acceptance(self, fn, kwargs, is_exception, expected_exc):
        result = getattr(mo_validation_kit, fn)(**kwargs, is_exception=is_exception)
        assert result == expected_exc

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
            ("ensure_empty", {"value": [1]}, True, ValueError, False),
            ("ensure_not_empty", {"value": ""}, True, ValueError, False),
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
                "ensure_exists",
                {"path": "nonexistent_file.tmp"},
                True,
                FileNotFoundError,
                False,
            ),
            (
                "ensure_not_exists",
                {"path": sys.executable},
                True,
                FileExistsError,
                False,
            ),
            ("custom", {"check": False}, True, ValidationError, False),
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
            ("ensure_empty", {"value": [1]}, False, ValueError, False),
            ("ensure_not_empty", {"value": ""}, False, ValueError, False),
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
                "ensure_exists",
                {"path": "nonexistent_file.tmp"},
                False,
                FileNotFoundError,
                False,
            ),
            (
                "ensure_not_exists",
                {"path": sys.executable},
                False,
                FileExistsError,
                False,
            ),
            ("custom", {"check": False}, False, ValidationError, False),
        ],
    )
    def test_validation_rejection(
        self,
        settings,
        capsys,
        caplog,
        is_debug,
        fn,
        kwargs,
        is_exception,
        expected_exc,
        is_msg,
    ):
        settings.DEBUG = is_debug
        result = getattr(mo_validation_kit, fn)(**kwargs, is_exception=is_exception)
        assert result.status_code == 400
        result = result.data
        assert result["status"] == "fail"
        assert result["message"]["code"] == "VALIDATION_ERR"
        assert result["message"]["category"] == "danger"
        if is_exception:
            assert result["data"] == []
            description = result["message"]["description"]
            exc_name = expected_exc.__name__

            if is_debug:
                assert exc_name in description
                captured = capsys.readouterr()
                assert "Traceback" in captured.out
                if is_msg:
                    assert "Custom Message 3 is not equal 5" in captured.out
            else:
                assert exc_name not in description
                with caplog.at_level(logging.ERROR):
                    assert any("Traceback" in rec.message for rec in caplog.records)
                    if is_msg:
                        assert any(
                            "Custom Message 3 is not equal 5" in rec.message
                            for rec in caplog.records
                        )
        else:
            assert result["data"][0]["type"] == expected_exc.__name__
            if is_msg:
                assert result["data"][0]["message"] == "Custom Message 3 is not equal 5"

    @pytest.mark.parametrize(
        "fn, kwargs, is_exception, expected_exc",
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
            ("ensure_empty", {"value": ""}, True, True),
            ("ensure_not_empty", {"value": " "}, True, True),
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
            ("ensure_empty", {"value": ""}, False, True),
            ("ensure_not_empty", {"value": " "}, False, True),
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
            ("ensure_exists", {"path": ""}, True, True),
            ("ensure_not_exists", {"path": ""}, True, FileExistsError),
            ("custom", {"check": None}, True, ValidationError),
            ("custom", {"check": lambda: 1 / 0}, True, ValidationError),
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
            ("ensure_exists", {"path": ""}, False, True),
            ("ensure_not_exists", {"path": ""}, False, FileExistsError),
            ("custom", {"check": None}, False, ValidationError),
            ("custom", {"check": lambda: 1 / 0}, False, ValidationError),
        ],
    )
    def test_validation_boundary_anomaly(
        self, settings, capsys, fn, kwargs, is_exception, expected_exc
    ):
        settings.DEBUG = True
        result = getattr(mo_validation_kit, fn)(**kwargs, is_exception=is_exception)
        if expected_exc is not True:
            assert result.status_code == 400
            result = result.data
            assert result["status"] == "fail"
            assert result["message"]["code"] == "VALIDATION_ERR"
            if is_exception:
                assert result["data"] == []
                assert (
                    str(expected_exc) in result["message"]["description"]
                    or getattr(expected_exc, "__name__", None)
                    in result["message"]["description"]
                )
                captured_print = capsys.readouterr()
                assert "Traceback" in captured_print.out
            else:
                assert result["data"][0]["type"] == expected_exc.__name__

        else:
            assert result == expected_exc


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
        result = mo_validation_kit.finalize(is_exception=is_exception)
        assert result.status_code == 400
        result = result.data
        assert result["status"] == "fail"
        assert result["message"]["code"] == "VALIDATION_ERR"
        assert result["message"]["category"] == "danger"
        if is_exception:
            assert result["data"] == []
            description = result["message"]["description"]
            exc_name = ValidationError.__name__
            if is_debug:
                assert exc_name in description
                captured = capsys.readouterr()
                assert "Traceback" in captured.out
                assert "mo_validation_kit.ensure_equal" in captured.out
                assert "mo_validation_kit.ensure_in" in captured.out
                assert "Custom Message 99 not in 1,2" in captured.out
            else:
                assert exc_name not in description
                with caplog.at_level(logging.ERROR):
                    assert any("Traceback" in rec.message for rec in caplog.records)
                    assert any(
                        "mo_validation_kit.ensure_equal" in rec.message
                        for rec in caplog.records
                    )
                    assert any(
                        "mo_validation_kit.ensure_in" in rec.message
                        for rec in caplog.records
                    )
                    assert any(
                        "Custom Message 99 not in 1,2" in rec.message
                        for rec in caplog.records
                    )

        else:
            assert len(result["data"]) == 2
            assert result["data"][1]["message"] == "Custom Message 99 not in 1,2"
            for err_obj in result["data"]:
                assert (
                    "ValueError" in err_obj["type"] or "LookupError" in err_obj["type"]
                )

            captured = capsys.readouterr()
            assert "Traceback" not in captured.out
            with caplog.at_level(logging.ERROR):
                assert not any("Traceback" in rec.message for rec in caplog.records)
