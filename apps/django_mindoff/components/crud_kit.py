"""
1. mo_crud_kit.create(model_df_dict, is_partial)
2. mo_crud_kit.update(model_df_dict, is_partial)
3. mo_crud_kit.delete(list_of_ids, is_partial)
4. mo_crud_kit.read(model, filter_conditions, columns, is_streaming)
"""

from typing import Dict, Tuple, Type, Union, List
from typeguard import typechecked
import polars as pl
from django.db import models
from types import SimpleNamespace
from .response_kit import mo_response_kit
from ._crud_kit.column_validator import ColumnValidator
from ._crud_kit.row_validator import RowValidator
from ._crud_kit.foreign_key_validator import ForeignKeyValidator
from ._crud_kit.crud_processor import CRUDProcessor
from .polars_kit import mo_polars_kit

ERROR_COL = "__error__info"


# --------------
# Classes
# --------------
@typechecked
class _DfDictValidInvalidSplitter:
    """
    ⚠️ INTERNAL CLASS
    Cascade-splits a dict of DataFrames/LazyFrames into valid and invalid sets
    based on `ERROR_COL` and relational dependencies (FK/OneToOne).
    """

    def __init__(
        self, df_dict: Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]]
    ):
        self.df_dict = self._normalize_dfs(df_dict)
        self.relations = self._build_relations(list(self.df_dict.keys()))

    def run(self) -> Tuple[
        Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
        Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
    ]:
        invalid_ids = self._collect_initial_invalid_ids()
        invalid_ids = self._propagate_invalid_ids(invalid_ids)
        return self._split_valid_invalid(invalid_ids)

    def _normalize_dfs(self, df_dict):
        """Ensure all DataFrames have __error__info column."""
        normalized = {}
        for model, df in df_dict.items():
            if ERROR_COL not in df.schema:
                df = df.with_columns(pl.lit(None).alias(ERROR_COL))
            normalized[model] = df
        return normalized

    def _build_relations(self, models_list: List[Type[models.Model]]):
        """Extract (child, fk_col, parent, pk_col) for FK/OneToOne relations."""
        relations = []
        for model in models_list:
            for f in model._meta.concrete_fields:
                if isinstance(f, (models.ForeignKey, models.OneToOneField)):
                    relations.append(
                        (
                            model,
                            f.db_column or f.name,
                            f.related_model,
                            f.related_model._meta.pk.db_column
                            or f.related_model._meta.pk.name,
                        )
                    )
        return relations

    def _collect_initial_invalid_ids(self):
        """Collect initial invalid IDs from rows with non-null __error__info."""
        return {
            m: df.filter(pl.col(ERROR_COL).is_not_null())
            .select(pl.col(m._meta.pk.db_column or m._meta.pk.name))
            .unique()
            for m, df in self.df_dict.items()
        }

    def _propagate_invalid_ids(self, invalid_ids):
        """Cascade invalid IDs across parent-child relations."""
        queue = [
            m for m, ids in invalid_ids.items() if not mo_polars_kit.is_df_empty(ids)
        ]
        visited = set()

        while queue:
            m = queue.pop()
            if m in visited:
                continue
            visited.add(m)

            for child, fk_col, parent, pk_col in self.relations:
                if m == child:
                    queue += self._propagate_to_parent(
                        invalid_ids, child, parent, fk_col, pk_col
                    )
                elif m == parent:
                    queue += self._propagate_to_child(
                        invalid_ids, child, parent, fk_col, pk_col
                    )

        return invalid_ids

    def _propagate_to_parent(self, invalid_ids, child, parent, fk_col, pk_col):
        """Mark parent IDs invalid if child rows are invalid."""
        new_invalid = (
            self.df_dict[child]
            .join(
                invalid_ids[child],
                on=child._meta.pk.db_column or child._meta.pk.name,
                how="inner",
            )
            .select(pl.col(fk_col).alias(pk_col))
            .unique()
        )
        before_empty = mo_polars_kit.is_df_empty(invalid_ids[parent])
        invalid_ids[parent] = invalid_ids[parent].vstack(new_invalid).unique()
        return (
            [parent]
            if not before_empty and not mo_polars_kit.is_df_empty(new_invalid)
            else []
        )

    def _propagate_to_child(self, invalid_ids, child, parent, fk_col, pk_col):
        """Mark child IDs invalid if parent rows are invalid."""
        new_invalid = (
            self.df_dict[child]
            .join(invalid_ids[parent], left_on=fk_col, right_on=pk_col, how="inner")
            .select(pl.col(child._meta.pk.db_column or child._meta.pk.name))
            .unique()
        )

        before_empty = mo_polars_kit.is_df_empty(invalid_ids[child])
        invalid_ids[child] = invalid_ids[child].vstack(new_invalid).unique()
        return (
            [child]
            if not before_empty and not mo_polars_kit.is_df_empty(new_invalid)
            else []
        )

    def _split_valid_invalid(self, invalid_ids):
        """Split into valid and invalid dfs based on invalid IDs."""
        valid_dfs, invalid_dfs = {}, {}
        for m, df in self.df_dict.items():
            pk = m._meta.pk.db_column or m._meta.pk.name
            bad_ids = invalid_ids[m]
            if mo_polars_kit.is_df_empty(bad_ids):
                valid_dfs[m] = df
                invalid_dfs[m] = df.filter(
                    pl.lit(False)
                )  # empty frame with same schema
            else:
                df_invalid = df.join(bad_ids, on=pk, how="inner")
                df_valid = df.join(bad_ids, on=pk, how="anti")
                valid_dfs[m], invalid_dfs[m] = df_valid, df_invalid

        return valid_dfs, invalid_dfs


# --------------
# Functions
# --------------
@mo_response_kit.response_guardian
@typechecked
def validate_and_create(
    df_dict: Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
    is_partial: bool = False,
) -> Tuple[str, Dict, Dict]:
    """
    Validate and create model instances from DataFrames.

    Returns:
        status: "ok", "fail", or "partial_ok"
        valid_dfs: dict of models with validated DataFrames
        invalid_dfs: dict of models with invalid DataFrames
    """
    # Step 1: Column validation
    column_validator = ColumnValidator(
        df_dict=df_dict,
        is_remove_extra_columns=True,
        is_add_missing_columns=True,
    )
    valid_dfs, invalid_dfs = column_validator.run()
    if not mo_polars_kit.is_all_dict_df_empty(invalid_dfs):
        return "fail", valid_dfs, invalid_dfs

    # Step 2: Row validation
    row_validator = RowValidator(valid_dfs)
    row_validated_dfs = row_validator.run()

    # Step 3: Foreign key validation
    fk_validator = ForeignKeyValidator(row_validated_dfs)
    fk_validated_dfs = fk_validator.validate()
    df_dict_valid_invalid_splitter = _DfDictValidInvalidSplitter(fk_validated_dfs)
    valid_dfs, invalid_dfs = df_dict_valid_invalid_splitter.run()

    # Step 4: Decide partial save
    if mo_polars_kit.is_all_dict_df_empty(valid_dfs):
        return "fail", valid_dfs, invalid_dfs
    if not mo_polars_kit.is_all_dict_df_empty(invalid_dfs):
        if not is_partial:
            return "fail", valid_dfs, invalid_dfs
        status = "partial_ok"
    else:
        status = "ok"

    # Step 5: Perform CRUD operation
    crud_processor = CRUDProcessor(valid_dfs)
    crud_processor.create()
    return status, valid_dfs, invalid_dfs


mo_crud_kit = SimpleNamespace(
    validate_and_create=validate_and_create,
)
