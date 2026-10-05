import pandas as pd
import numpy as np
from mapping_store import create_empty_mapping, add_column_mapping
from column_detector import detect_personal_columns

TYPE_PREFIX = {
    "name": "NAME",
    "phone": "PHONE",
    "email": "EMAIL",
    "passport": "PASS",
    "inn": "INN",
    "address": "ADDR",
    "birth_date": "DOB",
    "unknown": "DATA",
}


def _get_prefix(col_type):
    return TYPE_PREFIX.get(col_type, "DATA")


def _next_index(existing, prefix):
    max_num = 0
    for val in existing.values():
        if isinstance(val, str) and val.startswith(prefix + "_"):
            try:
                num = int(val.split("_", 1)[1])
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError):
                pass
    return max_num + 1


def _detect_column_types(df, columns):
    detected = detect_personal_columns(df)
    type_map = {col: col_type for col, col_type in detected}
    result = {}
    for col in columns:
        if col in type_map:
            result[col] = type_map[col]
        else:
            result[col] = "unknown"
    return result


def anonymize_dataframe(df, columns, existing_mapping=None):
    mapping = existing_mapping if existing_mapping is not None else create_empty_mapping()
    anon_df = df.copy()
    stats = {}

    detected_types = _detect_column_types(df, columns)

    for col in columns:
        if col not in df.columns:
            continue
        existing_type = mapping["columns"].get(col, {}).get("type")
        col_type = existing_type if existing_type and existing_type != "unknown" else detected_types.get(col, "unknown")
        existing = mapping["columns"].get(col, {}).get("mapping", {})
        prefix = _get_prefix(col_type)
        next_num = _next_index(existing, prefix)
        value_to_index = dict(existing)
        series = df[col]
        for value in series.dropna().unique():
            val_str = str(value)
            if val_str not in value_to_index:
                value_to_index[val_str] = f"{prefix}_{next_num:03d}"
                next_num += 1
        add_column_mapping(mapping, col, col_type, value_to_index)
        col_map = mapping["columns"][col]["mapping"]
        anon_series = series.map(lambda v: col_map.get(str(v)) if pd.notna(v) else np.nan)
        anon_df[col] = anon_series
        stats[col] = len(value_to_index)
    return anon_df, mapping, stats
