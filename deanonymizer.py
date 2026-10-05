import re
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def _normalize(val):
    return re.sub(r"[^\d]", "", str(val))


def deanonymize_dataframe(df, mapping):
    restore_df = df.copy()
    stats = {}
    for col_name, col_data in mapping.get("columns", {}).items():
        if col_name not in restore_df.columns:
            logger.warning("Колонка '%s' отсутствует в таблице, пропуск.", col_name)
            continue
        reverse = col_data.get("reverse", {})
        series = restore_df[col_name]
        unmapped = 0

        norm_index = {}
        for k, v in reverse.items():
            norm_index[_normalize(k)] = v

        def restore_value(val, rev=reverse, nidx=norm_index):
            nonlocal unmapped
            if pd.isna(val):
                return np.nan
            key = str(val).strip()
            if key in rev:
                return rev[key]
            norm = _normalize(key)
            if norm in nidx:
                return nidx[norm]
            unmapped += 1
            logger.warning("Значение %s не найдено в reverse-маппинге.", val)
            return val

        restore_df[col_name] = series.apply(restore_value)
        stats[col_name] = {"total": len(series), "unmapped": unmapped}
    return restore_df, stats
