"""Только синтетические данные; тесты не обращаются к реальным компаниям."""

import csv
import sqlite3

import pytest
from openpyxl import Workbook, load_workbook

from flare import io


@pytest.fixture
def fake_core(monkeypatch):
    from flare import core

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE imported(name TEXT PRIMARY KEY, city TEXT)")

    def save(database, record, source_name):
        if record["name"] == "СИНТЕТИКА: ошибка":
            database.execute("INSERT INTO imported VALUES ('ОТКАТ', 'Тест')")
            raise ValueError("Недопустимая тестовая запись")
        exists = database.execute("SELECT 1 FROM imported WHERE name=?", (record["name"],)).fetchone()
        database.execute("INSERT OR REPLACE INTO imported VALUES (?,?)", (record["name"], record["city"]))
        return 1, not exists

    monkeypatch.setattr(core, "upsert_business", save)
    yield conn
    conn.close()


def test_import_csv_idempotent_and_row_rollback(tmp_path, fake_core):
    path = tmp_path / "synthetic.csv"
    path.write_text(
        "name;city;phone_verified\nСИНТЕТИКА: кафе;Павлодар;да\n"
        "СИНТЕТИКА: ошибка;Павлодар;нет\nСИНТЕТИКА: салон;Экибастуз;false\n",
        encoding="utf-8-sig",
    )
    first = io.import_file(fake_core, path)
    assert first["created"] == 2
    assert first["errors"] == [{"row": 3, "error": "Недопустимая тестовая запись"}]
    assert fake_core.execute("SELECT COUNT(*) FROM imported").fetchone()[0] == 2
    second = io.import_file(fake_core, path)
    assert second["created"] == 0
    assert second["updated"] == 2


def test_xlsx_rejects_numeric_phone_and_formula_but_continues(tmp_path, fake_core):
    path = tmp_path / "synthetic.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["name", "city", "phone"])
    sheet.append(["СИНТЕТИКА: numeric", "Павлодар", 77000000000])
    sheet.append(["=1+1", "Павлодар", "+77000000001"])
    sheet.append(["СИНТЕТИКА: text", "Павлодар", "+77000000002"])
    workbook.save(path)
    result = io.import_file(fake_core, path)
    assert result["created"] == 1
    assert [error["row"] for error in result["errors"]] == [2, 3]
    assert all("7700" not in error["error"] for error in result["errors"])


def test_omitted_bool_remains_unknown():
    assert "phone_verified" not in io._convert(["name", "phone_verified"], ["СИНТЕТИКА", ""])
    with pytest.raises(ValueError, match="Логические"):
        io._convert(["phone_verified"], ["maybe"])


@pytest.mark.parametrize("value", ["=1+1", "+77000000000", "-1+2", "@SUM(A1)", "  =1", "\tvalue", "\rvalue", "\nvalue"])
def test_formula_guard(value):
    assert io.safe_cell(value).startswith("'")


@pytest.mark.parametrize("suffix", ["csv", "xlsx"])
def test_export_keeps_evidence_and_escapes_formulas(tmp_path, monkeypatch, suffix):
    from flare import core

    synthetic = {"id": 1, "name": "=1+1", "city": "Павлодар", "phone": "+77000000000",
                 "evidence": [{"url": "https://example.invalid", "quote": "СИНТЕТИКА"}]}
    monkeypatch.setattr(core, "list_businesses", lambda *args, **kwargs: [{"id": 1}])
    monkeypatch.setattr(core, "card", lambda *args: synthetic)
    path = tmp_path / f"synthetic.{suffix}"
    assert io.export_file(None, path, ready_only=True) == 1
    if suffix == "csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            row = next(csv.DictReader(stream))
    else:
        workbook = load_workbook(path, data_only=False)
        rows = workbook.active.iter_rows(values_only=True)
        columns = next(rows)
        row = dict(zip(columns, next(rows)))
        workbook.close()
    assert row["name"] == "'=1+1"
    assert row["phone"] == "'+77000000000"
    assert "https://example.invalid" in row["evidence"]


def test_duplicate_or_unknown_columns_rejected(tmp_path, fake_core):
    path = tmp_path / "synthetic.csv"
    path.write_text("name,city,name\nСИНТЕТИКА,Павлодар,СИНТЕТИКА\n", encoding="utf-8")
    with pytest.raises(ValueError, match="повторяются"):
        io.import_file(fake_core, path)
