"""
1. mo_crud_kit.create(model_frm_dict, is_partial)
2. mo_crud_kit.update(model_frm_dict, is_partial)
3. mo_crud_kit.delete(list_of_ids, is_partial)
4. mo_crud_kit.read(model, filter_conditions, columns, is_streaming)
"""

import warnings
import polars as pl
from itertools import islice
from typing import Dict, Tuple, Type, Union, List, Literal, Any
from typeguard import typechecked
from django.db import models
from django.db import connection
from django.db.utils import NotSupportedError
from django.core.paginator import Paginator, EmptyPage
from types import SimpleNamespace
from .response_kit import mo_response_kit
from .validation_kit import mo_validation_kit
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
class _ModelFrmsValidInvalidSplitter:
    """
    ⚠️ INTERNAL CLASS
    Cascade-splits a dict of DataFrames/LazyFrames into valid and invalid sets
    based on `ERROR_COL` and relational dependencies (FK/OneToOne).
    """

    def __init__(
        self, model_frms: Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]]
    ):
        self.model_frms = self._normalize_frms(model_frms)
        self.relations = self._build_relations(list(self.model_frms.keys()))

    def run(self) -> Tuple[
        Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
        Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
    ]:
        invalid_ids = self._collect_initial_invalid_ids()
        invalid_ids = self._propagate_invalid_ids(invalid_ids)
        return self._split_valid_invalid(invalid_ids)

    def _normalize_frms(self, model_frms):
        """Ensure all DataFrames have __error__info column."""
        normalized = {}
        for model, frm in model_frms.items():
            frm_schema = (
                frm.collect_schema() if isinstance(frm, pl.LazyFrame) else frm.schema
            )
            if ERROR_COL not in frm_schema:
                frm = frm.with_columns(pl.lit(None).alias(ERROR_COL))
            normalized[model] = frm
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
            m: frm.filter(pl.col(ERROR_COL).is_not_null())
            .select(pl.col(m._meta.pk.db_column or m._meta.pk.name))
            .unique()
            for m, frm in self.model_frms.items()
        }

    def _propagate_invalid_ids(self, invalid_ids):
        """Cascade invalid IDs across parent-child relations."""
        queue = [
            m for m, ids in invalid_ids.items() if not mo_polars_kit.is_frm_empty(ids)
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
            self.model_frms[child]
            .join(
                invalid_ids[child],
                on=child._meta.pk.db_column or child._meta.pk.name,
                how="inner",
            )
            .select(pl.col(fk_col).alias(pk_col))
            .unique()
        )
        before_empty = mo_polars_kit.is_frm_empty(invalid_ids[parent])
        invalid_ids[parent] = pl.concat([invalid_ids[parent], new_invalid]).unique()
        return (
            [parent]
            if not before_empty and not mo_polars_kit.is_frm_empty(new_invalid)
            else []
        )

    def _propagate_to_child(self, invalid_ids, child, parent, fk_col, pk_col):
        """Mark child IDs invalid if parent rows are invalid."""
        new_invalid = (
            self.model_frms[child]
            .join(invalid_ids[parent], left_on=fk_col, right_on=pk_col, how="inner")
            .select(pl.col(child._meta.pk.db_column or child._meta.pk.name))
            .unique()
        )

        before_empty = mo_polars_kit.is_frm_empty(invalid_ids[child])
        invalid_ids[child] = pl.concat([invalid_ids[child], new_invalid]).unique()
        return (
            [child]
            if not before_empty and not mo_polars_kit.is_frm_empty(new_invalid)
            else []
        )

    def _split_valid_invalid(self, invalid_ids):
        """Split into valid and invalid frms based on invalid IDs."""
        valid_model_frms, invalid_model_frms = {}, {}
        for m, frm in self.model_frms.items():
            pk = m._meta.pk.db_column or m._meta.pk.name
            bad_ids = invalid_ids[m]
            if mo_polars_kit.is_frm_empty(bad_ids):
                valid_model_frms[m] = frm.drop(ERROR_COL)
                invalid_model_frms[m] = frm.filter(pl.lit(False))
            else:
                frm_invalid = frm.join(bad_ids, on=pk, how="inner")
                frm_valid = frm.join(bad_ids, on=pk, how="anti").drop(ERROR_COL)
                valid_model_frms[m], invalid_model_frms[m] = frm_valid, frm_invalid

        return valid_model_frms, invalid_model_frms


# --------------
# Functions
# --------------
@typechecked
def create(
    model_frms: Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
    is_partial: bool = False,
    is_validate: bool = True,
    batch_size: int = 1000,
) -> Tuple[str, Dict, Dict]:
    model_frms = mo_polars_kit.sync_model_frms_type(model_frms)
    if is_validate:
        # Step 1: Column validation
        column_validator = ColumnValidator(
            model_frms=model_frms,
            is_remove_extra_columns=True,
            is_add_missing_columns=True,
        )
        valid_model_frms, invalid_model_frms = column_validator.run()
        if not mo_polars_kit.is_model_frms_empty(invalid_model_frms):
            return "fail", valid_model_frms, invalid_model_frms

        # Step 2: Row validation
        row_validator = RowValidator(valid_model_frms)
        row_validated_frms = row_validator.run()

        # Step 3: Foreign key validation
        fk_validator = ForeignKeyValidator(row_validated_frms)
        fk_validated_frms = fk_validator.validate()
        frm_dict_valid_invalid_splitter = _ModelFrmsValidInvalidSplitter(
            fk_validated_frms
        )
        valid_model_frms, invalid_model_frms = frm_dict_valid_invalid_splitter.run()

        # Step 4: Decide partial save
        if mo_polars_kit.is_model_frms_empty(valid_model_frms):
            return "fail", valid_model_frms, invalid_model_frms
        if not mo_polars_kit.is_model_frms_empty(invalid_model_frms):
            if not is_partial:
                return "fail", valid_model_frms, invalid_model_frms
            status = "partial_ok"
        else:
            status = "ok"
    else:
        warnings.warn(
            "Saving without validation may store unsafe or inconsistent data, "
            "which can affect mindoff's read/update/delete functions. "
            "Proceed only if intentional.",
            RuntimeWarning,
        )
        status = "ok"
        valid_model_frms, invalid_model_frms = model_frms, {}

    # Step 5: Perform CRUD operation
    crud_processor = CRUDProcessor(valid_model_frms)
    _ = crud_processor.create(batch_size=batch_size)
    return status, valid_model_frms, invalid_model_frms


@typechecked
def read(
    qs: models.QuerySet,
    *,
    page_number: int | None = None,
    is_lazy: bool = False,
    batch_size: int = 0,
) -> tuple[pl.DataFrame | pl.LazyFrame, dict[str, Any]]:
    # 1. Validate and Normalize
    mo_validation_kit.ensure(
        issubclass(qs._iterable_class, models.query.ValuesIterable),
        msg=f"Unsupported queryset type `{qs._iterable_class.__name__}`. "
        "You must call `.values()` on the queryset before passing it to `read()`.",
        is_exception=True,
    )
    mo_validation_kit.ensure_greater_equal(
        batch_size,
        0,
        msg=f"The 'batch_size' parameter must be a positive integer. Provided value: {batch_size}",
        is_exception=True,
    )
    if batch_size == 0:
        batch_size = 100 if page_number else 1000

    # 2. Empty Queryset
    if not qs.exists():
        df = pl.DataFrame([]).lazy() if is_lazy else pl.DataFrame([])
        stats = _read__build_stats(
            mode="pagination" if page_number else "streaming",
            batch_size=batch_size,
            total_count=0,
            total_pages=0,
            current_page=page_number if page_number else 0,
            has_next=False,
            has_previous=False,
        )
        return df, stats

    # 3. Streaming mode
    if not page_number:
        df = pl.concat(_read__batched_iterator(qs, batch_size, is_lazy), rechunk=False)
        stats = _read__build_stats(
            mode="streaming",
            batch_size=batch_size,
            total_count=qs.count(),
            total_pages=0,
            current_page=0,
            has_next=False,
            has_previous=False,
        )
        return df, stats

    # 4. Pagination mode
    paginator = Paginator(qs, batch_size)
    try:
        page = paginator.page(page_number)
        df = pl.DataFrame(list(page)).lazy() if is_lazy else pl.DataFrame(list(page))
        stats = _read__build_stats(
            mode="pagination",
            batch_size=batch_size,
            total_count=paginator.count,
            total_pages=paginator.num_pages,
            current_page=page.number,
            has_next=page.has_next(),
            has_previous=page.has_previous(),
        )
    except EmptyPage:
        df = pl.DataFrame([]).lazy() if is_lazy else pl.DataFrame([])
        stats = _read__build_stats(
            mode="pagination",
            batch_size=batch_size,
            total_count=paginator.count,
            total_pages=paginator.num_pages,
            current_page=page_number,
            has_next=False,
            has_previous=page_number > 1,
        )

    return df, stats


@typechecked
def update(
    model_frms: Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
    is_partial: bool = False,
    is_validate: bool = True,
    batch_size: int = 1000,
    is_temp_table: bool = True,
):
    model_frms = _update__fill_missing_columns(model_frms, batch_size=batch_size)

    if is_validate:
        # Step 1: Column validation
        column_validator = ColumnValidator(
            model_frms=model_frms,
            is_remove_extra_columns=True,
            is_add_missing_columns=True,
        )
        valid_model_frms, invalid_model_frms = column_validator.run()
        if not mo_polars_kit.is_model_frms_empty(invalid_model_frms):
            return "fail", valid_model_frms, invalid_model_frms

        # Step 2: Row validation
        row_validator = RowValidator(valid_model_frms)
        row_validated_frms = row_validator.run()

        # Step 3: Foreign key validation
        fk_validator = ForeignKeyValidator(row_validated_frms)
        fk_validated_frms = fk_validator.validate()
        frm_dict_valid_invalid_splitter = _ModelFrmsValidInvalidSplitter(
            fk_validated_frms
        )
        valid_model_frms, invalid_model_frms = frm_dict_valid_invalid_splitter.run()

        # Step 4: Decide partial save
        if mo_polars_kit.is_model_frms_empty(valid_model_frms):
            return "fail", valid_model_frms, invalid_model_frms
        if not mo_polars_kit.is_model_frms_empty(invalid_model_frms):
            if not is_partial:
                return "fail", valid_model_frms, invalid_model_frms
            status = "partial_ok"
        else:
            status = "ok"
    else:
        warnings.warn(
            "Updating without validation may store unsafe or inconsistent data, "
            "which can affect mindoff's read/update/delete functions. "
            "Proceed only if intentional.",
            RuntimeWarning,
        )
        status = "ok"
        valid_model_frms, invalid_model_frms = model_frms, {}

    # Step 5: Perform CRUD operation
    crud_processor = CRUDProcessor(valid_model_frms)
    _ = crud_processor.update(is_temp_table=is_temp_table, batch_size=batch_size)
    return status, valid_model_frms, invalid_model_frms


mo_crud_kit = SimpleNamespace(create=create, read=read, update=update)


def _read__batched_iterator(qs: models.QuerySet, size: int, is_lazy: bool):
    it = qs.iterator(chunk_size=size)
    while True:
        batch = list(islice(it, size))
        if not batch:
            break
        yield pl.DataFrame(batch).lazy() if is_lazy else pl.DataFrame(batch)


def _read__build_stats(
    *,
    mode: str,
    batch_size: int,
    total_count: int,
    total_pages: int | None,
    current_page: int | None,
    has_next: bool,
    has_previous: bool,
) -> dict[str, Any]:
    """Return a consistent stats dictionary."""
    return {
        "mode": mode,
        "batch_size": batch_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": current_page,
        "has_next": has_next,
        "has_previous": has_previous,
    }


def _update__fill_missing_columns(
    model_frms: Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
    *,
    batch_size: int,
) -> Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]]:
    updated_model_frames = {}

    for model_cls, df in model_frms.items():
        # 1. Find Missing Columns and primary key
        df_cols = set(df.columns)
        model_fields = {f.column or f.name for f in model_cls._meta.concrete_fields}
        missing_cols = list(model_fields - df_cols)
        pk_name = model_cls._meta.pk.name
        pk_column = model_cls._meta.pk.column

        pk_field = next((c for c in (pk_column, pk_name) if c in df_cols), None)
        mo_validation_kit.ensure_truthy(
            pk_field,
            msg=f"Primary key {pk_field} must exist in DataFrame to fetch missing columns.",
            is_exception=True,
        )
        if pk_field in missing_cols:
            missing_cols.remove(pk_field)
        if not missing_cols:
            updated_model_frames[model_cls] = df
            continue

        # 2. Generate Missing Frame
        schema = {pk_field: df.schema[pk_field], **dict.fromkeys(missing_cols, None)}
        base_missing_df = (
            pl.LazyFrame(schema=schema)
            if isinstance(df, pl.LazyFrame)
            else pl.DataFrame(schema=schema)
        )
        missing_df = __update__fetch_missing_chunks(
            model_cls, df, pk_field, missing_cols, batch_size, base_missing_df
        )

        # 3. Cut off if no missing data to Merge
        if mo_polars_kit.is_frm_empty(missing_df):
            for col in missing_cols:
                df = df.with_columns(pl.lit(None).alias(col))
            updated_model_frames[model_cls] = df
            continue

        # 4. Check again and Final merge
        overlap = set(df.columns) & set(missing_df.columns) - {pk_field}
        mo_validation_kit.ensure_falsey(
            overlap,
            msg=f"Duplicate columns found during merge for model {model_cls.__name__}: {', '.join(overlap)}",
            is_exception=True,
        )
        df = df.join(missing_df, on=pk_field, how="left")
        updated_model_frames[model_cls] = df

    return updated_model_frames


def __update__fetch_missing_chunks(
    model_cls,
    df,
    pk_field: str,
    missing_cols: list[str],
    batch_size: int,
    base_missing_df,
):
    pk_series = df.select(pk_field) if isinstance(df, pl.LazyFrame) else df[pk_field]
    missing_df = base_missing_df
    for chunk in pk_series.iter_slices(n_rows=batch_size):
        pk_chunk = chunk.to_list()
        qs = model_cls.objects.filter(**{f"{pk_field}__in": pk_chunk}).values(
            pk_field, *missing_cols
        )
        chunk_df, _ = read(
            qs, is_lazy=isinstance(df, pl.LazyFrame), batch_size=batch_size
        )
        if not mo_polars_kit.is_frm_empty(chunk_df):
            missing_df = pl.concat([missing_df, chunk_df], rechunk=False)
    return missing_df
