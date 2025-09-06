import polars as pl
import pytest
import uuid
import time
import psutil
import os
import random
import pandas as pd
from tabulate import tabulate
import statistics


def benchmark(func):
    """Decorator to measure time, memory, and CPU usage (normalized to total CPU)."""

    def wrapper(*args, **kwargs):
        process = psutil.Process(os.getpid())
        num_cpus = psutil.cpu_count(logical=True)

        start_mem = process.memory_info().rss
        start_time = time.perf_counter()
        start_cpu_time = time.process_time()

        result = func(*args, **kwargs)

        end_time = time.perf_counter()
        end_cpu_time = time.process_time()
        end_mem = process.memory_info().rss

        elapsed = end_time - start_time
        cpu_time = end_cpu_time - start_cpu_time

        # Normalize CPU percent to total system (max 100%)
        cpu_percent = (cpu_time / elapsed) * 100 / num_cpus if elapsed > 0 else 0.0

        stats = {
            "time_sec": elapsed,
            "cpu_percent": cpu_percent,
            "mem_mb": (end_mem - start_mem) / (1024 * 1024),
        }
        return result, stats

    return wrapper


# --- Fill Methods ---


@benchmark
def fill_with_map_elements(df, field_name="x"):
    def debug_uuid(x):
        if x is None:
            if random.choice([True, False]):
                result = sum(i for i in range(100))

            elif random.randint(1, 10) > 5:
                result = [i**2 for i in range(100)]
            return str(uuid.uuid4())
        return x

    df = df.with_columns(
        pl.col(field_name)
        .map_elements(
            lambda x: debug_uuid(x),
            skip_nulls=False,
            return_dtype=None,
        )
        .alias(field_name)
    )
    if isinstance(df, pl.LazyFrame):
        print("collecting map_gen")
        df = df.collect()
    return df


@benchmark
def fill_with_lit(df, col_name="x"):
    df = df.with_columns(
        pl.col(col_name)
        .fill_null(pl.lit(str(uuid.uuid4()), allow_object=True))
        .alias(col_name)
    )
    # df = df.with_columns(
    #     pl.when(pl.col(col_name).is_null())
    #     .then(pl.lit((uuid.uuid4()), allow_object=True))
    #     .otherwise(pl.col(col_name))
    #     .alias(col_name)
    # )

    if isinstance(df, pl.LazyFrame):
        df = df.collect()
    print(df)
    return df


@benchmark
def fill_with_null_pregen(df, col="x"):
    def debug_uuid(x=None):
        if x is None:
            if random.choice([True, False]):
                result = sum(i for i in range(100))

            elif random.randint(1, 10) > 5:
                result = [i**2 for i in range(100)]
            return str(uuid.uuid4())
        return x

    df = df.with_row_index("idx")
    null_rows = df.filter(pl.col("x").is_null())
    null_count = (
        null_rows.select(pl.len()).item(0, 0)
        if not isinstance(df, pl.LazyFrame)
        else null_rows.select(pl.len()).collect(engine="streaming").item(0, 0)
    )
    not_null_rows = df.filter(pl.col("x").is_not_null())
    null_rows = null_rows.with_columns(
        pl.Series("x", [debug_uuid() for _ in range(null_count)])
    )
    df_filled = pl.concat([null_rows, not_null_rows]).sort("idx").drop("idx")
    if isinstance(df_filled, pl.LazyFrame):
        print("collecting null_gen")
        df_filled = df_filled.collect()
    return df_filled


# --- Test Class (works with pytest or manually) ---


class TestBenchmarkFillMethods:

    def run_benchmark(self, df, frame_type, n_rows, repeats: int = 3):
        methods = {
            "map_elements": fill_with_map_elements,
            "pregenerated": fill_with_lit,
            "null_pregen": fill_with_null_pregen,
        }

        results = []
        for name, func in methods.items():
            times, mems, cpus, nulls_before, nulls_after = [], [], [], [], []
            for _ in range(repeats):
                # Track null counts
                if isinstance(df, pl.LazyFrame):
                    null_before = df.select(pl.col("x").null_count()).collect().item()
                else:
                    null_before = df["x"].null_count()

                df_out, stats = func(df)

                if isinstance(df_out, pl.LazyFrame):
                    null_after = (
                        df_out.select(pl.col("x").null_count()).collect().item()
                    )
                else:
                    null_after = df_out["x"].null_count()

                stats["null_before"] = null_before
                stats["null_after"] = null_after

                times.append(stats["time_sec"])
                mems.append(stats["mem_mb"])
                cpus.append(stats["cpu_percent"])
                nulls_before.append(null_before)
                nulls_after.append(null_after)

            results.append(
                [
                    frame_type,
                    name,
                    f"{statistics.mean(times):.6f}",
                    f"{statistics.mean(mems):.3f}",
                    f"{statistics.mean(cpus):.2f}",
                    int(statistics.mean(nulls_before)),
                    int(statistics.mean(nulls_after)),
                ]
            )

        return results

    def test_benchmark(self, n_rows, frame_type, repeats: int = 3):
        import random

        data = {
            "x": [
                None if y >= (n_rows / 2) else str(uuid.uuid4()) for y in range(n_rows)
            ]
        }
        df = pl.DataFrame(data)

        assert df["x"].null_count() > 0, "Null not found"
        if frame_type == "lf":
            df = df.lazy()
        return self.run_benchmark(df, frame_type, n_rows, repeats)


# --- Raw Python Runner ---
def main():
    tester = TestBenchmarkFillMethods()
    for n_rows in [50, 50_000]:
        all_results = []
        for frame_type in ["df", "lf"]:
            all_results.extend(tester.test_benchmark(n_rows, frame_type, repeats=5))

        # Print one table per n_rows
        headers = [
            "Frame Type",
            "Function",
            "Avg Time (s)",
            "Avg Mem (MB)",
            "Avg CPU (%)",
            "Nulls Before",
            "Nulls After",
        ]
        print(f"\n=== Benchmark Results (n_rows = {n_rows}) ===")
        print(tabulate(all_results, headers=headers, tablefmt="fancy_grid"))


if __name__ == "__main__":
    main()
