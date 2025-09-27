# flattener.py
import uuid
from collections import defaultdict
from typing import List, Dict, Union, Literal
import polars as pl


class JsonFlattener:
    def __init__(
        self,
        payload_list: List[Dict],
        nested_table_list: List[str],
        parent_table_name: str,
        frame_type: Literal["auto", "dataframe", "lazyframe"] = "auto",
        lazy_threshold: int = 10000,
    ):
        self.payload_list = payload_list
        self.nested_table_list = nested_table_list
        self.parent_table_name = parent_table_name
        self.frame_type = frame_type
        self.lazy_threshold = lazy_threshold

        self.is_lazy = (
            len(payload_list) > lazy_threshold
            if frame_type == "auto"
            else frame_type == "lazyframe"
        )
        self.frame = pl.LazyFrame if self.is_lazy else pl.DataFrame
        self.results: Dict[str, Union[pl.DataFrame, pl.LazyFrame]] = {}
        self.uuid_tracker = {parent_table_name: [f"{parent_table_name}_uuid"]}
        self.nested_keys = defaultdict(set)

    def flatten(self) -> Dict[str, Union[pl.DataFrame, pl.LazyFrame]]:
        self._init_parent()
        for path in sorted(self.nested_table_list, key=lambda x: x.count(".")):
            self._process_path(path)
        self._cleanup_nested_keys()
        return self.results

    # ---------- Private helpers ----------

    def _frame_instance(self, data: Dict) -> Union[pl.DataFrame, pl.LazyFrame]:
        if self.is_lazy and self.frame == pl.DataFrame:
            return self.frame(data).lazy()
        return self.frame(data)

    def _init_parent(self):
        parent_id = self.uuid_tracker[self.parent_table_name][0]
        self.results[self.parent_table_name] = self._frame_instance(
            {
                **{
                    k: [d.get(k) for d in self.payload_list]
                    for k in (self.payload_list[0].keys() if self.payload_list else [])
                },
                parent_id: [str(uuid.uuid4()) for _ in self.payload_list],
            }
        )

    def _process_path(self, path: str):
        parts, table_path = path.split("."), []
        for i, key in enumerate(parts):
            table_path.append(key)
            table, parent = (
                "__".join(table_path),
                self.parent_table_name if i == 0 else "__".join(table_path[:-1]),
            )
            if parent not in self.results:
                raise ValueError(f"Parent {parent} missing for {table}")
            self._extract_subtable(parent, table, key)

    def _extract_subtable(self, parent: str, table: str, key: str):
        cols = self._schema_names(self.results[parent])
        if key not in cols:
            self.results[table] = pl.DataFrame()
            return

        df = (
            self.results[parent]
            .select([*self.uuid_tracker[parent], key])
            .filter(
                pl.col(key).is_not_null()
                & pl.col(key).map_elements(
                    lambda val: val is not None and len(val) > 0,
                    return_dtype=pl.Boolean,
                )
            )
            .explode(key)
        )

        is_lazy_subtable = self._decide_lazy(df)
        df = self._maybe_unnest(df, key)
        df = self._add_uuid(df, key, is_lazy_subtable)

        self.uuid_tracker[table] = [*self.uuid_tracker[parent], f"{key}_uuid"]
        self.results[table] = (
            df.lazy() if is_lazy_subtable and not isinstance(df, pl.LazyFrame) else df
        )
        self.nested_keys[parent].add(key)

        if self._is_empty(self.results[table], is_lazy_subtable):
            self.results[table] = pl.LazyFrame() if is_lazy_subtable else pl.DataFrame()

    def _schema_names(self, df) -> List[str]:
        return (
            df.collect_schema().names() if isinstance(df, pl.LazyFrame) else df.columns
        )

    def _decide_lazy(self, df) -> bool:
        if self.frame_type == "auto":
            return isinstance(df, pl.LazyFrame) or (
                hasattr(df, "height") and df.height > self.lazy_threshold
            )
        return self.is_lazy

    def _maybe_unnest(self, df, key: str):
        schema = df.collect_schema()
        if isinstance(schema.get(key), pl.Struct):
            return df.unnest(key)
        return df

    def _add_uuid(self, df, key: str, is_lazy_subtable: bool):
        uuid_col = f"{key}_uuid"
        if not is_lazy_subtable:
            return df.with_columns(
                pl.Series(
                    name=uuid_col, values=[str(uuid.uuid4()) for _ in range(df.height)]
                )
            )
        return df.with_columns(
            pl.struct(pl.all())
            .map_elements(lambda _: str(uuid.uuid4()), return_dtype=pl.String)
            .alias(uuid_col)
        )

    def _is_empty(self, df, is_lazy_subtable: bool) -> bool:
        if is_lazy_subtable:
            return not df.collect_schema()
        return df.is_empty()

    def _cleanup_nested_keys(self):
        for table, cols in self.nested_keys.items():
            if table in self.results:
                existing_cols = self._schema_names(self.results[table])
                self.results[table] = self.results[table].drop(
                    [c for c in cols if c in existing_cols]
                )


def json_to_frame(
    payload_list: List[Dict],
    nested_table_list: List[str],
    parent_table_name: str,
    frame_type: Literal["auto", "dataframe", "lazyframe"] = "auto",
    lazy_threshold: int = 10000,
) -> Dict[str, Union[pl.DataFrame, pl.LazyFrame]]:
    return JsonFlattener(
        payload_list=payload_list,
        nested_table_list=nested_table_list,
        parent_table_name=parent_table_name,
        frame_type=frame_type,
        lazy_threshold=lazy_threshold,
    ).flatten()
