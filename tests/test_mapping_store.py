import os
import tempfile

import pytest

from mapping_store import (
    add_column_mapping,
    create_empty_mapping,
    load_mapping,
    save_mapping,
)


def test_create_empty_mapping():
    m = create_empty_mapping()
    assert m["version"] == 1
    assert "created_at" in m
    assert m["columns"] == {}


def test_save_load_roundtrip():
    m = create_empty_mapping()
    add_column_mapping(m, "ФИО", "name", {"А": 1, "Б": 2})
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        path = f.name
    try:
        save_mapping(m, path)
        loaded = load_mapping(path)
        assert loaded["columns"]["ФИО"]["mapping"] == {"А": 1, "Б": 2}
        assert loaded["columns"]["ФИО"]["reverse"] == {"1": "А", "2": "Б"}
    finally:
        os.unlink(path)


def test_add_column_mapping():
    m = create_empty_mapping()
    add_column_mapping(m, "Телефон", "phone", {"+79001112233": 1})
    assert m["columns"]["Телефон"]["mapping"]["+79001112233"] == 1
    assert m["columns"]["Телефон"]["reverse"]["1"] == "+79001112233"


def test_add_column_mapping_does_not_overwrite():
    m = create_empty_mapping()
    add_column_mapping(m, "Телефон", "phone", {"+79001112233": 1})
    add_column_mapping(m, "Телефон", "phone", {"+79001112233": 1, "+79004445566": 2})
    assert m["columns"]["Телефон"]["mapping"]["+79001112233"] == 1
    assert m["columns"]["Телефон"]["mapping"]["+79004445566"] == 2
    assert len(m["columns"]["Телефон"]["mapping"]) == 2


def test_unicode_values():
    m = create_empty_mapping()
    add_column_mapping(m, "ФИО", "name", {"Иванов И.И.": 1, "Петров П.П.": 2})
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w", encoding="utf-8") as f:
        path = f.name
    try:
        save_mapping(m, path)
        loaded = load_mapping(path)
        assert loaded["columns"]["ФИО"]["mapping"]["Иванов И.И."] == 1
    finally:
        os.unlink(path)
