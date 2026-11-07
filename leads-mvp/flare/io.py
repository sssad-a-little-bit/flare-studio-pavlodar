"""Локальный импорт и экспорт. Исходные файлы не сохраняются в базе целиком."""

from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import InvalidFileException


IMPORT_COLUMNS = (
    "source_external_id", "name", "category", "city", "address", "phone",
    "phone_type", "phone_verified", "whatsapp", "whatsapp_verified", "email",
    "profile_url", "website", "website_status", "website_checked_at",
    "website_check_source", "website_evidence", "website_check_methods",
    "contact_name", "contact_role", "contact_business", "contact_verified",
    "source_url", "observed_at", "confidence", "signal_type", "signal_quote",
    "signal_reason", "signal_date", "signal_url", "stage", "do_not_contact",
    "exclusion_reason",
)
BOOL_COLUMNS = {"phone_verified", "whatsapp_verified", "contact_verified", "do_not_contact"}
PHONE_COLUMNS = {"phone", "whatsapp", "contact_business"}
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_ROWS = 50_000


def _headers(values):
    headers = [str(v or "").strip().lstrip("\ufeff") for v in values]
    # Ignore entirely empty trailing spreadsheet columns, but not gaps.
    while headers and not headers[-1]:
        headers.pop()
    if not headers or any(not h for h in headers):
        raise ValueError("Нужна строка непустых заголовков; используйте шаблон импорта")
    if len(set(headers)) != len(headers):
        raise ValueError("Заголовки столбцов повторяются")
    if any(h not in IMPORT_COLUMNS for h in headers):
        raise ValueError("Неизвестные столбцы: сопоставьте заголовки с шаблоном импорта")
    if "name" not in headers or "city" not in headers:
        raise ValueError("Обязательные столбцы: name и city")
    return headers


def _convert(headers, values):
    if len(values) > len(headers) and any(v not in (None, "") for v in values[len(headers):]):
        raise ValueError("В строке больше значений, чем заголовков")
    record = {}
    for column, value in zip(headers, values):
        if value is None or value == "":
            continue
        if column in PHONE_COLUMNS and not isinstance(value, str):
            raise ValueError("Телефоны и деловые контакты XLSX должны быть текстовыми ячейками")
        if isinstance(value, (datetime, date)):
            value = value.isoformat()
        if column in BOOL_COLUMNS:
            normalized = str(value).strip().lower()
            if normalized not in {"true", "false", "1", "0", "да", "нет"}:
                raise ValueError("Логические поля принимают true/false, 1/0 или да/нет")
            record[column] = normalized in {"true", "1", "да"}
        elif column == "confidence":
            try:
                record[column] = float(value)
            except (ValueError, TypeError):
                raise ValueError("confidence должен быть числом от 0 до 1") from None
        else:
            record[column] = str(value).strip()
    return record


def _csv_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(8192)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(stream, dialect, strict=True)
        headers = _headers(next(reader, []))
        for index, values in enumerate(reader, start=2):
            yield index, headers, values


def _xlsx_rows(path):
    try:
        workbook = load_workbook(path, read_only=True, data_only=False)
    except (BadZipFile, InvalidFileException, KeyError, ValueError):
        raise ValueError("Не удалось прочитать XLSX: файл повреждён или имеет другой формат") from None
    try:
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)
        headers = _headers(next(rows, []))
        for index, values in enumerate(rows, start=2):
            # Formula cells must never be interpreted as imported business facts.
            if any(isinstance(v, str) and v.startswith("=") for v in values):
                yield index, headers, ValueError("Формулы в импортируемом XLSX не допускаются")
            else:
                yield index, headers, values
    finally:
        workbook.close()


def import_file(conn, path, *, source_name="import"):
    """Импортирует валидные строки; ошибки строк не откатывают остальные.

    Отчёт содержит номера строк и причины, без исходных контактов.
    Внешний транзакционный контекст остаётся под управлением вызывающего кода.
    """
    from . import core

    path = Path(path)
    if path.suffix.lower() not in {".csv", ".xlsx"}:
        raise ValueError("Поддерживаются только CSV UTF-8 и XLSX")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Файл превышает ограничение 25 МБ")
    report = {"processed": 0, "created": 0, "updated": 0, "errors": []}
    rows = _csv_rows(path) if path.suffix.lower() == ".csv" else _xlsx_rows(path)
    last_index = 1
    try:
        for index, headers, values in rows:
            last_index = index
            if index > MAX_ROWS + 1:
                report["errors"].append({"row": index, "error": "Достигнут предел 50000 строк; разделите файл"})
                break
            if not isinstance(values, Exception) and all(v in (None, "") for v in values):
                continue
            report["processed"] += 1
            conn.execute("SAVEPOINT import_row")
            try:
                if isinstance(values, Exception):
                    raise values
                record = _convert(headers, values)
                _, created = core.upsert_business(conn, record, source_name=source_name)
                conn.execute("RELEASE SAVEPOINT import_row")
                report["created" if created else "updated"] += 1
            except ValueError as exc:
                conn.execute("ROLLBACK TO SAVEPOINT import_row")
                conn.execute("RELEASE SAVEPOINT import_row")
                report["errors"].append({"row": index, "error": str(exc)})
            except Exception:
                conn.execute("ROLLBACK TO SAVEPOINT import_row")
                conn.execute("RELEASE SAVEPOINT import_row")
                # No raw SQL, payload, contact or credentials in error reports.
                report["errors"].append({"row": index, "error": "Не удалось сохранить строку; проверьте формат и базу"})
    except (csv.Error, UnicodeError):
        report["errors"].append({
            "row": last_index + 1,
            "error": "Не удалось прочитать CSV: проверьте UTF-8, разделители и кавычки; чтение остановлено",
        })
    finally:
        rows.close()
    return report


def safe_cell(value):
    """Защита CSV/XLSX от запуска формул при открытии в табличном редакторе."""
    if isinstance(value, (dict, list, tuple)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    if value is None:
        return ""
    if isinstance(value, str):
        value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
        if re.match(r"^[ \t\r\n]*[=+@\-\t\r\n]", value):
            return "'" + value
    return value


def export_file(conn, path, *, ready_only=False, city=None, stage=None):
    """Экспорт карточек с текущей квалификацией и ссылками на доказательства."""
    from . import core

    path = Path(path)
    if path.suffix.lower() not in {".csv", ".xlsx"}:
        raise ValueError("Поддерживаются только CSV и XLSX")
    businesses = core.list_businesses(conn, ready_only=ready_only, city=city, stage=stage)
    cards = [core.card(conn, business["id"]) for business in businesses]
    # Плоские поля для рабочего списка; полная история остаётся в JSON-колонках.
    for card in cards:
        card["business_phones"] = "; ".join(
            c["value"] + (" (подтверждён)" if c["verified"] else " (не подтверждён)")
            for c in card.get("contacts", []) if c["kind"] == "phone")
        card["confirmed_whatsapp"] = "; ".join(
            c["value"] for c in card.get("contacts", []) if c["kind"] == "whatsapp" and c["verified"])
        card["business_emails"] = "; ".join(c["value"] for c in card.get("contacts", []) if c["kind"] == "email")
        card["business_profiles"] = "; ".join(c["value"] for c in card.get("contacts", []) if c["kind"] == "profile")
        current_people = {c["value"] for c in card.get("contacts", []) if c["kind"] == "responsible" and c["verified"]}
        responsible = [o for o in card.get("observations", []) if o["kind"] == "responsible"
                       and o["payload"]["contact_business"] in current_people]
        person = max(responsible, key=lambda o: (o["observed_at"], o["id"]))["payload"] if responsible else {}
        card["responsible_name"] = person.get("contact_name", "")
        card["responsible_role"] = person.get("contact_role", "")
        card["responsible_business_contact"] = person.get("contact_business", "")
        labels = {"confirmed_demand": "Подтверждённый спрос", "likely_benefit": "Гипотеза пользы сайта"}
        card["interest_types"] = "; ".join(sorted({labels[s["signal_type"]] for s in card.get("signals", []) if s["current"]}))
        card["website_benefit"] = "; ".join(s.get("signal_reason", "") for s in card.get("signals", [])
                                           if s["signal_type"] == "likely_benefit" and s["current"])
        card["source_urls"] = "; ".join(dict.fromkeys(e["url"] for e in card.get("evidence", [])))
    # Stable leading columns; include every remaining card field, including nested evidence.
    columns = ["id", "name", "city", "category", "address", "stage", "do_not_contact",
               "business_phones", "confirmed_whatsapp", "business_emails", "responsible_name",
               "responsible_role", "responsible_business_contact", "website", "website_status",
               "website_benefit", "interest_types", "priority", "data_quality", "next_step", "exclusion_reason"]
    columns += sorted({key for card in cards for key in card} - set(columns))
    if path.suffix.lower() == ".csv":
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            writer.writerows([[safe_cell(card.get(column)) for column in columns] for card in cards])
    else:
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("Лиды Flare Studio")
        sheet.append(columns)
        for card in cards:
            values = [safe_cell(card.get(column)) for column in columns]
            if any(isinstance(value, str) and len(value) > 32767 for value in values):
                raise ValueError("Карточка превышает предел ячейки XLSX (32767 символов); используйте CSV")
            sheet.append(values)
        workbook.save(path)
        workbook.close()
    return len(cards)
