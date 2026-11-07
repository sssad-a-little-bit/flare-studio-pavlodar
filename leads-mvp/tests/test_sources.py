"""All businesses in this file are SYNTHETIC test fixtures, never real leads."""
import json

import pytest

from flare.db import connect, migrate
from flare.sources import SourceError, collect_sources, fetch_osm


@pytest.fixture
def conn():
    db = connect(':memory:')
    migrate(db)
    yield db
    db.close()


def synthetic_record():
    return {
        'name': 'СИНТЕТИЧЕСКОЕ тестовое кафе', 'city': 'Павлодар', 'category': 'кафе',
        'address': 'Тестовая, 123', 'source_external_id': 'node/999999999999',
        'source_url': 'https://www.openstreetmap.org/node/999999999999',
        'confidence': .65, 'phone': '+77000000001', 'phone_verified': False,
    }


def test_unavailable_source_does_not_stop_following_source(conn):
    def fetch(source, city, category, limit):
        if source == '2gis':
            raise SourceError('api_key_and_storage_permission_required')
        return [synthetic_record()]
    result = collect_sources(conn, 'Павлодар', 'кафе', ['2gis', 'osm'], fetcher=fetch)
    assert result[0]['status'] == 'unavailable'
    assert result[1]['status'] == 'completed'
    assert result[1]['received'] == 1
    assert conn.execute('SELECT count(*) FROM businesses').fetchone()[0] == 1
    assert conn.execute('SELECT count(*) FROM collection_attempts').fetchone()[0] == 2


def test_repeated_collection_keeps_single_business(conn):
    def fetch(*args):
        return [synthetic_record()]
    for _ in range(2):
        report = collect_sources(conn, 'Павлодар', 'кафе', ['osm'], fetcher=fetch)
        assert report[0]['received'] == 1
    assert conn.execute('SELECT count(*) FROM businesses').fetchone()[0] == 1


def test_bad_record_isolated_and_no_sensitive_exception_logged(conn):
    invalid = synthetic_record() | {'phone': 'private-invalid-phone'}
    result = collect_sources(conn, 'Павлодар', 'кафе', ['osm'], fetcher=lambda *a: [invalid, synthetic_record()])
    assert result[0]['status'] == 'partial'
    assert result[0]['received'] == 1
    assert result[0]['error'] == 'invalid_records'
    assert 'private-invalid-phone' not in json.dumps([dict(r) for r in conn.execute('SELECT * FROM collection_attempts')])


def test_official_site_from_osm_remains_unchecked(monkeypatch):
    monkeypatch.setattr('flare.sources._request', lambda *a: {'elements': [{
        'type': 'node', 'id': 999999999999,
        'tags': {'name': 'СИНТЕТИЧЕСКОЕ кафе', 'website': 'https://example.org', 'phone': '+77000000001'},
    }]})
    row = fetch_osm('Павлодар', 'кафе', 1)[0]
    assert row['website_status'] == 'unchecked'
    assert row['phone_verified'] is False
    assert 'contact_name' not in row
    assert 'whatsapp' not in row


def test_yandex_stays_disabled_even_with_key(conn, monkeypatch):
    monkeypatch.setenv('YANDEX_API_KEY', 'SYNTHETIC_NOT_A_SECRET')
    result = collect_sources(conn, 'Павлодар', 'кафе', ['yandex'])
    assert result[0]['status'] == 'unavailable'
    assert result[0]['error'] == 'license_prohibits_storage'
    assert conn.execute('SELECT count(*) FROM businesses').fetchone()[0] == 0
