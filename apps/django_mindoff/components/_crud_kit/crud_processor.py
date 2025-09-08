import uuid
import os
import tempfile
from django.conf import settings
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from typing import Dict, Union, Type, Literal
import polars as pl
from django.db import models
import time
from django.db import connection
from typeguard import typechecked


@typechecked
class CRUDProcessor:
    def __init__(
        self,
        model_frame_map: Dict[Type[models.Model], Union[pl.DataFrame, pl.LazyFrame]],
        db_alias: str = "default",
    ):
        self.model_frame_map = model_frame_map
        self.db_alias = db_alias
        self.engine = self._get_sqlalchemy_engine()

    def _get_sqlalchemy_engine(self):
        if self.db_alias not in settings.DATABASES:
            raise ValueError(
                f"Database alias '{self.db_alias}' not found in settings.DATABASES"
            )

        db = settings.DATABASES[self.db_alias]
        engine = db["ENGINE"]
        user = quote_plus(db.get("USER", ""))
        password = quote_plus(db.get("PASSWORD", ""))
        host = db.get("HOST", "localhost")
        port = db.get("PORT", "")
        name = db["NAME"]

        connection.ensure_connection()
        if "mysql" in engine:
            dialect = "mysql+pymysql"
        elif "postgresql" in engine or "postgres" in engine:
            dialect = "postgresql+psycopg2"
        elif "sqlite" in engine:
            return create_engine("sqlite://", creator=lambda: connection.connection)
        else:
            raise ValueError(f"Unsupported database engine: {engine}")

        auth_part = f"{user}:{password}@" if user or password else ""
        port_part = f":{port}" if port else ""
        return create_engine(f"{dialect}://{auth_part}{host}{port_part}/{name}")

    @staticmethod
    def _track_time(func):
        def wrapper(self, *args, **kwargs):
            start = time.time()
            try:
                result = func(self, *args, **kwargs)
                success = True
            except Exception as e:
                result = {"error": str(e)}
                success = False
            return {
                "success": success,
                "result": result,
                "time_taken_seconds": round(time.time() - start, 4),
            }

        return wrapper

    @_track_time
    def create(self) -> dict:
        results = {}
        with self.engine.begin() as conn:
            for model, df in self.model_frame_map.items():
                table = model._meta.db_table
                try:
                    if isinstance(df, pl.LazyFrame):
                        df_schema = df.collect_schema()

                        def write_batch(
                            df: pl.DataFrame,
                            table_name=table,
                            expected_schema=df_schema,
                        ) -> pl.DataFrame:
                            df.write_database(
                                table_name=table_name,
                                connection=conn,
                                if_table_exists="append",
                                engine="sqlalchemy",
                            )
                            return pl.DataFrame(schema=expected_schema)

                        df.map_batches(write_batch, streamable=True).collect(
                            engine="streaming"
                        )
                    else:
                        df.write_database(
                            table_name=table,
                            connection=conn,
                            if_table_exists="append",
                            engine="sqlalchemy",
                        )
                    results[table] = "Success"
                except Exception as e:
                    raise RuntimeError(f"Failed to insert into {table}: {e}") from e
        return results

    # def _save_via_lazy_chunks(self, lf: pl.LazyFrame, table: str, conn):
    #     total_rows_est = lf.fetch(1).height  # Quick way to estimate
    #     if total_rows_est == 0:
    #         return
    #     idx = 0
    #     while True:
    #         chunk = lf.slice(idx, self.chunk_size).collect(streaming=True)
    #         if chunk.is_empty():
    #             break
    #         chunk.write_database(
    #             table_name=table,
    #             connection=conn,
    #             if_table_exists="append",
    #             engine="sqlalchemy",
    #         )
    #         idx += self.chunk_size
