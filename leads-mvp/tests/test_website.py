"""Только синтетические фирмы и HTML; реальные сайты не запрашиваются."""
from unittest.mock import patch

import pytest

from flare import core
from flare.db import connect, migrate
from flare.website import WebsiteError, _public_url, check_website


@pytest.fixture
def conn():
    conn = connect(':memory:')
    migrate(conn)
    yield conn
    conn.close()


def candidate(conn, **patch):
    record = {
        'source_external_id': 'SYNTHETIC:website-1', 'name': 'СИНТЕТИЧЕСКОЕ Кафе Тест',
        'category': 'кафе', 'city': 'Павлодар', 'address': 'Синтетическая улица, 123',
        'website': 'https://synthetic.example.org', 'phone': '+7 777 123 45 67',
        'source_url': 'https://synthetic.example.org/profile', 'phone_verified': False,
    }
    record.update(patch)
    return core.upsert_business(conn, record, source_name='synthetic')[0]


def test_matching_html_is_signal_but_never_automatically_found(conn):
    bid = candidate(conn)
    result = check_website(conn, bid, fetcher=lambda url: {
        'url': url,
        'html': '<html><body>СИНТЕТИЧЕСКОЕ Кафе Тест Павлодар <a href="tel:+77771234567">Звонок</a></body></html>',
    })
    assert result['recommended_found'] is True
    assert result['name_match'] and result['city_match'] and result['phone_match']
    card = core.card(conn, bid)
    assert card['website_status'] == 'ambiguous'
    assert not card['ready']
    assert 'HTML-страница доступна' in card['evidence'][-1]['excerpt']


def test_different_business_is_ambiguous(conn):
    bid = candidate(conn)
    result = check_website(conn, bid, fetcher=lambda url: {'url': url, 'html': '<h1>Иная СИНТЕТИЧЕСКАЯ компания</h1>'})
    assert result['recommended_found'] is False
    assert core.card(conn, bid)['website_status'] == 'ambiguous'


def test_unavailable_candidate_does_not_prove_absence(conn):
    bid = candidate(conn)

    def unavailable(url):
        raise WebsiteError('access_denied')

    result = check_website(conn, bid, fetcher=unavailable)
    assert result['status'] == 'unavailable'
    assert result['error'] == 'access_denied'
    assert core.card(conn, bid)['website_status'] == 'ambiguous'


def test_no_candidate_does_not_make_negative_finding(conn):
    bid = candidate(conn, website='')
    result = check_website(conn, bid, fetcher=lambda _: pytest.fail('network not expected'))
    assert result['status'] == 'no_candidate'
    assert core.card(conn, bid)['website_status'] == 'unchecked'


def test_found_site_never_downgraded(conn):
    bid = candidate(conn, website_status='found', website_checked_at=core.now(),
                    website_check_source='Синтетическая ручная проверка',
                    website_evidence='Синтетическая проверка контактов и ссылки из профиля',
                    website_check_methods=['profile', 'contacts'])
    result = check_website(conn, bid, fetcher=lambda _: pytest.fail('network not expected'))
    assert result['status'] == 'already_excluded'
    assert core.card(conn, bid)['stage'] == 'исключён'


def test_dns_private_ip_rejected():
    with patch('flare.website.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
        with pytest.raises(WebsiteError, match='non_public_address'):
            _public_url('https://synthetic.example.org')


def test_directory_is_not_site():
    with patch('flare.website.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('8.8.8.8', 443))]):
        with pytest.raises(WebsiteError, match='profile_is_not_website'):
            _public_url('https://instagram.com/synthetic')


def test_script_contacts_not_used(conn):
    bid = candidate(conn)
    result = check_website(conn, bid, fetcher=lambda url: {'url': url, 'html':
        '<script>СИНТЕТИЧЕСКОЕ Кафе Тест Павлодар +77771234567</script><h1>Пусто</h1>'})
    assert not result['recommended_found']
    assert not result['phone_match']


def test_robots_disallow_blocks_page_fetch(monkeypatch):
    import flare.website as website

    monkeypatch.setattr(website, '_public_url', lambda url: url)
    seen = []

    def get(url, **kwargs):
        seen.append(url)
        return url, 200, 'text/plain', 'User-agent: *\nDisallow: /'

    monkeypatch.setattr(website, '_get', get)
    with pytest.raises(WebsiteError, match='robots_disallowed'):
        website._fetch_public_html('https://synthetic.example.org')
    assert seen == ['https://synthetic.example.org/robots.txt']


def test_redirect_to_new_host_blocked_before_target_fetch(monkeypatch):
    import flare.website as website

    monkeypatch.setattr(website, '_public_url', lambda url: url)
    monkeypatch.setattr(website.time, 'sleep', lambda _: None)
    seen = []

    class Redirect:
        status_code = 302
        headers = {'Location': 'https://another-synthetic.example.org'}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def get(url, **kwargs):
        seen.append(url)
        return Redirect()

    monkeypatch.setattr(website.requests, 'get', get)
    with pytest.raises(WebsiteError, match='cross_origin_redirect_requires_review'):
        website._get('https://synthetic.example.org')
    assert seen == ['https://synthetic.example.org']
