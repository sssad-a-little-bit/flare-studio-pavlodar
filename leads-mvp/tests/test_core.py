"""All companies, contacts and quotations in this module are SYNTHETIC TEST DATA."""
from datetime import datetime, timedelta, timezone

import pytest

from flare import core
from flare.db import connect, migrate


@pytest.fixture
def db():
    conn = connect(':memory:')
    migrate(conn)
    yield conn
    conn.close()


def date_ago(days=0):
    return (datetime.now(timezone.utc) - timedelta(days=days, seconds=1)).isoformat(timespec='seconds')


def record(**changes):
    """СИНТЕТИЧЕСКАЯ компания; не использовать для реальных звонков."""
    stamp = date_ago()
    r = dict(
        name='СИНТЕТИЧЕСКОЕ кафе Альфа', category='кафе', city='Павлодар',
        address='Тестовая улица, 1', source_external_id='synthetic-alpha',
        phone='+77010000001', phone_verified=True,
        source_url='https://example.org/synthetic/alpha', observed_at=stamp,
        confidence=0.8, website_status='not_found', website_checked_at=stamp,
        website_check_source='Синтетическая ручная проверка',
        website_evidence='СИНТЕТИЧЕСКИЕ search и profile; сайт не найден при проверке',
        website_check_methods=['search', 'profile'],
        signal_type='likely_benefit', signal_reason='СИНТЕТИЧЕСКАЯ гипотеза: каталог услуг',
        signal_date=stamp,
    )
    r.update(changes)
    return r


def count(db, table):
    return db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]


def test_exact_reimport_does_not_duplicate_business_contacts_or_observations(db):
    r = record()
    first, created = core.upsert_business(db, r)
    initial = {table: count(db, table) for table in ('businesses', 'contacts', 'evidence', 'observations', 'identities')}
    second, created_again = core.upsert_business(db, r)
    assert created and not created_again
    assert first == second
    assert initial == {table: count(db, table) for table in initial}


def test_stable_source_id_survives_rename_phone_and_website_changes(db):
    first, _ = core.upsert_business(db, record())
    second, created = core.upsert_business(db, record(
        name='СИНТЕТИЧЕСКОЕ новое имя', phone='+77010000002',
        website='https://example.org/business', website_status='ambiguous',
    ))
    assert first == second and not created
    assert count(db, 'businesses') == 1
    assert count(db, 'observations') >= 3
    assert core.card(db, first)['website_status'] == 'ambiguous'


def test_phone_plus_branch_location_deduplicates_across_sources_and_renames(db):
    first, _ = core.upsert_business(db, record(source_external_id='source-a'), source_name='source-a')
    second, created = core.upsert_business(db, record(name='СИНТЕТИЧЕСКИЙ ребрендинг', source_external_id='source-b'), source_name='source-b')
    assert first == second and not created
    assert count(db, 'businesses') == 1
    assert {r[0] for r in db.execute('SELECT name FROM sources')} == {'source-a', 'source-b'}


def test_shared_chain_phone_does_not_merge_different_branches(db):
    first, _ = core.upsert_business(db, record(source_external_id='branch-1'))
    second, created = core.upsert_business(db, record(source_external_id='branch-2', address='Тестовая улица, 2'))
    assert first != second and created
    assert count(db, 'businesses') == 2


def test_conflicting_identifiers_do_not_merge_or_modify_records(db):
    first = record(source_external_id='first')
    second = record(name='СИНТЕТИЧЕСКОЕ кафе Бета', source_external_id='second', phone='+77010000002', address='Тестовая улица, 2')
    a, _ = core.upsert_business(db, first)
    b, _ = core.upsert_business(db, second)
    before = [dict(row) for row in db.execute('SELECT * FROM businesses ORDER BY id')]
    with pytest.raises(ValueError, match='Конфликт идентификаторов'):
        core.upsert_business(db, record(source_external_id='first', name=second['name'], address=second['address'], phone=second['phone']))
    assert a != b and before == [dict(row) for row in db.execute('SELECT * FROM businesses ORDER BY id')]


def test_confirmed_website_excludes_and_reimport_cannot_restore_lead(db):
    bid, _ = core.upsert_business(db, record())
    assert core.card(db, bid)['ready']
    core.upsert_business(db, record(website_status='found', website='https://example.org/official', website_evidence='СИНТЕТИЧЕСКАЯ проверка действующего сайта: телефон и профиль совпали'))
    found = core.card(db, bid)
    assert found['stage'] == 'исключён'
    assert found['website_status'] == 'found'
    assert found['exclusion_reason']
    assert not found['ready']
    # Even explicitly importing an active stage and negative check cannot reset exclusion.
    core.upsert_business(db, record(stage='готов к звонку', do_not_contact=False))
    after = core.card(db, bid)
    assert after['website_status'] == 'found'
    assert after['website'] == 'https://example.org/official'
    assert after['exclusion_reason'] == found['exclusion_reason']
    assert core.list_businesses(db, ready_only=True) == []


@pytest.mark.parametrize('status', ['unchecked', 'ambiguous'])
def test_unchecked_or_ambiguous_website_never_ready(db, status):
    r = record(website_status=status, website='https://example.org/candidate')
    bid, _ = core.upsert_business(db, r)
    c = core.card(db, bid)
    assert not c['ready']
    assert c['stage'] == 'требует проверки'


def test_directory_or_instagram_never_accepted_as_official_site(db):
    for candidate in ('https://instagram.com/synthetic', 'https://2gis.kz/pavlodar/firm/123'):
        with pytest.raises(ValueError, match='каталог или соцсеть'):
            core.upsert_business(db, record(website_status='found', website=candidate))
    assert count(db, 'businesses') == 0


def test_do_not_contact_survives_imports_and_renaming(db):
    bid, _ = core.upsert_business(db, record())
    core.prohibit(db, bid, 'СИНТЕТИЧЕСКИЙ запрет: не звонить')
    core.upsert_business(db, record(name='СИНТЕТИЧЕСКИЙ ребрендинг', stage='готов к звонку', do_not_contact=False))
    c = core.card(db, bid)
    assert c['do_not_contact'] == 1
    assert not c['ready']
    assert c['stage'] != 'готов к звонку'
    assert any(row['kind'] == 'do_not_contact' for row in c['interactions'])


@pytest.mark.parametrize('stage', ['связались', 'заинтересован', 'отказ', 'перезвонить', 'клиент', 'исключён'])
def test_processed_stage_not_reset_by_recollection(db, stage):
    bid, _ = core.upsert_business(db, record())
    core.interact(db, bid, stage, 'СИНТЕТИЧЕСКИЙ результат контакта')
    core.upsert_business(db, record(stage='новый'))
    c = core.card(db, bid)
    assert c['stage'] == stage
    assert not c['ready']
    assert len(c['interactions']) == 1


def test_benefit_is_not_demand_and_manual_conversation_creates_actual_demand(db):
    bid, _ = core.upsert_business(db, record())
    c = core.card(db, bid)
    assert c['priority_factors']['likely_benefit'] > 0
    assert c['priority_factors']['confirmed_demand'] == 0
    assert {s['signal_type'] for s in c['signals']} == {'likely_benefit'}
    core.interact(db, bid, 'заинтересован', 'СИНТЕТИЧЕСКИЙ разговор: попросили предложение')
    c = core.card(db, bid)
    assert c['priority_factors']['confirmed_demand'] > 0
    assert {s['signal_type'] for s in c['signals']} == {'likely_benefit', 'confirmed_demand'}
    assert any(e['url'] == 'manual://conversation' for e in c['evidence'])
    assert not c['ready']  # already contacted; never offered as a new cold lead


def test_public_demand_requires_quote_url_and_date(db):
    for missing in ('signal_quote', 'signal_url', 'signal_date'):
        r = record(signal_type='confirmed_demand', signal_quote='СИНТЕТИЧЕСКАЯ цитата: ищем разработчика сайта', signal_url='https://example.org/synthetic/request')
        r.pop(missing)
        with pytest.raises(ValueError):
            core.upsert_business(db, r)
    assert count(db, 'businesses') == 0


def test_stale_signals_and_stale_website_checks_block_calls(db, monkeypatch):
    monkeypatch.setenv('FLARE_DATA_FRESH_DAYS', '5')
    monkeypatch.setenv('FLARE_BENEFIT_FRESH_DAYS', '5')
    bid, _ = core.upsert_business(db, record(website_checked_at=date_ago(6), signal_date=date_ago(6)))
    c = core.card(db, bid)
    assert not c['ready']
    assert c['priority_factors']['likely_benefit'] == 0
    assert any('Проверка сайта устарела' in blocker for blocker in c['blockers'])
    assert c['signals'][0]['current'] is False


def test_missing_phone_confirmation_blocks_calls_even_with_high_score(db):
    bid, _ = core.upsert_business(db, record(phone_verified=False, confidence=1))
    c = core.card(db, bid)
    assert c['data_quality'] == 100
    assert c['priority_factors']['verified_business_phone'] == 0
    assert not c['ready']


def test_deleted_processed_business_keeps_only_hashed_suppression_and_cannot_return(db):
    r = record()
    bid, _ = core.upsert_business(db, r)
    core.prohibit(db, bid, 'СИНТЕТИЧЕСКИЙ запрет')
    core.delete_business(db, bid)
    assert count(db, 'businesses') == 0
    assert count(db, 'contacts') == 0
    assert count(db, 'evidence') == 0
    assert count(db, 'observations') == 0
    assert count(db, 'interactions') == 0
    assert count(db, 'identities') == 0
    rows = [dict(row) for row in db.execute('SELECT * FROM suppressions')]
    assert rows and all(len(row['digest']) == 64 for row in rows)
    assert all(r['phone'] not in str(row) and r['name'] not in str(row) for row in rows)
    new_bid, _ = core.upsert_business(db, record(name='СИНТЕТИЧЕСКОЕ новое имя', do_not_contact=False))
    c = core.card(db, new_bid)
    assert c['do_not_contact'] == 1
    assert c['stage'] == 'исключён'
    assert not c['ready']


def test_history_retains_old_name_and_website_observation(db):
    bid, _ = core.upsert_business(db, record(observed_at=date_ago(2)))
    core.upsert_business(db, record(name='СИНТЕТИЧЕСКИЙ ребрендинг', observed_at=date_ago(1), website='https://example.org/candidate', website_status='ambiguous'))
    c = core.card(db, bid)
    names = {o['payload']['name'] for o in c['observations'] if o['kind'] == 'facts'}
    assert names == {'СИНТЕТИЧЕСКОЕ кафе Альфа', 'СИНТЕТИЧЕСКИЙ ребрендинг'}
    assert len(c['evidence']) == 2
    assert count(db, 'businesses') == 1


def test_repeated_interested_note_same_second_has_distinct_evidence(db, monkeypatch):
    bid, _ = core.upsert_business(db, record())
    frozen = date_ago()
    monkeypatch.setattr(core, 'now', lambda: frozen)
    note = 'СИНТЕТИЧЕСКИЙ повторный разговор: интерес подтверждён'
    core.interact(db, bid, 'заинтересован', note)
    core.interact(db, bid, 'заинтересован', note)
    c = core.card(db, bid)
    assert len(c['interactions']) == 2
    conversations = [e for e in c['evidence'] if e['url'] == 'manual://conversation']
    assert len(conversations) == 2
    assert len({e['fingerprint'] for e in conversations}) == 2
    demands = [s for s in c['signals'] if s['signal_type'] == 'confirmed_demand']
    assert len(demands) == 2


def test_verified_business_phone_requires_source_url(db):
    r = record(website_status='unchecked')
    r.pop('source_url')
    with pytest.raises(ValueError, match='контакт требует URL источника'):
        core.upsert_business(db, r)
    assert count(db, 'businesses') == 0


@pytest.mark.parametrize('role', ['owner', 'manager'])
def test_owner_or_manager_phone_requires_confirmed_identity_not_just_boolean(db, role):
    r = record(phone_type=role, contact_verified=True)
    with pytest.raises(ValueError):
        core.upsert_business(db, r)
    assert count(db, 'businesses') == 0


def test_recollection_cannot_erase_confirmed_website_with_negative_or_unchecked_status(db):
    from flare.sources import collect_sources

    found = record(website_status='found', website='https://example.org/official')
    bid, _ = core.upsert_business(db, found, source_name='osm')
    for status in ('not_found', 'unchecked', 'ambiguous'):
        r = record(website_status=status)
        if status == 'ambiguous':
            r['website'] = 'https://example.org/other-candidate'
        report = collect_sources(db, 'Павлодар', 'кафе', ['osm'], fetcher=lambda *_: [r])
        assert report[0]['status'] == 'completed'
        c = core.card(db, bid)
        assert c['website_status'] == 'found'
        assert c['website'] == 'https://example.org/official'
        assert c['stage'] == 'исключён'
        assert not c['ready']
        assert count(db, 'businesses') == 1


def test_processed_history_prevents_requalification_after_explicit_stage_reset(db):
    r = record()
    bid, _ = core.upsert_business(db, r)
    assert core.card(db, bid)['ready']
    core.interact(db, bid, 'связались', 'СИНТЕТИЧЕСКИЙ состоявшийся контакт')
    core.interact(db, bid, 'новый', 'СИНТЕТИЧЕСКОЕ ошибочное возвращение стадии')
    core.upsert_business(db, record(stage='готов к звонку'))
    c = core.card(db, bid)
    assert not c['ready']
    assert core.list_businesses(db, ready_only=True) == []
    assert any('уже обработан' in reason for reason in c['blockers'])
    assert len(c['interactions']) == 2
    # Even deleting a card with a reset stage retains suppression of repeat processing.
    core.delete_business(db, bid)
    reimported, _ = core.upsert_business(db, r)
    assert core.card(db, reimported)['stage'] == 'исключён'
    assert not core.card(db, reimported)['ready']


def test_imported_processed_stage_cannot_be_forgotten_by_explicit_reset(db):
    bid, _ = core.upsert_business(db, record(stage='связались'))
    assert not core.card(db, bid)['ready']
    core.interact(db, bid, 'новый', 'СИНТЕТИЧЕСКИЙ сброс стадии CRM')
    core.upsert_business(db, record(stage='новый'))
    c = core.card(db, bid)
    assert not c['ready']
    assert core.list_businesses(db, ready_only=True) == []
    assert any('уже обработан' in reason for reason in c['blockers'])
