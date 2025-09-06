import warnings
import inspect
import polars as pl
from typeguard import typechecked
from types import SimpleNamespace
from functools import partial
from django.db import models
from typing import Dict, Type, Tuple, Union, Any, Callable, Literal
from apps.django_mindoff.components.validation_kit import mo_validation_kit


@typechecked
def is_df_empty(df: pl.DataFrame | pl.LazyFrame) -> bool:
    no_columns = False
    no_rows = False
    if isinstance(df, pl.DataFrame):
        no_columns = len(df.columns) == 0
        no_rows = df.is_empty()
    elif isinstance(df, pl.LazyFrame):
        no_columns = len(df.schema) == 0
        if not no_columns:
            no_rows = df.limit(1).collect(streaming=True).height == 0
    else:
        return True
    return no_columns or no_rows


@typechecked
def is_all_dict_df_empty(
    dfs: dict[type[models.Model], pl.DataFrame | pl.LazyFrame],
) -> bool:
    return all(mo_polars_kit.is_df_empty(df) for df in dfs.values())


@typechecked
def split_df_dict_on_column(
    df_dict: Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
    column: str,
) -> Tuple[
    Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
    Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
]:
    valid_dfs, invalid_dfs = {}, {}
    for model, df in df_dict.items():
        if column not in (df.columns if isinstance(df, pl.DataFrame) else df.schema):
            df = df.with_columns(pl.lit(None).alias(column))
        valid = df.filter(pl.col(column).is_null())
        invalid = df.filter(pl.col(column).is_not_null())
        valid_dfs[model] = valid
        invalid_dfs[model] = invalid
    return valid_dfs, invalid_dfs


@typechecked
def fr_fill_null(
    fr: Union[pl.DataFrame, pl.LazyFrame],
    *,
    column: str,
    fill_value: Union[Any, Callable[..., Any]],
    mode: Literal["lit", "map", "pre-gen"],
    dtype: type | None = None,
    **custom_params: Any,
) -> Union[pl.DataFrame, pl.LazyFrame]:
    if callable(fill_value):
        loaded_func = partial(fill_value, **custom_params)
        apply_fill_value = lambda: loaded_func()
    else:
        apply_fill_value = lambda: fill_value
    if mode == "map":
        fr = fr.with_columns(
            pl.col(column)
            .map_elements(
                lambda x: apply_fill_value() if x is None else x,
                skip_nulls=False,
                return_dtype=dtype,
            )
            .alias(column)
        )

    elif mode == "pre-gen":
        fr = fr.with_row_index("__mo_temp__idx")
        null_rows = fr.filter(pl.col(column).is_null())
        null_count = (
            null_rows.select(pl.len()).collect(engine="streaming").item()
            if isinstance(fr, pl.LazyFrame)
            else null_rows.select(pl.len()).item()
        )
        not_null_rows = fr.filter(pl.col(column).is_not_null())
        null_rows = null_rows.with_columns(
            pl.Series(column, [apply_fill_value() for _ in range(null_count)])
        )
        fr = (
            pl.concat([null_rows, not_null_rows])
            .sort("__mo_temp__idx")
            .drop("__mo_temp__idx")
        )

    elif mode == "lit":
        fr = fr.with_columns(
            pl.col(column)
            .fill_null(pl.lit(apply_fill_value(), allow_object=True))
            .alias(column)
        )

    return fr


@typechecked
def fr_fill_notnull(
    fr: Union[pl.DataFrame, pl.LazyFrame],
    *,
    column: str,
    fill_value: Union[Any, Callable[..., Any]],
    mode: Literal["lit", "map", "pre-gen"],
    row_param: str | None = None,
    dtype: type | None = None,
    **custom_params: Any,
) -> Union[pl.DataFrame, pl.LazyFrame]:
    mo_validation_kit.ensure(
        lambda: not row_param or mode == "map",
        msg="'row_param' can only be used with mode='map'",
        is_exception=True,
    )
    if callable(fill_value):
        loaded_func = partial(fill_value, **custom_params)
        if row_param:
            apply_fill_value = lambda x: loaded_func(**{row_param: x})
        else:
            apply_fill_value = lambda _: loaded_func()
    else:
        apply_fill_value = lambda: fill_value
    if mode == "map":
        fr = fr.with_columns(
            pl.col(column)
            .map_elements(
                lambda x: apply_fill_value(x) if x is not None else x,
                skip_nulls=True,
                return_dtype=dtype,
            )
            .alias(column)
        )

    elif mode == "pre-gen":
        fr = fr.with_row_index("__mo_temp__idx")
        not_null_rows = fr.filter(pl.col(column).is_not_null())
        not_null_count = (
            not_null_rows.select(pl.len()).collect(engine="streaming").item()
            if isinstance(fr, pl.LazyFrame)
            else not_null_rows.select(pl.len()).item()
        )
        null_rows = fr.filter(pl.col(column).is_null())
        not_null_rows = not_null_rows.with_columns(
            pl.Series(column, [apply_fill_value() for _ in range(not_null_count)])
        )
        fr = (
            pl.concat([null_rows, not_null_rows])
            .sort("__mo_temp__idx")
            .drop("__mo_temp__idx")
        )

    elif mode == "lit":
        fr = fr.with_columns(
            pl.when(pl.col(column).is_not_null())
            .then(pl.lit(apply_fill_value(), allow_object=True))
            .otherwise(pl.col(column))
            .alias(column)
        )

    return fr


mo_polars_kit = SimpleNamespace(
    is_df_empty=is_df_empty,
    is_all_dict_df_empty=is_all_dict_df_empty,
    split_df_dict_on_column=split_df_dict_on_column,
    fr_fill_null=fr_fill_null,
    fr_fill_notnull=fr_fill_notnull,
)
