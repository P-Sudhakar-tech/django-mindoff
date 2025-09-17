import os
import random
import time
import uuid

import polars as pl
import psutil
import pytest


def benchmark(func):
    """Decorator to measure time, memory, and CPU usage."""

    def wrapper(*args, **kwargs):
        process = psutil.Process(os.getpid())
        start_mem = process.memory_info().rss
        start_cpu = process.cpu_percent(interval=None)
        start_time = time.perf_counter()

        result = func(*args, **kwargs)

        end_time = time.perf_counter()
        end_cpu = process.cpu_percent(interval=None)
        end_mem = process.memory_info().rss

        stats = {
            "time_sec": end_time - start_time,
            "cpu_percent": end_cpu - start_cpu,
            "mem_mb": (end_mem - start_mem) / (1024 * 1024),
        }
        return result, stats

    return wrapper


# --- Fill Methods ---


@benchmark
def fill_with_map_elements(df, field_name="x"):
    def debug_uuid(x):
        if x == "<<__monp__>>":
            val = str(uuid.uuid4())
            return val
        return x

    return df.with_columns(
        pl.col(field_name)
        .fill_null("<<__monp__>>")
        .map_elements(debug_uuid, return_dtype=pl.Utf8)
        .alias(field_name)
    )


@benchmark
def fill_with_pregenerated(df, col="x"):
    def transform(col):
        col = col.cast(pl.Utf8).str.strip_chars()
        is_null = col.is_null()
        col_len = (
            df.select(col.is_null().sum()).item()
            if not isinstance(df, pl.LazyFrame)
            else df.select(col.is_null().sum()).collect().item()
        )
        uuid4_values = [str(uuid.uuid4()) for _ in range(col_len)]
        generated = pl.Series(name="__temp__", values=uuid4_values)
        col = pl.when(is_null).then(generated).otherwise(col)
        return col

    df = df.with_columns(transform(pl.col(col_name)).alias(col_name))
    return df


# --- Class-based Test ---


class TestBenchmarkFillMethods:

    @pytest.mark.parametrize("n_rows", [20, 10_000, 100_000])
    @pytest.mark.parametrize("frame_type", ["df", "lf"])
    def test_benchmark(self, n_rows, frame_type):
        # Prepare input
        data = {"x": [None if random.random() < 0.5 else str(i) for i in range(n_rows)]}
        df = pl.DataFrame(data)
        print("dtype", df["x"].dtype)
        assert df["x"].null_count() > 0, "Null not found"
        if frame_type == "lf":
            df = df.lazy()

        # Run benchmarks
        _, stats_map = fill_with_map_elements(df)
        _, stats_pre = fill_with_pregenerated(df)

        print(f"\n[{frame_type}] map_elements({n_rows}) => {stats_map}")
        print(f"[{frame_type}] pregenerated({n_rows}) => {stats_pre}")

        # Validate: no nulls remain
        df_map, _ = fill_with_map_elements(df)
        df_pre, _ = fill_with_pregenerated(df)

        # collect if lazy
        if isinstance(df_map, pl.LazyFrame):
            df_map = df_map.collect()
        if isinstance(df_pre, pl.LazyFrame):
            df_pre = df_pre.collect()

        assert df_map["x"].null_count() == 0, "Map nulls are not changed"
        assert df_pre["x"].null_count() == 0, "Pre nulls are not changed"

        # validate shape
        assert df_map.shape == df_pre.shape, "Map and Pre did not match"
