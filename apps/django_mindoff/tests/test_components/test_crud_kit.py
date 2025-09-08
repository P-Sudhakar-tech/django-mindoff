"""
1. Column Validation Exact Columns Accepts
3. Column Validation Extra Columns removed Accepts
3. Column Validation Add Missing Non Required Columns Accepts
4. Column Validation Missing Required Columns Rejects


1. Row Validation Valid Rows Accepts
2. Row Validation Incorrect Row Partial Parent Rejects
3. Row Validation Incorrect Row Partial First Child Rejects
4. Row Validation Incorrect Row Partial Last Child Rejects
5. Row Validation Incorrect Row all Rejects

1. Foreign Key Validation Valid Rows Accepts
2. Foreign Key Validation Invalid Rows Partial Rejects
3. Foreign Key Validation Invalid Rows all Rejects
"""

import pytest
import polars as pl
import polars.testing as pl_testing
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from apps.django_mindoff.components.tdd_kit import MindoffTestCase
from apps.django_mindoff.components.crud_kit import mo_crud_kit
from apps.django_mindoff.components.polars_kit import mo_polars_kit


@pytest.mark.django_db(transaction=True)
class TestValidateCreateCrud(MindoffTestCase):
    @pytest.mark.parametrize("is_lazy", [False, True])
    @pytest.mark.parametrize(
        "case_name, remove_columns, modify_rows, is_partial, expected_status",
        [
            # ---------------- Acceptance ----------------
            (
                "col_exact_accepts",
                [],
                [
                    {},
                    {},
                    {
                        0: {"chapter_id": None},
                        1: {"chapter_id": None},
                    },
                ],
                True,
                "ok",
            ),
            ("col_exact_accepts", [], [], False, "ok"),
            (
                "col_extra_removed_accepts",
                [["nickname"], ["edition"], ["summary"]],
                [],
                True,
                "ok",
            ),
            (
                "col_extra_removed_accepts",
                [["nickname"], ["edition"], ["summary"]],
                [],
                False,
                "ok",
            ),
            ("col_add_missing_accepts", [], [], True, "ok"),
            ("col_add_missing_accepts", [], [], False, "ok"),
            ("row_valid_accepts", [], [], True, "ok"),
            ("row_valid_accepts", [], [], False, "ok"),
            (
                "fk_optional_none_accepts",
                [],
                [
                    {},
                    {},
                    {0: {"author_id": None}},
                ],
                True,
                "ok",
            ),
            (
                "fk_optional_none_accepts",
                [],
                [
                    {},
                    {},
                    {0: {"author_id": None}},
                ],
                False,
                "ok",
            ),
            ("fk_valid_accepts", [], [], True, "ok"),
            ("fk_valid_accepts", [], [], False, "ok"),
            # ---------------- Rejection ----------------
            (
                "col_missing_required_rejects",
                [["name"], ["title"], ["title"]],
                [],
                False,
                "fail",
            ),
            (
                "row_partial_parent_rejects",
                [],
                [{0: {"name": None}}],
                True,
                "partial_ok",
            ),
            (
                "row_partial_first_child_rejects",
                [],
                [{}, {1: {"pages": "abc", "title": None}}],
                True,
                "partial_ok",
            ),
            (
                "row_partial_last_child_rejects",
                [],
                [{}, {}, {0: {"order": "first", "title": None}}],
                True,
                "partial_ok",
            ),
            (
                "row_all_rejects",
                [],
                [
                    {0: {"name": None}, 1: {"name": None}},
                    {0: {"title": None, "pages": "bad"}},
                    {0: {"title": None, "order": None}},
                ],
                False,
                "fail",
            ),
            (
                "fk_partial_required_fk_none_rejects",
                [],
                [
                    {},
                    {},
                    {0: {"book_id": None}},
                ],
                True,
                "raise",
            ),
            (
                "fk_partial_required_fk_none_rejects",
                [],
                [
                    {},
                    {},
                    {0: {"book_id": None}},
                ],
                False,
                "raise",
            ),
            (
                "fk_all_required_fk_none_rejects",
                [],
                [
                    {},
                    {},
                    {0: {"book_id": None}, 1: {"author_id": None}},
                ],
                False,
                "raise",
            ),
            (
                "fk_invalid_partial_rejects",
                [],
                [{0: {"author_id": uuid.uuid4()}}],
                True,
                "raise",
            ),
            (
                "fk_invalid_all_rejects",
                [],
                [
                    {0: {"author_id": uuid.uuid4()}},
                    {0: {"book_id": uuid.uuid4()}, 1: {"author_id": uuid.uuid4()}},
                ],
                False,
                "raise",
            ),
        ],
    )
    def test_validate_create_accepts_rejects(
        self,
        case_name,
        remove_columns,
        modify_rows,
        is_partial,
        expected_status,
        is_lazy,
    ):
        app_name = self.mo_mock_app()
        author_model, book_model, chapter_model = self._make_model(app_name)
        df_dict = self.mo_mock_model_dfs(
            models=[author_model, book_model, chapter_model],
            exclude_columns=remove_columns,
            modify=modify_rows,
            counts=[2, 1, 1],
        )
        if is_lazy:
            df_dict = self._convert_to_lazy_dict(df_dict)
        for df in df_dict.values():
            assert not mo_polars_kit.is_frm_empty(df)
        if expected_status == "raise":
            with pytest.raises(ValueError):
                mo_crud_kit.create(df_dict, is_partial=is_partial)
            return
        status, valid_dfs, invalid_dfs = mo_crud_kit.create(
            df_dict, is_partial=is_partial
        )
        if is_lazy:
            valid_dfs = mo_polars_kit.collect_model_frms(valid_dfs, streaming=True)
            invalid_dfs = mo_polars_kit.collect_model_frms(invalid_dfs, streaming=True)
        invalid_error_info = [
            info
            for df in invalid_dfs.values()
            if "__error__info" in df.columns
            for info in df["__error__info"].to_list()
        ]
        assert case_name is not None
        assert status == expected_status
        for df in valid_dfs.values():
            assert "__error__info" not in df.columns
        for df in invalid_dfs.values():
            assert "__error__info" in df.columns
        if expected_status == "ok":
            assert not mo_polars_kit.is_model_frms_empty(valid_dfs)
            assert mo_polars_kit.is_model_frms_empty(invalid_dfs)
            assert len(invalid_error_info) == 0
            self._assert_db_matches(valid_dfs)
        elif expected_status == "partial_ok":
            assert not mo_polars_kit.is_model_frms_empty(valid_dfs)
            assert not mo_polars_kit.is_model_frms_empty(invalid_dfs)
            assert len(invalid_error_info) != 0
            self._assert_db_matches(valid_dfs)
        elif expected_status == "fail":
            assert mo_polars_kit.is_model_frms_empty(valid_dfs)
            assert not mo_polars_kit.is_model_frms_empty(invalid_dfs)
            assert len(invalid_error_info) != 0

    def _make_model(self, app_name):
        author_model = self.mo_mock_model(
            model_name="AuthorModel",
            app_name=app_name,
            fields={
                "name": models.CharField(max_length=50),
                "nickname": models.CharField(max_length=50, blank=True, null=True),
            },
        )
        book_model = self.mo_mock_model(
            model_name="BookModel",
            app_name=app_name,
            fields={
                "title": models.CharField(max_length=100),
                "pages": models.IntegerField(),
                "edition": models.CharField(max_length=50, blank=True, null=True),
                "summary": models.TextField(blank=True, null=True),
            },
            foreign_keys=[(author_model._meta.app_label, author_model.__name__)],
        )
        chapter_model = self.mo_mock_model(
            model_name="ChapterModel",
            app_name=app_name,
            fields={
                "title": models.CharField(max_length=100),
                "order": models.IntegerField(),
                "summary": models.TextField(blank=True, null=True),
            },
            foreign_keys=[
                (author_model._meta.app_label, author_model.__name__, "optional"),
                (book_model._meta.app_label, book_model.__name__),
            ],
        )
        return author_model, book_model, chapter_model

    def _convert_to_lazy_dict(self, df_dict: dict):
        model_ldf = {}
        for k, v in df_dict.items():
            if isinstance(v, pl.DataFrame):
                model_ldf[k] = v.lazy()
            else:
                model_ldf[k] = v

        return model_ldf

    def _assert_db_matches(self, valid_dfs: dict[type[models.Model], pl.DataFrame]):
        for model, df in valid_dfs.items():
            # Grab all PKs we just inserted/updated
            pk_field = model._meta.pk.name
            pk_column = model._meta.pk.column
            pks = df[pk_column].to_list()
            db_rows = model.objects.filter(**{f"{pk_field}__in": pks}).values()
            db_df = pl.DataFrame(list(db_rows))
            assert not mo_polars_kit.is_frm_empty(
                db_df
            ), f"{model.__name__}: no rows found in database"
            db_df = self._validate_and_normalize_db_df(db_df, model)
            assert db_df.shape[0] == df.shape[0], (
                f"{model.__name__}: row count mismatch "
                f"(expected {df.shape[0]}, got {db_df.shape[0]})"
            )

            for col in df.columns:
                if col not in db_df.columns:
                    continue
                expected = df.sort(by=pk_column)[col]
                actual = db_df.sort(by=pk_column)[col]
                pl_testing.assert_series_equal(
                    expected,
                    actual,
                    check_names=True,
                    check_dtype=False,
                    check_exact=True,
                )

    def _validate_and_normalize_db_df(
        self, db_df: pl.DataFrame | pl.LazyFrame, model: type[models.Model]
    ):
        fields = list(model._meta.concrete_fields)
        for f in fields:
            pk_field = f.name
            pk_column = f.column
            if pk_field != pk_column and pk_field in db_df.columns:
                db_df = db_df.rename({pk_field: pk_column})
            if isinstance(
                f, (models.UUIDField, models.ForeignKey, models.OneToOneField)
            ):
                col_name = pk_column or pk_field
                if col_name in db_df.columns:
                    db_df = db_df.with_columns(
                        db_df[col_name]
                        .map_elements(lambda x: str(x) if x is not None else None)
                        .str.to_lowercase()
                        .str.replace_all("-", "")
                        .cast(pl.Utf8)
                        .alias(col_name)
                    )
        expected_cols = [f.column or f.name for f in fields]
        missing = [c for c in expected_cols if c not in db_df.columns]
        assert len(missing) == 0, f"Missing columns {model.__name__}: {missing}"
        return db_df
