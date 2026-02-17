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

import uuid

import polars as pl
import polars.testing as pl_testing
import pytest
from django.db import models
from django.db.models import Count, F
from typeguard import TypeCheckError

from ...components.crud_kit import mo_crud_kit
from ...components.polars_kit import mo_polars_kit
from ...components.tdd_kit import MindoffTestCase
from ...components.validation_kit import ValidationError

shared_uuid_author_book_relation = str(uuid.uuid4().hex)


@pytest.mark.django_db(transaction=True)
class TestCreateCrud(MindoffTestCase):
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
                        0: {"id": None},
                        1: {"id": None},
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
                    {0: {"author_ref_id": None}},
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
                    {0: {"author_ref_id": None}},
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
                    {0: {"book_ref_id": None}},
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
                    {0: {"book_ref_id": None}},
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
                    {0: {"book_ref_id": None}, 1: {"author_ref_id": None}},
                ],
                False,
                "raise",
            ),
            (
                "fk_invalid_partial_rejects",
                [],
                [{0: {"id": str(uuid.uuid4())}}],
                True,
                "raise",
            ),
            (
                "fk_invalid_all_rejects",
                [],
                [
                    {0: {"id": str(uuid.uuid4())}},
                    {
                        0: {"id": str(uuid.uuid4())},
                        1: {"author_ref_id": str(uuid.uuid4())},
                    },
                ],
                False,
                "raise",
            ),
        ],
    )
    def test_create_with_validation_accepts_rejects(
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

    @pytest.mark.parametrize("is_lazy", [False, True])
    @pytest.mark.parametrize("should_raise", [True, False])
    def test_create_without_validation_accepts_rejects(self, is_lazy, should_raise):
        app_name = self.mo_mock_app()
        author_model, book_model, chapter_model = self._make_model(app_name)
        df_dict = self.mo_mock_model_dfs(
            models=[author_model, book_model, chapter_model],
            counts=[2, 1, 1],
            is_uuid_hex=False if should_raise else True,
        )
        if is_lazy:
            df_dict = self._convert_to_lazy_dict(df_dict)

        if should_raise:
            with pytest.raises(RuntimeError):
                mo_crud_kit.create(df_dict, is_partial=False, is_validate=False)
        else:
            status, valid_dfs, invalid_dfs = mo_crud_kit.create(
                df_dict, is_partial=False, is_validate=False
            )
            if is_lazy:
                valid_dfs = mo_polars_kit.collect_model_frms(valid_dfs)
            assert status == "ok"
            assert not mo_polars_kit.is_model_frms_empty(valid_dfs)
            assert mo_polars_kit.is_model_frms_empty(invalid_dfs)
            self._assert_db_matches(valid_dfs)

    @pytest.mark.parametrize("is_lazy", [False, True])
    def test_multiple_create_boundary(self, is_lazy):
        app_name = self.mo_mock_app()
        author_model, book_model, chapter_model = self._make_model(app_name)
        df_dict_1 = self.mo_mock_model_dfs(
            models=[author_model, book_model, chapter_model],
            counts=[2, 1, 1],
        )
        df_dict_2 = self.mo_mock_model_dfs(
            models=[author_model, book_model, chapter_model],
            counts=[2, 1, 1],
        )
        if is_lazy:
            df_dict_1 = self._convert_to_lazy_dict(df_dict_1)
            df_dict_2 = self._convert_to_lazy_dict(df_dict_2)
        status_1, valid_dfs_1, invalid_dfs_1 = mo_crud_kit.create(
            df_dict_1, is_partial=False, is_validate=False
        )
        status_2, valid_dfs_2, invalid_dfs_2 = mo_crud_kit.create(
            df_dict_2, is_partial=False, is_validate=False
        )
        if is_lazy:
            valid_dfs_1 = mo_polars_kit.collect_model_frms(valid_dfs_1)
            valid_dfs_2 = mo_polars_kit.collect_model_frms(valid_dfs_2)
        assert status_1 == "ok"
        assert status_2 == "ok"
        assert not mo_polars_kit.is_model_frms_empty(valid_dfs_1)
        assert not mo_polars_kit.is_model_frms_empty(valid_dfs_2)
        assert mo_polars_kit.is_model_frms_empty(invalid_dfs_1)
        assert mo_polars_kit.is_model_frms_empty(invalid_dfs_2)
        auther_table_values = author_model.objects.all().values("id").distinct()
        author_table_list = list(auther_table_values)
        assert len(author_table_list) == 4

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
            pk_field = model._meta.pk.name
            pk_column = model._meta.pk.column
            pks = df[pk_column].to_list()
            db_rows = model.objects.filter(**{f"{pk_field}__in": pks}).values()
            db_df = pl.DataFrame(list(db_rows))
            all_db_rows = model.objects.all().values()
            all_db_df = pl.DataFrame(list(all_db_rows))
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


@pytest.mark.django_db(transaction=True)
class TestReadCrud(MindoffTestCase):

    # ----------------------------
    # VALID QUERYSET TESTS
    # ----------------------------
    @pytest.mark.parametrize("is_lazy", [False, True])
    @pytest.mark.parametrize(
        "qs_func, columns",
        [
            (
                lambda self, book: book.objects.all().values().order_by("id"),
                ["id", "title", "pages", "author_ref_id"],
            ),
            (
                lambda self, book: book.objects.annotate(
                    title_len=Count("title")
                ).values(),
                ["id", "title", "pages", "author_ref_id", "title_len"],
            ),
            (lambda self, book: book.objects.values("id", "title"), ["id", "title"]),
            (
                lambda self, book: book.objects.values(book_name=F("title")),
                ["book_name"],
            ),
            (lambda self, book: book.objects.values("pages").distinct(), ["pages"]),
            (
                lambda self, book: book.objects.annotate(count_pages=Count("pages"))
                .values("id", "count_pages", "title")
                .order_by("id"),
                ["id", "count_pages", "title"],
            ),
        ],
    )
    def test_stream_read_valid(self, is_lazy, qs_func, columns):
        _, book = self._create_data(parent_count=10)
        qs = qs_func(self, book)
        df, stats = mo_crud_kit.read(qs, batch_size=10, is_lazy=is_lazy)
        df_instance = pl.LazyFrame if is_lazy else pl.DataFrame
        assert isinstance(df, df_instance)
        df = df.collect() if is_lazy else df
        assert df.shape[0] == 20
        assert set(columns) == set(df.columns)
        for col in columns:
            assert col in df.columns, f"{col} not available in df.columns"
            if col in ("id", "author_ref_id"):
                convert_to_str = lambda row: (str(row) if row is not None else None)
                df = mo_polars_kit.frm_fill_notnull(
                    df,
                    column=col,
                    fill_value=convert_to_str,
                    row_param="row",
                    mode="map",
                    dtype=pl.Utf8,
                )
                assert_count = 10 if col == "author_ref_id" else 20
                assert (
                    df[col].n_unique() == assert_count
                ), f"Column '{col}' has duplicates"
        assert stats["mode"] == "streaming"
        assert stats["batch_size"] == 10

    @pytest.mark.parametrize("is_lazy", [False, True])
    @pytest.mark.parametrize("page_number", [1, 2])
    @pytest.mark.parametrize(
        "qs_func, columns",
        [
            (
                lambda self, book: book.objects.all().values().order_by("id"),
                ["id", "title", "pages", "author_ref_id"],
            ),
            (
                lambda self, book: book.objects.annotate(
                    title_len=Count("title")
                ).values(),
                ["id", "title", "pages", "author_ref_id", "title_len"],
            ),
            (lambda self, book: book.objects.values("id", "title"), ["id", "title"]),
            (
                lambda self, book: book.objects.values(book_name=F("title")),
                ["book_name"],
            ),
            (lambda self, book: book.objects.values("pages").distinct(), ["pages"]),
            (
                lambda self, book: book.objects.annotate(count_pages=Count("pages"))
                .values("id", "count_pages", "title")
                .order_by("id"),
                ["id", "count_pages", "title"],
            ),
        ],
    )
    def test_paginate_read_valid(self, is_lazy, page_number, qs_func, columns):
        _, book = self._create_data(parent_count=9)
        qs = qs_func(self, book)
        df, stats = mo_crud_kit.read(
            qs, page_number=page_number, batch_size=10, is_lazy=is_lazy
        )
        df_instance = pl.LazyFrame if is_lazy else pl.DataFrame
        assert isinstance(df, df_instance)
        df = df.collect() if is_lazy else df
        child_count = 10 if page_number == 1 else 8
        assert df.shape[0] == child_count
        assert set(columns) == set(df.columns)
        for col in columns:
            assert col in df.columns, f"{col} not available in df.columns"
            if col in ("id"):
                convert_to_str = lambda row: (str(row) if row is not None else None)
                df = mo_polars_kit.frm_fill_notnull(
                    df,
                    column=col,
                    fill_value=convert_to_str,
                    row_param="row",
                    mode="map",
                    dtype=pl.Utf8,
                )
                assert (
                    df[col].n_unique() == child_count
                ), f"Column '{col}' has duplicates"
        assert stats["mode"] == "pagination"
        assert stats["batch_size"] == 10
        assert stats["total_count"] == 18
        assert stats["total_pages"] == 2
        assert stats["has_previous"] == (False if page_number == 1 else True)
        assert stats["has_next"] == (True if page_number == 1 else False)

    # ----------------------------
    # INVALID / NON-QUERYSET
    # ----------------------------
    @pytest.mark.parametrize("is_lazy", [False, True])
    @pytest.mark.parametrize("page_number", [None, -1, 1, 2])
    @pytest.mark.parametrize("batch_size", [-10, 10])
    @pytest.mark.parametrize(
        "non_qs",
        [
            lambda self, book: book.objects.values_list("id", flat=True),
            lambda self, book: book.objects.aggregate(avg_pages=models.Avg("pages")),
            lambda self, book: book.objects.only("title"),
            lambda self, book: book.objects.defer("title"),
            lambda self, book: book.objects.filter(pages__in=[1]),
        ],
    )
    def test_stream_paginate_read_invalid(
        self, is_lazy, batch_size, non_qs, page_number
    ):
        _, book = self._create_data()
        obj = non_qs(self, book)
        with pytest.raises((ValidationError, TypeCheckError)):
            mo_crud_kit.read(
                obj, page_number=page_number, batch_size=batch_size, is_lazy=is_lazy
            )

    # ----------------------------
    # BOUNDARY CASES
    # ----------------------------
    @pytest.mark.parametrize("is_lazy", [False, True])
    @pytest.mark.parametrize("page_number", [1, 500, 1000])
    def test_huge_pagenumber_boundary(self, is_lazy, page_number):
        _, book = self._create_data(parent_count=1000)
        qs = book.objects.all().order_by("id").values()
        df, stats = mo_crud_kit.read(
            qs, page_number=page_number, batch_size=2, is_lazy=is_lazy
        )
        df = df.collect() if is_lazy else df
        assert df.shape[0] == 2
        assert stats["current_page"] == page_number
        if page_number == 1:
            assert stats["has_previous"] is False
            assert stats["has_next"] is True
        elif page_number == 500:
            assert stats["has_previous"] is True
            assert stats["has_next"] is True
        elif page_number == 1000:
            assert stats["has_previous"] is True
            assert stats["has_next"] is False

    @pytest.mark.parametrize("is_lazy", [False, True])
    @pytest.mark.parametrize("page_number", [None, 1])
    def test_empty_queryset_boundary(self, is_lazy, page_number):
        _, book = self._create_data(parent_count=100)
        qs = book.objects.none().values()
        df, stats = mo_crud_kit.read(qs, page_number=page_number, is_lazy=is_lazy)
        df = df.collect() if is_lazy else df
        assert mo_polars_kit.is_frm_empty(df)
        assert stats["mode"] == "pagination" if page_number else "streaming"
        assert stats["current_page"] == (page_number if page_number else 0)

    def _create_data(self, parent_count=2, child_count=2):
        """
        Create temporary models + save data.
        parent_count × child_count total rows for child model.
        """
        app_name = self.mo_mock_app()
        author_model = self.mo_mock_model(
            "AuthorModel",
            app_name=app_name,
            fields={"name": models.CharField(max_length=50)},
        )
        book_model = self.mo_mock_model(
            "BookModel",
            app_name=app_name,
            fields={
                "title": models.CharField(max_length=100),
                "pages": models.IntegerField(),
            },
            foreign_keys=[(author_model._meta.app_label, author_model.__name__)],
        )
        # Create data: parent_count × child_count
        df_dict = self.mo_mock_model_dfs(
            models=[author_model, book_model], counts=[parent_count, child_count]
        )
        mo_crud_kit.create(df_dict, is_partial=False)
        return author_model, book_model


@pytest.mark.django_db(transaction=True)
class TestUpdateCrud(MindoffTestCase):
    @pytest.mark.parametrize("is_lazy", [False, True])
    @pytest.mark.parametrize("is_temp_table", [False, True])
    @pytest.mark.parametrize(
        "case_name, remove_columns, modify_rows, model_scope, update_mode, expected_status",
        [
            # ---------------- VALID ----------------
            (
                "update_all_main",
                [],
                [],
                "main",
                "update",
                "ok",
            ),
            (
                "update_all_sub",
                [],
                [],
                "sub",
                "update",
                "ok",
            ),
            (
                "update_all_main_and_sub",
                [],
                [],
                "both",
                "update",
                "ok",
            ),
            ("update_same_values_main", [], [], "main", "update", "ok"),
            ("update_same_values_sub", [], [], "sub", "update", "ok"),
            ("update_same_values_main_and_sub", [], [], "both", "update", "ok"),
            (
                "update_partial_cols_main",
                [],
                [{0: {"nickname": "Nick"}}],
                "main",
                "update",
                "ok",
            ),
            (
                "update_partial_cols_sub",
                [],
                [{}, {0: {"edition": "First"}}],
                "sub",
                "update",
                "ok",
            ),
            (
                "update_partial_cols_both",
                [],
                [{0: {"nickname": "Nick"}}, {0: {"edition": "First"}}],
                "both",
                "update",
                "ok",
            ),
            (
                "upsert_non_existing_main",
                [],
                [{0: {"author_ref_id": str(uuid.uuid4().hex), "name": "Inserted"}}],
                "main",
                "upsert",
                "ok",
            ),
            (
                "upsert_non_existing_sub",
                [],
                [
                    {},
                    {
                        0: {
                            "book_ref_id": str(uuid.uuid4().hex),
                            "title": "Inserted Book",
                            "pages": 123,
                        }
                    },
                ],
                "sub",
                "upsert",
                "ok",
            ),
            (
                "upsert_non_existing_both",
                [],
                [
                    {
                        0: {
                            "author_ref_id": shared_uuid_author_book_relation,
                            "name": "Inserted Author",
                            "nickname": "Inserted Book",
                        }
                    },
                    {
                        0: {
                            "book_ref_id": str(uuid.uuid4().hex),
                            "edition": "Inserted Book Edition",
                            "title": "Inserted Book Title",
                            "author_ref_id": shared_uuid_author_book_relation,
                        }
                    },
                ],
                "both",
                "upsert",
                "ok",
            ),
        ],
    )
    def test_update_with_validation(
        self,
        case_name,
        remove_columns,
        modify_rows,
        model_scope,
        update_mode,
        expected_status,
        is_temp_table,
        is_lazy,
    ):
        # 1. Create app + models
        app_name = self.mo_mock_app()
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

        # 2. Create initial data (parent + child)
        df_dict = self.mo_mock_model_dfs(
            models=[author_model, book_model],
            counts=[3, 1],
        )
        if is_lazy:
            df_dict = self._convert_to_lazy_dict(df_dict)

        # 3. Ensure initial data saved
        created_status, created_valid_dfs, created_invalid_dfs = mo_crud_kit.create(
            df_dict
        )
        if is_lazy:
            created_valid_dfs = mo_polars_kit.collect_model_frms(
                created_valid_dfs, streaming=True
            )
            created_invalid_dfs = mo_polars_kit.collect_model_frms(
                created_invalid_dfs, streaming=True
            )
        assert created_status == "ok"

        # 4. Prepare update DataFrames
        update_dict = self.mo_update_mock_model_dfs(
            created_valid_dfs,
            exclude_columns=remove_columns,
            modify=modify_rows,
            counts=[3, 1, 1],
        )
        scopes = {
            "main": slice(0, 1),
            "sub": slice(1, 2),
            "both": slice(None),
        }
        update_df_list = list(update_dict.items())[scopes[model_scope]]
        update_dict = dict(update_df_list)
        if is_lazy:
            update_dict = self._convert_to_lazy_dict(update_dict)

        # 5. Run update
        if expected_status == "raise":
            with pytest.raises(ValueError):
                mo_crud_kit.update(update_dict, is_temp_table=is_temp_table)
            return
        updated_status, updated_valid_dfs, updated_invalid_dfs = mo_crud_kit.update(
            update_dict, is_temp_table=is_temp_table
        )
        if is_lazy:
            updated_valid_dfs = mo_polars_kit.collect_model_frms(
                updated_valid_dfs, streaming=True
            )
            updated_invalid_dfs = mo_polars_kit.collect_model_frms(
                updated_invalid_dfs, streaming=True
            )

        # 6. Update Assertions
        assert case_name is not None
        assert updated_status == expected_status
        for df in updated_valid_dfs.values():
            assert "__error__info" not in df.columns
        for df in updated_invalid_dfs.values():
            assert "__error__info" in df.columns
        if expected_status == "ok":
            assert not mo_polars_kit.is_model_frms_empty(updated_valid_dfs)
            assert mo_polars_kit.is_model_frms_empty(updated_invalid_dfs)
            self._assert_db_matches(updated_valid_dfs)

    @pytest.mark.parametrize("is_lazy", [False, True])
    @pytest.mark.parametrize("is_temp_table", [False, True])
    @pytest.mark.parametrize(
        "case_name, remove_columns, modify_rows, model_scope, update_mode, expected_status",
        [
            # ---------------- VALID ----------------
            (
                "update_all_main",
                [],
                [],
                "main",
                "update",
                "ok",
            ),
            (
                "update_all_sub",
                [],
                [],
                "sub",
                "update",
                "ok",
            ),
            (
                "update_all_main_and_sub",
                [],
                [],
                "both",
                "update",
                "ok",
            ),
            ("update_same_values_main", [], [], "main", "update", "ok"),
            ("update_same_values_sub", [], [], "sub", "update", "ok"),
            ("update_same_values_main_and_sub", [], [], "both", "update", "ok"),
            (
                "update_partial_cols_main",
                [],
                [{0: {"nickname": "Nick"}}],
                "main",
                "update",
                "ok",
            ),
            (
                "update_partial_cols_sub",
                [],
                [{}, {0: {"edition": "First"}}],
                "sub",
                "update",
                "ok",
            ),
            (
                "update_partial_cols_both",
                [],
                [{0: {"nickname": "Nick"}}, {0: {"edition": "First"}}],
                "both",
                "update",
                "ok",
            ),
            (
                "upsert_non_existing_main",
                [],
                [{0: {"author_ref_id": str(uuid.uuid4().hex), "name": "Inserted"}}],
                "main",
                "upsert",
                "ok",
            ),
            (
                "upsert_non_existing_sub",
                [],
                [
                    {},
                    {
                        0: {
                            "book_ref_id": str(uuid.uuid4().hex),
                            "title": "Inserted Book",
                            "pages": 123,
                        }
                    },
                ],
                "sub",
                "upsert",
                "ok",
            ),
            (
                "upsert_non_existing_both",
                [],
                [
                    {
                        0: {
                            "author_ref_id": shared_uuid_author_book_relation,
                            "name": "Inserted Author",
                            "nickname": "Inserted Book",
                        }
                    },
                    {
                        0: {
                            "book_ref_id": str(uuid.uuid4().hex),
                            "edition": "Inserted Book Edition",
                            "title": "Inserted Book Title",
                            "author_ref_id": shared_uuid_author_book_relation,
                        }
                    },
                ],
                "both",
                "upsert",
                "ok",
            ),
        ],
    )
    def test_update_without_validation(
        self,
        case_name,
        remove_columns,
        modify_rows,
        model_scope,
        update_mode,
        expected_status,
        is_temp_table,
        is_lazy,
    ):
        # 1. Create app + models
        app_name = self.mo_mock_app()
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

        # 2. Create initial data (parent + child)
        df_dict = self.mo_mock_model_dfs(
            models=[author_model, book_model],
            counts=[3, 1],
        )
        if is_lazy:
            df_dict = self._convert_to_lazy_dict(df_dict)

        # 3. Ensure initial data saved
        created_status, created_valid_dfs, created_invalid_dfs = mo_crud_kit.create(
            df_dict
        )
        if is_lazy:
            created_valid_dfs = mo_polars_kit.collect_model_frms(
                created_valid_dfs, streaming=True
            )
            created_invalid_dfs = mo_polars_kit.collect_model_frms(
                created_invalid_dfs, streaming=True
            )
        assert created_status == "ok"

        # 4. Prepare update DataFrames
        update_dict = self.mo_update_mock_model_dfs(
            created_valid_dfs,
            exclude_columns=remove_columns,
            modify=modify_rows,
            counts=[3, 1, 1],
        )
        scopes = {
            "main": slice(0, 1),
            "sub": slice(1, 2),
            "both": slice(None),
        }
        update_df_list = list(update_dict.items())[scopes[model_scope]]
        update_dict = dict(update_df_list)
        if is_lazy:
            update_dict = self._convert_to_lazy_dict(update_dict)

        # 5. Run update
        if expected_status == "raise":
            with pytest.raises(ValueError):
                mo_crud_kit.update(
                    update_dict, is_temp_table=is_temp_table, is_validate=False
                )
            return
        updated_status, updated_valid_dfs, updated_invalid_dfs = mo_crud_kit.update(
            update_dict, is_temp_table=is_temp_table, is_validate=False
        )
        if is_lazy:
            updated_valid_dfs = mo_polars_kit.collect_model_frms(
                updated_valid_dfs, streaming=True
            )
            updated_invalid_dfs = mo_polars_kit.collect_model_frms(
                updated_invalid_dfs, streaming=True
            )

        # 6. Update Assertions
        assert case_name is not None
        assert updated_status == expected_status
        for df in updated_valid_dfs.values():
            assert "__error__info" not in df.columns
        for df in updated_invalid_dfs.values():
            assert "__error__info" in df.columns
        if expected_status == "ok":
            assert not mo_polars_kit.is_model_frms_empty(updated_valid_dfs)
            assert mo_polars_kit.is_model_frms_empty(updated_invalid_dfs)
            self._assert_db_matches(updated_valid_dfs)

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
