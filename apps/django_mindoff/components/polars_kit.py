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
def is_frm_empty(frm: pl.DataFrame | pl.LazyFrame) -> bool:
    no_columns = False
    no_rows = False
    if isinstance(frm, pl.DataFrame):
        no_columns = len(frm.columns) == 0
        no_rows = frm.is_empty()
    elif isinstance(frm, pl.LazyFrame):
        no_columns = len(frm.collect_schema()) == 0
        if not no_columns:
            no_rows = frm.limit(1).collect(engine="streaming").height == 0
    else:
        return True
    return no_columns or no_rows


@typechecked
def is_model_frms_empty(
    dfs: dict[type[models.Model], pl.DataFrame | pl.LazyFrame],
) -> bool:
    return all(mo_polars_kit.is_frm_empty(df) for df in dfs.values())


@typechecked
def has_nulls_in_frm_col(frm: pl.DataFrame | pl.LazyFrame, column: str) -> bool:
    expr = pl.col(column).is_null().any()
    if isinstance(frm, pl.DataFrame):
        return frm.select(expr).item()
    else:
        return frm.select(expr).collect(engine="streaming").item()


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
        if column not in (
            df.columns if isinstance(df, pl.DataFrame) else df.collect_schema()
        ):
            df = df.with_columns(pl.lit(None).alias(column))
        valid = df.filter(pl.col(column).is_null())
        invalid = df.filter(pl.col(column).is_not_null())
        valid_dfs[model] = valid
        invalid_dfs[model] = invalid
    return valid_dfs, invalid_dfs


@typechecked
def frm_fill_null(
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
        target_dtype = pl.Series([apply_fill_value()]).dtype
        new_dtype = target_dtype if not dtype else dtype
        null_rows = null_rows.with_columns(
            pl.Series(column, [apply_fill_value() for _ in range(null_count)]).cast(
                new_dtype
            )
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
def frm_fill_notnull(
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
        target_dtype = pl.Series([apply_fill_value()]).dtype
        new_dtype = target_dtype if not dtype else dtype
        not_null_rows = not_null_rows.with_columns(
            pl.Series(column, [apply_fill_value() for _ in range(not_null_count)]).cast(
                new_dtype
            )
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


mo_polars_kit = SimpleNamespace(
    is_frm_empty=is_frm_empty,
    is_model_frms_empty=is_model_frms_empty,
    has_nulls_in_frm_col=has_nulls_in_frm_col,
    split_df_dict_on_column=split_df_dict_on_column,
    frm_fill_null=frm_fill_null,
    frm_fill_notnull=frm_fill_notnull,
    get_frm_height=get_frm_height,
    collect_model_frms=collect_model_frms,
    sync_model_frms_type=sync_model_frms_type,
)
