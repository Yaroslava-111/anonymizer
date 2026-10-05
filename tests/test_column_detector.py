import pandas as pd

from column_detector import detect_personal_columns


def test_phone_by_name():
    df = pd.DataFrame({"Телефон": ["+79001112233", "+79004445566"]})
    result = detect_personal_columns(df)
    assert any(col == "Телефон" and t == "phone" for col, t in result)


def test_email_by_name():
    df = pd.DataFrame({"Email": ["a@b.com", "c@d.org"]})
    result = detect_personal_columns(df)
    assert any(col == "Email" and t == "email" for col, t in result)


def test_name_by_name():
    df = pd.DataFrame({"ФИО": ["Иванов", "Петров"]})
    result = detect_personal_columns(df)
    assert any(col == "ФИО" and t == "name" for col, t in result)


def test_passport_by_content():
    df = pd.DataFrame({"Документ": ["1234 567890", "2345 678901"]})
    result = detect_personal_columns(df)
    assert any(col == "Документ" and t == "passport" for col, t in result)


def test_phone_by_content():
    df = pd.DataFrame({"Контакт": ["+79001112233", "+79004445566", "+79007778899"]})
    result = detect_personal_columns(df)
    assert any(t == "phone" for _, t in result)


def test_email_by_content():
    df = pd.DataFrame({"Связь": ["test@example.com", "user@domain.org", "admin@mail.ru"]})
    result = detect_personal_columns(df)
    assert any(t == "email" for _, t in result)


def test_inn_by_name():
    df = pd.DataFrame({"ИНН": ["1234567890", "0987654321"]})
    result = detect_personal_columns(df)
    assert any(col == "ИНН" and t == "inn" for col, t in result)


def test_no_false_positives():
    df = pd.DataFrame({
        "ID": [1, 2, 3],
        "Название": ["Товар А", "Товар Б", "Товар В"],
        "Цена": [100.0, 200.0, 300.0],
    })
    result = detect_personal_columns(df)
    assert len(result) == 0
