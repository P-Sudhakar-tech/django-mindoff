import polars as pl
from django.db import models
from django.db.models.fields.related import ForeignKey, OneToOneField
import numpy as np
from ..polars_kit import mo_polars_kit


ERROR_COL = "__error__info"


class ForeignKeyValidator:
    def __init__(self, df_dict: dict[type[models.Model], pl.DataFrame | pl.LazyFrame]):
        self.df_dict = df_dict

    def validate(self) -> dict[type[models.Model], pl.DataFrame | pl.LazyFrame]:
        return {
            model: self._validate_model_foreign_keys(model, df)
            for model, df in self.df_dict.items()
        }

    def _validate_model_foreign_keys(self, model, df):
        if mo_polars_kit.is_df_empty(df):
            return df
        for field in model._meta.get_fields():
            error_message = f"Invalid foreign key to {model.__name__}"
            if ERROR_COL not in df.columns:
                df = df.with_columns(pl.lit(None).cast(pl.Utf8).alias(ERROR_COL))

            if not isinstance(field, (ForeignKey, OneToOneField)):
                continue

            db_col = field.db_column
            if db_col not in df.columns:
                raise ValueError(
                    f"Missing foreign key column '{db_col}' in DataFrame for model '{model.__name__}'"
                )

            related_model = field.related_model
            related_pk_field = related_model._meta.pk
            related_pk_col = (
                related_pk_field.db_column or related_pk_field.attname or "id"
            )

            # Get distinct FK values used in current df
            fk_values = self._get_distinct_fk_values(df, db_col)

            # Skip validation if no non-null values
            if not fk_values:
                continue

            if related_model in self.df_dict:
                related_df = self.df_dict[related_model]
                related_ids_expr = related_df.select(
                    pl.col(related_pk_col).cast(pl.Utf8).unique()
                )[related_pk_col]
            else:
                db_ids_qs = related_model.objects.filter(
                    **{f"{related_pk_col}__in": fk_values}
                ).values_list(related_pk_col, flat=True)
                related_ids_expr = pl.Series(
                    "__fk_valid_ids", np.array(db_ids_qs, dtype=str)
                )

            # Vectorized FK validation
            df = df.with_columns(
                pl.when(~pl.col(db_col).is_in(related_ids_expr))
                .then(
                    pl.when(pl.col(ERROR_COL).is_not_null())
                    .then(pl.col(ERROR_COL) + pl.lit("; ") + pl.lit(error_message))
                    .otherwise(pl.lit(error_message))
                )
                .otherwise(pl.col(ERROR_COL))
                .alias(ERROR_COL)
            )
        return df

    def _get_distinct_fk_values(
        self, df: pl.DataFrame | pl.LazyFrame, col: str
    ) -> list:
        try:
            # Always narrow to only the FK column
            df_fk = df.select(pl.col(col).drop_nulls().cast(pl.Utf8).unique())
            if isinstance(df, pl.LazyFrame):
                return df_fk.collect(streaming=True).get_column(col).to_list()
            else:
                return df_fk.get_column(col).to_list()
        except Exception as e:
            raise ValueError(
                f"Error extracting unique FK values from column '{col}': {e}"
            )
