from functools import partial
from types import SimpleNamespace
from typing import List, Any, Callable, Dict, Literal, Tuple, Type, Union

import polars as pl
from django.db import models
from typeguard import typechecked

from .validation_kit import mo_validation_kit
from ._polars_kit.json_to_frame import json_to_frame, build_model_frms


@typechecked
def is_frm_empty(frm: pl.DataFrame | pl.LazyFrame) -> bool:
    if isinstance(frm, pl.DataFrame):
        return frm.is_empty()
    if not frm.collect_schema():
        return True
    return frm.limit(1).collect().is_empty()


@typechecked
def is_model_frms_empty(
    dfs: dict[type[models.Model], pl.DataFrame | pl.LazyFrame],
) -> bool:
    return all(mo_polars_kit.is_frm_empty(df) for df in dfs.values())


@typechecked
def is_model_frms_not_empty(
    dfs: dict[type[models.Model], pl.DataFrame | pl.LazyFrame],
) -> bool:
    return any(not mo_polars_kit.is_frm_empty(df) for df in dfs.values())


@typechecked
def has_nulls_in_frm_col(frm: pl.DataFrame | pl.LazyFrame, column: str) -> bool:
    if isinstance(frm, pl.DataFrame):
        return frm[column].null_count() > 0
    return frm.select(pl.col(column).is_null().any()).collect().item()


@typechecked
def split_model_frms_on_null(
    df_dict: dict[type[models.Model], pl.DataFrame | pl.LazyFrame],
    column: str = "__error__info",
) -> tuple[
    dict[type[models.Model], pl.DataFrame | pl.LazyFrame],
    dict[type[models.Model], pl.DataFrame | pl.LazyFrame],
]:
    valid_dfs, invalid_dfs = {}, {}
    for model, df in df_dict.items():
        schema = df.schema
        work_df = df
        if column not in schema:
            work_df = df.with_columns(pl.lit(None, dtype=pl.String).alias(column))
        valid_dfs[model] = work_df.filter(pl.col(column).is_null())
        invalid_dfs[model] = work_df.filter(pl.col(column).is_not_null())
    return valid_dfs, invalid_dfs


@typechecked
def frm_fill_null(
    fr: pl.DataFrame | pl.LazyFrame,
    *,
    column: str,
    fill_value: Any | Callable[..., Any],
    mode: Literal["lit", "map"],
    dtype: pl.DataType | None = None,
    **custom_params: Any,
) -> pl.DataFrame | pl.LazyFrame:
    if mode == "lit":
        value = fill_value(**custom_params) if callable(fill_value) else fill_value
        return fr.with_columns(
            pl.col(column).fill_null(pl.lit(value, dtype=dtype)).alias(column)
        )
    mo_validation_kit.ensure_truthy(
        callable(fill_value),
        msg="fill_value must be callable when mode='map'",
        is_exception=True,
    )
    loaded_func = partial(fill_value, **custom_params)
    target_dtype = dtype or fr.schema.get(column) or pl.String

    def _batch_fill(s: pl.Series) -> pl.Series:
        if s.null_count() == 0:
            return s
        data = s.to_list()
        for i, v in enumerate(data):
            if v is None:
                data[i] = loaded_func()
        return pl.Series(s.name, data, dtype=target_dtype)

    return fr.with_columns(
        pl.col(column).map_batches(_batch_fill, return_dtype=target_dtype).alias(column)
    )


@typechecked
def frm_fill_notnull(
    fr: pl.DataFrame | pl.LazyFrame,
    *,
    column: str,
    fill_value: Any | Callable[..., Any],
    mode: Literal["lit", "map"],
    row_param: str | None = None,
    dtype: pl.DataType | None = None,
    **custom_params: Any,
) -> pl.DataFrame | pl.LazyFrame:
    mo_validation_kit.ensure(
        lambda: not row_param or mode == "map",
        msg="'row_param' can only be used with mode='map'",
        is_exception=True,
    )
    if mode == "lit":
        value = fill_value(**custom_params) if callable(fill_value) else fill_value
        return fr.with_columns(
            pl.when(pl.col(column).is_not_null())
            .then(pl.lit(value, dtype=dtype))
            .otherwise(pl.col(column))
            .alias(column)
        )
    mo_validation_kit.ensure_truthy(
        callable(fill_value),
        msg="fill_value must be callable when mode='map'",
        is_exception=True,
    )
    loaded_func = partial(fill_value, **custom_params)
    target_dtype = dtype or fr.schema.get(column) or pl.String

    def _batch_fill(s: pl.Series) -> pl.Series:
        if s.null_count() == s.len():
            return s
        data = s.to_list()
        if row_param:
            for i, v in enumerate(data):
                if v is not None:
                    data[i] = loaded_func(**{row_param: v})
        else:
            for i, v in enumerate(data):
                if v is not None:
                    data[i] = loaded_func()
        return pl.Series(s.name, data, dtype=target_dtype)

    return fr.with_columns(
        pl.col(column).map_batches(_batch_fill, return_dtype=target_dtype).alias(column)
    )


@typechecked
def get_frm_height(frm: Union[pl.DataFrame, pl.LazyFrame]) -> int:
    if isinstance(frm, pl.LazyFrame):
        return frm.select(pl.count()).collect(engine="streaming").item()
    else:
        return frm.height


@typechecked
def collect_model_frms(
    df_dict: Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
    streaming: bool = True,
) -> Dict[Type[models.Model], pl.DataFrame]:
    collected_model_frms = {}
    for model, df in df_dict.items():
        if isinstance(df, pl.LazyFrame):
            collected_model_frms[model] = df.collect(streaming=streaming)
        elif isinstance(df, pl.DataFrame):
            collected_model_frms[model] = df
    return collected_model_frms


@typechecked
def sync_model_frms_type(
    model_frms: dict[type[models.Model], pl.DataFrame | pl.LazyFrame],
) -> dict[type[models.Model], pl.DataFrame | pl.LazyFrame]:
    any_lazy = any(isinstance(v, pl.LazyFrame) for v in model_frms.values())
    if not any_lazy:
        return model_frms
    synced_model_frms = {}
    for k, v in model_frms.items():
        if isinstance(v, pl.DataFrame):
            synced_model_frms[k] = v.lazy()
        else:
            synced_model_frms[k] = v
    return synced_model_frms


@typechecked
def join_model_frms(
    target: Dict[Type[models.Model], pl.DataFrame],
    source: Dict[Type[models.Model], pl.DataFrame],
    *,
    on: str,
    add: list[str],
) -> Dict[Type[models.Model], pl.DataFrame]:

    merged_results: Dict[Type[models.Model], pl.DataFrame] = {}
    for model, original_df in target.items():
        incoming_df = source.get(model)
        if incoming_df is None or incoming_df.is_empty():
            continue
        if on not in original_df.columns:
            raise ValueError(f"{on} not found in target for {model.__name__}")
        if on not in incoming_df.columns:
            raise ValueError(f"{on} not found in source for {model.__name__}")
        for col in add:
            if col not in incoming_df.columns:
                raise ValueError(f"{col} not found in source for {model.__name__}")
        incoming_subset = incoming_df.select([on, *add])
        merged = original_df.join(
            incoming_subset,
            on=on,
            how="left",
        )
        merged_results[model] = merged
    return merged_results


mo_polars_kit = SimpleNamespace(
    is_frm_empty=is_frm_empty,
    is_model_frms_empty=is_model_frms_empty,
    is_model_frms_not_empty=is_model_frms_not_empty,
    has_nulls_in_frm_col=has_nulls_in_frm_col,
    split_model_frms_on_null=split_model_frms_on_null,
    frm_fill_null=frm_fill_null,
    frm_fill_notnull=frm_fill_notnull,
    get_frm_height=get_frm_height,
    collect_model_frms=collect_model_frms,
    sync_model_frms_type=sync_model_frms_type,
    json_to_frame=json_to_frame,
    build_model_frms=build_model_frms,
    join_model_frms=join_model_frms,
)

# ------------- HELPER FUNCTIONS --------------------
