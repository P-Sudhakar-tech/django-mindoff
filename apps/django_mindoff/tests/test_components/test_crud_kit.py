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
from django.db import models
from model_bakery import baker
from apps.django_mindoff.components.helpers.tdd_fixtures import MindoffTestCase
from apps.django_mindoff.components.crud_kit import mo_crud_kit


@pytest.mark.django_db(transaction=True)
class TestColumnValidationCrud(MindoffTestCase):
    @pytest.mark.parametrize(
        "case_name, remove_columns, modify_rows, is_partial, expected_status",
        [
            # ---------------- Column Validation ----------------
            ("col_exact_accepts", [], [], True, "ok"),
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
            (
                "col_missing_required_rejects",
                [["name"], ["title"], ["title"]],
                [],
                False,
                "fail",
            ),
            # ---------------- Row Validation ----------------
            ("row_valid_accepts", [], [], True, "ok"),
            ("row_valid_accepts", [], [], False, "ok"),
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
                [{0: {"pages": "abc", "title": None}}],
                True,
                "partial_ok",
            ),
            (
                "row_partial_last_child_rejects",
                [],
                [{0: {"order": "first", "title": None}}],
                True,
                "partial_ok",
            ),
            (
                "row_all_rejects",
                [],
                [
                    {0: {"name": None}},
                    {0: {"title": None, "pages": "bad"}},
                    {0: {"title": None, "order": None, "book_id": None}},
                ],
                False,
                "fail",
            ),
            # ---------------- Foreign Key Validation ----------------
            ("fk_valid_accepts", [], [], True, "ok"),
            ("fk_valid_accepts", [], [], False, "ok"),
            (
                "fk_invalid_partial_rejects",
                [],
                [{0: {"author_id": 999}}],
                True,
                "partial_ok",
            ),
            (
                "fk_invalid_all_rejects",
                [],
                [
                    {0: {"author_id": 999}},
                    {0: {"book_id": 999}},
                ],
                False,
                "fail",
            ),
        ],
    )
    def test_validation_cases(
        self, case_name, remove_columns, modify_rows, is_partial, expected_status
    ):
        app_name = self.init_temp_app()
        author_model = self.init_temp_model(
            model_name="AuthorModel",
            app_name=app_name,
            fields={
                "name": models.CharField(max_length=50),
            },
        )

        book_model = self.init_temp_model(
            model_name="BookModel",
            app_name=app_name,
            fields={
                "title": models.CharField(max_length=100),
                "pages": models.IntegerField(),
            },
            foreign_keys=[(author_model._meta.app_label, author_model.__name__)],
        )

        chapter_model = self.init_temp_model(
            model_name="ChapterModel",
            app_name=app_name,
            fields={
                "title": models.CharField(max_length=100),
                "order": models.IntegerField(),
            },
            foreign_keys=[
                (author_model._meta.app_label, author_model.__name__),
                (book_model._meta.app_label, book_model.__name__),
            ],
        )
        df_dict = self.generate_model_dfs(
            models=[author_model, book_model, chapter_model],
            exclude_columns=remove_columns,
            modify=modify_rows,
            counts=[2, 1, 1],
        )
        print(df_dict)
        assert True == False
        # run your validator logic here and assert expected_status
        # result = run_validation(df_dict, partial=is_partial)
        # status, _, _ = mo_crud_kit.create(df_dict, is_partial=is_partial)
        # assert result.status == expected_status
