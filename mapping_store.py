import json
from datetime import datetime, timezone


def create_empty_mapping():
    return {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "columns": {},
    }


def save_mapping(mapping, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def load_mapping(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def add_column_mapping(mapping, col_name, col_type, value_to_index):
    if col_name not in mapping["columns"]:
        mapping["columns"][col_name] = {
            "type": col_type,
            "mapping": {},
            "reverse": {},
        }
    col_map = mapping["columns"][col_name]
    for value, idx in value_to_index.items():
        if value not in col_map["mapping"]:
            col_map["mapping"][value] = idx
            col_map["reverse"][str(idx)] = value
    return mapping
