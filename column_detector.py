import re
import pandas as pd
from rich.console import Console

from config import PERSONAL_COLUMN_PATTERNS, REGEX_PATTERNS


def _match_column_name(col_name):
    normalized = col_name.strip().lower()
    for pattern, col_type in PERSONAL_COLUMN_PATTERNS.items():
        if pattern == normalized:
            return col_type
        if len(normalized) >= 3 and len(pattern) >= 3:
            if pattern in normalized or normalized in pattern:
                return col_type
    return None


def _match_column_content(series, sample_size=100):
    non_null = series.dropna().astype(str).head(sample_size)
    if len(non_null) == 0:
        return None
    for col_type, regex in REGEX_PATTERNS.items():
        matches = non_null.str.match(regex, case=False)
        if matches.mean() > 0.7:
            return col_type
    return None


def detect_personal_columns(df):
    results = []
    for col in df.columns:
        detected_type = _match_column_name(col)
        if detected_type is None:
            detected_type = _match_column_content(df[col])
        if detected_type is not None:
            results.append((col, detected_type))
    return results


def suggest_columns_for_anonymization(df):
    console = Console()
    detected = detect_personal_columns(df)
    if not detected:
        console.print("[yellow]Не удалось автоматически определить персональные колонки.[/yellow]")
        return
    console.print("[bold]Определены персональные колонки:[/bold]")
    for i, (col_name, col_type) in enumerate(detected, 1):
        console.print(f"  [{i}] {col_name} ({col_type})")
    return detected
