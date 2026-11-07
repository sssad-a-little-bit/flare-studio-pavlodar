"""End-to-end CLI checks; all companies/contact values are SYNTHETIC TEST DATA."""
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(db_path, *arguments, expected=0):
    env = dict(os.environ, FLARE_DATA_FRESH_DAYS='90', FLARE_BENEFIT_FRESH_DAYS='180')
    result = subprocess.run(
        [sys.executable, '-m', 'flare', '--db', str(db_path), *map(str, arguments)],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == expected, result.stderr or result.stdout
    return json.loads(result.stdout) if result.stdout else None


def test_cli_import_ready_export_block_reimport_is_persistent(tmp_path):
    db_path = tmp_path / 'synthetic.sqlite3'
    csv_path = tmp_path / 'synthetic.csv'
    export_path = tmp_path / 'synthetic-export.xlsx'
    checked = (datetime.now(timezone.utc) - timedelta(seconds=2)).isoformat(timespec='seconds')
    synthetic = dict(
        source_external_id='synthetic-cli-1', name='СИНТЕТИЧЕСКОЕ CLI кафе',
        city='Павлодар', category='кафе', address='Тестовая улица, 99',
        phone='+77010000009', phone_verified='true', source_url='https://example.org/synthetic/cli',
        observed_at=checked, confidence='0.9', do_not_contact='false',
        website_status='not_found', website_checked_at=checked,
        website_check_source='СИНТЕТИЧЕСКАЯ ручная проверка',
        website_evidence='СИНТЕТИЧЕСКАЯ проверка: поиск и профиль',
        website_check_methods='search;profile', signal_type='likely_benefit',
        signal_reason='СИНТЕТИЧЕСКАЯ гипотеза: меню и бронирование', signal_date=checked,
    )
    with csv_path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(synthetic))
        writer.writeheader()
        writer.writerow(synthetic)
    assert run_cli(db_path, 'init')['status']
    report = run_cli(db_path, 'import', csv_path, '--source', 'synthetic_crm')
    assert report == {'processed': 1, 'created': 1, 'updated': 0, 'errors': []}
    leads = run_cli(db_path, 'list', '--ready')
    assert len(leads) == 1 and leads[0]['ready'] is True
    bid = leads[0]['id']
    card = run_cli(db_path, 'show', bid, '--json')
    assert card['contacts'][0]['value'] == synthetic['phone']
    assert card['signals'][0]['signal_type'] == 'likely_benefit'
    assert run_cli(db_path, 'export', export_path, '--ready')['exported'] == 1
    from openpyxl import load_workbook
    workbook = load_workbook(export_path, read_only=True)
    try:
        rows = list(workbook.active.values)
        headers = list(rows[0])
        assert rows[1][headers.index('name')] == synthetic['name']
        assert json.loads(rows[1][headers.index('contacts')])[0]['value'] == synthetic['phone']
    finally:
        workbook.close()
    run_cli(db_path, 'block', bid, '--reason', 'СИНТЕТИЧЕСКИЙ запрет контакта')
    report = run_cli(db_path, 'import', csv_path, '--source', 'synthetic_crm')
    assert report == {'processed': 1, 'created': 0, 'updated': 1, 'errors': []}
    assert run_cli(db_path, 'list', '--ready') == []
    card = run_cli(db_path, 'show', bid, '--json')
    assert card['do_not_contact'] == 1
    assert any(i['kind'] == 'do_not_contact' for i in card['interactions'])


def test_cli_reports_bad_import_rows_and_disabled_sources_with_nonzero_exit(tmp_path):
    db_path = tmp_path / 'synthetic.sqlite3'
    bad_import = tmp_path / 'synthetic-invalid.csv'
    bad_import.write_text('name,city,category,phone\nСИНТЕТИЧЕСКАЯ ошибка,Павлодар,кафе,123\n', encoding='utf-8')
    report = run_cli(db_path, 'import', bad_import, expected=2)
    assert report['created'] == 0
    assert report['errors'][0]['row'] == 2
    assert '123' not in report['errors'][0]['error']
    sources = run_cli(db_path, 'collect', '--city', 'Павлодар', '--category', 'кафе', '--sources', 'yandex,instagram', expected=2)
    assert len(sources) == 2
    assert all(source['status'] == 'unavailable' for source in sources)
    attempts = run_cli(db_path, 'attempts')
    assert len(attempts) == 2
    assert all(attempt['error_code'] for attempt in attempts)
