import uuid
import warnings
from http import HTTPStatus
from typing import Dict, List, Literal, Optional, Set, Tuple, Union
from unittest.mock import MagicMock, patch

import pytest

from ....components.tdd_kit import MindoffTestCase
from ....components.tdd_kit import (
    _build_payload_from_schema,
    _generate_for_type,
)


# ════════════════════════════════════════════════════════════════════════
# 🧩 TEST DOUBLES
# ════════════════════════════════════════════════════════════════════════


def _make_api_cls(
    *,
    method="get",
    payload_schema=None,
    response_type="json",
    query_params_schema=None,
):
    class FakeAPI:
        pass

    FakeAPI.method = method
    FakeAPI.payload_schema = payload_schema
    FakeAPI.response_type = response_type
    FakeAPI.query_params_schema = query_params_schema
    return FakeAPI


def _make_raw_response(
    *,
    status_code=200,
    content_type="application/json",
    body=None,
):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"Content-Type": content_type}
    if isinstance(body, bytes):
        resp.content = body
        resp.json.side_effect = Exception("not JSON")
    elif isinstance(body, str):
        resp.content = body.encode()
        resp.json.side_effect = Exception("not JSON")
    elif body is None:
        resp.content = b"{}"
        resp.json.return_value = {
            "status": HTTPStatus.OK,
            "message": {
                "code": "ok",
                "title": "OK",
                "description": "desc",
                "category": "cat",
            },
            "data": [],
        }
    else:
        import json

        resp.content = json.dumps(body).encode()
        resp.json.return_value = body
    return resp


_SIMPLE_SCHEMA = {"name": str, "age": int, "score": float, "active": bool}
_LIST_SCHEMA = [{"name": str, "age": int}]
_LIST_PLAIN_SCHEMA = [str]

_VALID_JSON_BODY = {
    "status": HTTPStatus.OK,
    "message": {"code": "ok", "title": "t", "description": "d", "category": "c"},
    "data": [],
}


# ════════════════════════════════════════════════════════════════════════
# 🚂 TestBuildPayloadFromSchema
# ════════════════════════════════════════════════════════════════════════


class TestBuildPayloadFromSchema:
    """Unit tests for _build_payload_from_schema / _generate_for_type. No DB needed."""

    # ✅ ACCEPTANCE — primitives ─────────────────────────────────────────

    @pytest.mark.parametrize(
        "tp, check",
        [
            (int, lambda v: isinstance(v, int)),
            (float, lambda v: isinstance(v, float)),
            (bool, lambda v: isinstance(v, bool)),
            (bytes, lambda v: isinstance(v, bytes)),
            (uuid.UUID, lambda v: bool(uuid.UUID(v))),
            (str, lambda v: isinstance(v, str) and v.startswith("test_")),
        ],
    )
    def test_primitives(self, tp, check):
        """Primitive types generate a correctly-typed value."""
        result = _build_payload_from_schema({"field": tp})
        assert check(
            result["field"]
        ), f"{tp} produced unexpected value: {result['field']!r}"

    def test_none_type(self):
        """None / type(None) → None (both sentinels)."""
        assert _generate_for_type(None) is None
        assert _generate_for_type(type(None)) is None

    # ✅ ACCEPTANCE — bare collections ───────────────────────────────────

    @pytest.mark.parametrize(
        "tp, expected",
        [
            (list, []),
            (dict, {}),
            (tuple, ()),
            (set, []),  # JSON-serialisable
        ],
    )
    def test_bare_collections(self, tp, expected):
        """Bare collection types produce the correct empty structure."""
        result = _build_payload_from_schema({"field": tp})
        assert result["field"] == expected

    # ✅ ACCEPTANCE — Union / Optional ───────────────────────────────────

    @pytest.mark.parametrize(
        "tp",
        [
            Optional[str],
            Union[str, int],
            Union[None, str],
        ],
    )
    def test_union_and_optional_resolve_to_str(self, tp):
        """Union/Optional picks the first non-None branch (str in all cases here)."""
        result = _build_payload_from_schema({"field": tp})
        assert isinstance(result["field"], str)

    # ✅ ACCEPTANCE — typing generics ────────────────────────────────────

    def test_typing_list_of_str(self):
        """List[str] → single-item list of str."""
        result = _build_payload_from_schema({"field": List[str]})
        assert isinstance(result["field"], list)
        assert len(result["field"]) == 1
        assert isinstance(result["field"][0], str)

    def test_typing_set_of_str(self):
        """Set[str] → single-item list of str (JSON-serialisable)."""
        result = _build_payload_from_schema({"field": Set[str]})
        assert isinstance(result["field"], list)
        assert isinstance(result["field"][0], str)

    def test_typing_dict_str_int(self):
        """Dict[str, int] → dict with one str key and int value."""
        result = _build_payload_from_schema({"field": Dict[str, int]})
        assert isinstance(result["field"], dict)
        k, v = next(iter(result["field"].items()))
        assert isinstance(k, str) and isinstance(v, int)

    def test_typing_tuple_str_int(self):
        """Tuple[str, int] → list matching element types in order."""
        result = _build_payload_from_schema({"field": Tuple[str, int]})
        assert isinstance(result["field"], list)
        assert isinstance(result["field"][0], str)
        assert isinstance(result["field"][1], int)

    def test_typing_literal(self):
        """Literal['a', 'b'] → first value."""
        result = _build_payload_from_schema({"field": Literal["a", "b"]})
        assert result["field"] == "a"

    # ✅ ACCEPTANCE — schema shapes ──────────────────────────────────────

    def test_dict_schema_all_fields_present(self):
        """Dict schema produces all declared keys."""
        result = _build_payload_from_schema(_SIMPLE_SCHEMA)
        assert set(result.keys()) == set(_SIMPLE_SCHEMA.keys())

    @pytest.mark.parametrize("list_dict_count, expected_len", [(1, 1), (3, 3)])
    def test_list_of_schema_dict(self, list_dict_count, expected_len):
        """list[{...}] generates list_dict_count dicts with correct field types."""
        result = _build_payload_from_schema(_LIST_SCHEMA, list_dict_count)
        assert isinstance(result, list) and len(result) == expected_len
        for item in result:
            assert isinstance(item["name"], str) and isinstance(item["age"], int)

    def test_list_of_plain_type(self):
        """list[str] (non-schema-dict) → single-item list of str."""
        result = _build_payload_from_schema(_LIST_PLAIN_SCHEMA)
        assert isinstance(result, list) and len(result) == 1
        assert isinstance(result[0], str)

    @pytest.mark.parametrize("schema, expected", [([], []), ({}, {})])
    def test_empty_schema(self, schema, expected):
        """Empty list/dict schema → matching empty collection."""
        assert _build_payload_from_schema(schema) == expected

    @pytest.mark.parametrize(
        "schema, path",
        [
            ({"outer": {"inner": str}}, ["outer", "inner"]),
            ({"l1": {"l2": {"l3": str}}}, ["l1", "l2", "l3"]),
        ],
    )
    def test_nested_schema_dict(self, schema, path):
        """Nested dict schemas are recursed correctly at all depths."""
        node = _build_payload_from_schema(schema)
        for key in path:
            assert isinstance(node, dict)
            node = node[key]
        assert isinstance(node, str)

    # 🚫 REJECTION / ANOMALY ─────────────────────────────────────────────

    def test_unrecognised_type_returns_none_and_warns(self, capsys):
        """Unrecognised type → None + yellow WARNING printed, no crash."""

        class WeirdType:
            pass

        result = _build_payload_from_schema({"field": WeirdType})
        assert result["field"] is None
        assert "WARNING" in capsys.readouterr().out

    def test_unexpected_schema_shape_returns_empty_dict_and_warns(self, capsys):
        """Schema that is not list or dict → empty dict + yellow WARNING."""
        result = _build_payload_from_schema("not_a_schema")
        assert result == {}
        assert "WARNING" in capsys.readouterr().out

    def test_unrecognised_type_never_raises(self):
        """Unrecognised type must always return gracefully."""

        class AnotherWeirdType:
            pass

        try:
            _build_payload_from_schema({"f": AnotherWeirdType})
        except Exception as e:
            pytest.fail(f"Raised unexpectedly: {e}")

    # 🚧 BOUNDARY ────────────────────────────────────────────────────────

    def test_large_schema_all_fields_generated(self):
        """20-field schema → all 20 fields present in result."""
        assert (
            len(_build_payload_from_schema({f"field_{i}": str for i in range(20)}))
            == 20
        )

    def test_list_dict_count_zero_returns_empty_list(self):
        """list_dict_count=0 → empty list, no crash."""
        assert _build_payload_from_schema(_LIST_SCHEMA, list_dict_count=0) == []


# ════════════════════════════════════════════════════════════════════════
# 🚂 TestMoTestApi
# ════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestMoTestApi(MindoffTestCase):
    """Tests for the mo_test_api fixture."""

    API_URL_NAME = "tdd_test__sample_api"

    def _patched_call(self, api_cls, http_method, **call_kwargs):
        """Patch resolver + reverse + client method; return (response, mock)."""
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=api_cls,
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ),
            patch.object(
                self.client, http_method, return_value=_make_raw_response()
            ) as mock,
        ):
            response = self.mo_test_api(self.API_URL_NAME, **call_kwargs)
        return response, mock

    # ✅ ACCEPTANCE ───────────────────────────────────────────────────────

    def test_returns_raw_response_object(self):
        """mo_test_api returns an object with .status_code, .headers, .content."""
        response, _ = self._patched_call(_make_api_cls(method="get"), "get")
        assert hasattr(response, "status_code")
        assert hasattr(response, "headers")
        assert hasattr(response, "content")

    @pytest.mark.parametrize("method", ["get", "delete"])
    def test_get_and_delete_send_no_payload(self, method):
        """GET and DELETE never include a data kwarg."""
        _, mock = self._patched_call(_make_api_cls(method=method), method)
        assert "data" not in (mock.call_args.kwargs or {})

    @pytest.mark.parametrize("method", ["post", "put"])
    def test_post_and_put_with_schema_auto_generates(self, method, capsys):
        """POST and PUT both trigger payload auto-generation from schema."""
        _, mock = self._patched_call(
            _make_api_cls(method=method, payload_schema=_SIMPLE_SCHEMA), method
        )
        assert "Auto-generating" in capsys.readouterr().out
        sent = mock.call_args.kwargs.get("data") or mock.call_args.args[1]
        assert isinstance(sent, dict)
        assert set(sent.keys()) == set(_SIMPLE_SCHEMA.keys())

    def test_post_with_no_schema_warns_and_sends_empty_dict(self):
        """POST + payload_schema=None → warnings.warn issued, empty dict sent."""
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=_make_api_cls(method="post", payload_schema=None),
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ),
            patch.object(
                self.client, "post", return_value=_make_raw_response()
            ) as mock,
        ):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                self.mo_test_api(self.API_URL_NAME)
            assert any("payload_schema is None" in str(x.message) for x in w)
            sent = mock.call_args.kwargs.get("data")
            if sent is None and len(mock.call_args.args) > 1:
                sent = mock.call_args.args[1]
            assert sent == {}

    def test_custom_payload_overrides_schema_and_suppresses_notice(self, capsys):
        """custom_payload bypasses schema generation — no ANSI notice, exact dict sent."""
        custom = {"custom_key": "custom_value"}
        _, mock = self._patched_call(
            _make_api_cls(method="post", payload_schema=_SIMPLE_SCHEMA),
            "post",
            custom_payload=custom,
        )
        assert "Auto-generating" not in capsys.readouterr().out
        sent = mock.call_args.kwargs.get("data") or mock.call_args.args[1]
        assert sent == custom

    def test_url_kwargs_passed_to_reverse(self):
        """url_kwargs supplied by caller are forwarded to reverse."""
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=_make_api_cls(method="get"),
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={"pk": "int"},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ) as mock_rev,
            patch.object(self.client, "get", return_value=_make_raw_response()),
        ):
            self.mo_test_api(self.API_URL_NAME, url_kwargs={"pk": 42})
        mock_rev.assert_called_once_with(self.API_URL_NAME, kwargs={"pk": 42})

    def test_missing_url_kwargs_raises_with_helpful_message(self):
        """URL has named groups but url_kwargs not supplied → ValueError listing required kwargs."""
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=_make_api_cls(method="get"),
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={"pk": "int", "slug": "slug"},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ),
        ):
            with pytest.raises(ValueError, match="pk"):
                self.mo_test_api(self.API_URL_NAME)

    def test_no_url_groups_needs_no_url_kwargs(self):
        """URL with no named groups works fine without url_kwargs."""
        _, mock = self._patched_call(_make_api_cls(method="get"), "get")
        assert mock.called

    def test_query_params_schema_auto_generates_and_appends(self, capsys):
        """query_params_schema on API class → auto-generated params appended to URL."""
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=_make_api_cls(
                    method="get",
                    query_params_schema={"page": int, "search": str},
                ),
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ),
            patch.object(self.client, "get", return_value=_make_raw_response()) as mock,
        ):
            self.mo_test_api(self.API_URL_NAME)
        assert "Auto-generating" in capsys.readouterr().out
        url = mock.call_args.args[0]
        assert "page=" in url and "search=" in url

    def test_custom_query_params_override_schema(self):
        """custom_query_params overrides auto-generation from query_params_schema."""
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=_make_api_cls(
                    method="get",
                    query_params_schema={"page": int},
                ),
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ),
            patch.object(self.client, "get", return_value=_make_raw_response()) as mock,
        ):
            self.mo_test_api(self.API_URL_NAME, custom_query_params={"page": 99})
        url = mock.call_args.args[0]
        assert "page=99" in url

    def test_no_query_params_schema_omits_query_string(self):
        """No query_params_schema and no custom_query_params → URL has no query string."""
        _, mock = self._patched_call(_make_api_cls(method="get"), "get")
        url = mock.call_args.args[0]
        assert "?" not in url

    def test_user_triggers_force_authenticate(self):
        """Passing user= calls client.force_authenticate with that user."""
        fake_user = MagicMock()
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=_make_api_cls(method="get"),
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ),
            patch.object(self.client, "get", return_value=_make_raw_response()),
            patch.object(self.client, "force_authenticate") as mock_auth,
        ):
            self.mo_test_api(self.API_URL_NAME, user=fake_user)
        mock_auth.assert_called_once_with(user=fake_user)

    def test_no_user_skips_force_authenticate(self):
        """user=None → force_authenticate never called."""
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=_make_api_cls(method="get"),
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ),
            patch.object(self.client, "get", return_value=_make_raw_response()),
            patch.object(self.client, "force_authenticate") as mock_auth,
        ):
            self.mo_test_api(self.API_URL_NAME)
        mock_auth.assert_not_called()

    def test_accept_header_always_json_and_custom_headers_merged(self):
        """Accept: application/json always present; extra headers merged, not replaced."""
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=_make_api_cls(method="get"),
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ),
            patch.object(self.client, "get", return_value=_make_raw_response()) as mock,
        ):
            self.mo_test_api(self.API_URL_NAME, headers={"X-Custom": "value"})
        sent = mock.call_args.kwargs.get("headers", {})
        assert sent.get("Accept") == "application/json"
        assert sent.get("X-Custom") == "value"

    def test_list_dict_count_controls_schema_list_length(self, capsys):
        """list_dict_count=3 → list payload has 3 dicts."""
        _, mock = self._patched_call(
            _make_api_cls(method="post", payload_schema=_LIST_SCHEMA),
            "post",
            list_dict_count=3,
        )
        capsys.readouterr()
        sent = mock.call_args.kwargs.get("data") or mock.call_args.args[1]
        assert isinstance(sent, list) and len(sent) == 3

    # 🚫 REJECTION ────────────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "method, payload",
        [
            ("get", {"bad": "payload"}),
            ("delete", {"bad": "payload"}),
        ],
    )
    def test_get_and_delete_with_payload_raises(self, method, payload):
        """GET and DELETE with a payload → raises."""
        with (
            patch(
                "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
                return_value=_make_api_cls(method=method),
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit._get_url_pattern_named_groups",
                return_value={},
            ),
            patch(
                "apps.django_mindoff.components.tdd_kit.reverse", return_value="/fake/"
            ),
        ):
            with pytest.raises(Exception):
                self.mo_test_api(self.API_URL_NAME, custom_payload=payload)


# ════════════════════════════════════════════════════════════════════════
# 🚂 TestMoAssertApiResponse
# ════════════════════════════════════════════════════════════════════════


@pytest.mark.django_db
class TestMoAssertApiResponse(MindoffTestCase):
    """Tests for the mo_assert_api_response fixture."""

    API_URL_NAME = "tdd_test__assert_api"

    def _assert(self, api_cls, response, **kwargs):
        with patch(
            "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
            return_value=api_cls,
        ):
            self.mo_assert_api_response(
                api_url_name=self.API_URL_NAME,
                response=response,
                **kwargs,
            )

    # ✅ ACCEPTANCE — JSON envelope ───────────────────────────────────────

    def test_json_valid_envelope_passes(self):
        """Well-formed JSON envelope with all required keys → no AssertionError."""
        self._assert(_make_api_cls(response_type="json"), _make_raw_response())

    @pytest.mark.parametrize(
        "missing_key, match",
        [
            ("status", "status"),
            ("message", "message"),
            ("data", "data"),
        ],
    )
    def test_json_missing_top_level_key_fails(self, missing_key, match):
        """JSON body missing any top-level key → AssertionError."""
        body = {k: v for k, v in _VALID_JSON_BODY.items() if k != missing_key}
        with pytest.raises(AssertionError, match=match):
            self._assert(
                _make_api_cls(response_type="json"), _make_raw_response(body=body)
            )

    @pytest.mark.parametrize(
        "missing_key", ["code", "title", "description", "category"]
    )
    def test_json_missing_message_subkey_fails(self, missing_key):
        """JSON message block missing any sub-key → AssertionError."""
        msg = {k: v for k, v in _VALID_JSON_BODY["message"].items() if k != missing_key}
        body = {**_VALID_JSON_BODY, "message": msg}
        with pytest.raises(AssertionError, match=missing_key):
            self._assert(
                _make_api_cls(response_type="json"), _make_raw_response(body=body)
            )

    def test_json_message_subkey_wrong_type_fails(self):
        """message.code is int, not str → AssertionError."""
        body = {
            **_VALID_JSON_BODY,
            "message": {**_VALID_JSON_BODY["message"], "code": 123},
        }
        with pytest.raises(AssertionError, match="string"):
            self._assert(
                _make_api_cls(response_type="json"), _make_raw_response(body=body)
            )

    def test_json_data_not_list_fails(self):
        """JSON 'data' is a dict, not a list → AssertionError."""
        body = {**_VALID_JSON_BODY, "data": {"not": "a list"}}
        with pytest.raises(AssertionError, match="list"):
            self._assert(
                _make_api_cls(response_type="json"), _make_raw_response(body=body)
            )

    def test_wrong_content_type_for_json_fails(self):
        """response_type='json' but Content-Type is text/html → AssertionError."""
        resp = _make_raw_response(content_type="text/html", body="<html/>")
        with pytest.raises(AssertionError, match="JSON"):
            self._assert(_make_api_cls(response_type="json"), resp)

    # ✅ ACCEPTANCE — status code ─────────────────────────────────────────

    def test_wrong_status_code_fails(self):
        """Response status_code != expected → AssertionError containing the actual code."""
        resp = _make_raw_response()
        resp.status_code = 404
        with pytest.raises(AssertionError, match="404"):
            self._assert(_make_api_cls(response_type="json"), resp)

    def test_expected_status_code_400_passes(self):
        """expected_status_code=400 with a matching response → passes."""
        resp = _make_raw_response(content_type="text/plain", body="bad request")
        resp.status_code = 400
        with patch(
            "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
            return_value=_make_api_cls(response_type="plain"),
        ):
            self.mo_assert_api_response(
                api_url_name=self.API_URL_NAME,
                response=resp,
                expected_status_code=400,
            )

    # ✅ ACCEPTANCE — all supported response type branches ────────────────

    @pytest.mark.parametrize(
        "response_type, content_type, body",
        [
            ("binary", "application/octet-stream", b"\x00\x01\x02"),
            ("html", "text/html", "<html><body>ok</body></html>"),
            ("plain", "text/plain", "just some text"),
        ],
    )
    def test_valid_response_types_pass(self, response_type, content_type, body):
        """Each supported response_type passes with correct content-type and body."""
        resp = _make_raw_response(content_type=content_type, body=body)
        self._assert(_make_api_cls(response_type=response_type), resp)

    def test_others_response_type_skips_content_type_assertion(self):
        """response_type='others' → only status code checked, content-type ignored."""
        resp = _make_raw_response(
            content_type="application/x-custom-format", body=b"\xde\xad\xbe\xef"
        )
        self._assert(_make_api_cls(response_type="others"), resp)

    @pytest.mark.parametrize(
        "response_type, content_type, body, match",
        [
            ("html", "text/html", "<div>no tag</div>", "html"),
            ("plain", "application/json", None, "plain"),
        ],
    )
    def test_wrong_content_or_body_fails(
        self, response_type, content_type, body, match
    ):
        """Mismatched content-type or invalid body → AssertionError."""
        resp = _make_raw_response(content_type=content_type, body=body)
        with pytest.raises(AssertionError, match=match):
            self._assert(_make_api_cls(response_type=response_type), resp)

    def test_binary_empty_content_fails(self):
        """binary response with no content → AssertionError."""
        resp = _make_raw_response(content_type="application/octet-stream", body=b"")
        resp.content = b""
        with pytest.raises(AssertionError):
            self._assert(_make_api_cls(response_type="binary"), resp)

    def test_none_response_fails(self):
        """response=None → AssertionError immediately."""
        with patch(
            "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
            return_value=_make_api_cls(),
        ):
            with pytest.raises(AssertionError, match="no response"):
                self.mo_assert_api_response(
                    api_url_name=self.API_URL_NAME, response=None
                )

    # ✅ ACCEPTANCE — custom_response_type override ───────────────────────

    def test_custom_response_type_overrides_class_declaration(self):
        """custom_response_type='plain' overrides class response_type='json'."""
        resp = _make_raw_response(content_type="text/plain", body="override works")
        with patch(
            "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
            return_value=_make_api_cls(response_type="json"),
        ):
            self.mo_assert_api_response(
                api_url_name=self.API_URL_NAME,
                response=resp,
                custom_response_type="plain",
            )

    @pytest.mark.parametrize("invalid_type", ["JSON", "PLAIN", "Html", "xml", "file"])
    def test_invalid_custom_response_type_raises(self, invalid_type):
        """Values not in the Literal set → TypeCheckError raised by typeguard."""
        from typeguard import TypeCheckError

        with patch(
            "apps.django_mindoff.components.tdd_kit._get_api_cls_attributes",
            return_value=_make_api_cls(),
        ):
            with pytest.raises(TypeCheckError):
                self.mo_assert_api_response(
                    api_url_name=self.API_URL_NAME,
                    response=_make_raw_response(),
                    custom_response_type=invalid_type,
                )
