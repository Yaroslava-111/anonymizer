import os
import tempfile

import pandas as pd
import pytest

from anonymizer import anonymize_dataframe
from deanonymizer import deanonymize_dataframe
from mapping_store import load_mapping


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "ФИО": ["Иванов И.И.", "Петров П.П.", "Сидоров С.С.", "Иванов И.И."],
        "Телефон": ["+79001112233", "+79004445566", "+79007778899", "+79001112233"],
        "Возраст": [25, 30, 35, 25],
    })


def test_roundtrip(sample_df):
    anon_df, mapping, _ = anonymize_dataframe(sample_df, ["ФИО", "Телефон"])
    restored_df, _ = deanonymize_dataframe(anon_df, mapping)
    pd.testing.assert_frame_equal(sample_df, restored_df)


def test_mapping_consistency(sample_df):
    anon_df1, mapping1, _ = anonymize_dataframe(sample_df, ["ФИО"])
    anon_df2, _, _ = anonymize_dataframe(sample_df, ["ФИО"], existing_mapping=mapping1)
    pd.testing.assert_frame_equal(anon_df1, anon_df2)


def test_new_values_in_existing_mapping():
    df1 = pd.DataFrame({"Имя": ["А", "Б", "В"]})
    anon1, mapping1, _ = anonymize_dataframe(df1, ["Имя"])

    df2 = pd.DataFrame({"Имя": ["А", "Г", "Д"]})
    anon2, mapping2, stats = anonymize_dataframe(df2, ["Имя"], existing_mapping=mapping1)

    restored2, _ = deanonymize_dataframe(anon2, mapping2)
    pd.testing.assert_frame_equal(df2, restored2)
    assert stats["Имя"] == 5


def test_nan_preserved():
    df = pd.DataFrame({"ФИО": ["А", None, "Б"]})
    anon_df, mapping, _ = anonymize_dataframe(df, ["ФИО"])
    assert pd.isna(anon_df["ФИО"].iloc[1])
    restored, _ = deanonymize_dataframe(anon_df, mapping)
    assert pd.isna(restored["ФИО"].iloc[1])
    assert restored["ФИО"].iloc[0] == "А"
    assert restored["ФИО"].iloc[2] == "Б"


def test_csv_roundtrip():
    df = pd.DataFrame({
        "ФИО": ["Иванов", "Петров", "Сидоров"],
        "Телефон": ["+79001112233", "+79004445566", "+79007778899"],
    })
    anon_df, mapping, _ = anonymize_dataframe(df, ["ФИО", "Телефон"])
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
        anon_path = f.name
        anon_df.to_csv(f, index=False, encoding="utf-8")
    try:
        loaded = pd.read_csv(anon_path, encoding="utf-8")
        restored, _ = deanonymize_dataframe(loaded, mapping)
        pd.testing.assert_frame_equal(df, restored)
    finally:
        os.unlink(anon_path)
