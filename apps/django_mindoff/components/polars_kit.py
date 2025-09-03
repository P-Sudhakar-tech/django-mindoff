import polars as pl
from typeguard import typechecked
from types import SimpleNamespace
from django.db import models
from typing import Dict, Type, Tuple, Union


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


mo_polars_kit = SimpleNamespace(
    is_df_empty=is_df_empty,
    is_all_dict_df_empty=is_all_dict_df_empty,
    split_df_dict_on_column=split_df_dict_on_column,
)
