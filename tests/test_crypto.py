import pytest

from crypto_utils import decrypt_mapping, encrypt_mapping
from mapping_store import create_empty_mapping, add_column_mapping


@pytest.fixture
def sample_mapping():
    m = create_empty_mapping()
    add_column_mapping(m, "ФИО", "name", {"Иванов": 1, "Петров": 2})
    add_column_mapping(m, "Телефон", "phone", {"+79001112233": 1})
    return m


def test_encrypt_decrypt_roundtrip(sample_mapping):
    encrypted = encrypt_mapping(sample_mapping, "secret123")
    decrypted = decrypt_mapping(encrypted, "secret123")
    assert decrypted["columns"]["ФИО"]["mapping"]["Иванов"] == 1
    assert decrypted["columns"]["Телефон"]["reverse"]["1"] == "+79001112233"


def test_wrong_password_fails(sample_mapping):
    encrypted = encrypt_mapping(sample_mapping, "correct")
    with pytest.raises(Exception):
        decrypt_mapping(encrypted, "wrong")


def test_different_encryptions_differ(sample_mapping):
    e1 = encrypt_mapping(sample_mapping, "pass1")
    e2 = encrypt_mapping(sample_mapping, "pass1")
    d1 = decrypt_mapping(e1, "pass1")
    d2 = decrypt_mapping(e2, "pass1")
    assert d1 == d2
    assert e1 != e2
