"""Ограниченная проверка указанного сайта, без поискового скрейпинга.

HTTP-доступность и совпадения — наблюдения, а не доказательство принадлежности.
Автопроверка всегда оставляет кандидата на ручной проверке.
"""
from __future__ import annotations

import ipaddress
import os
import re
import socket
import time
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests

from . import normalize as norm

USER_AGENT = 'FlareStudioLocalMVP/0.1'
MAX_BYTES = 1_000_000
_LAST_REQUEST = 0.0


class WebsiteError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _public_url(value):
    try:
        value = norm.url(value)
        parsed = urlsplit(value)
        if parsed.port not in (None, 80, 443):
            raise WebsiteError('unsupported_port')
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise WebsiteError('non_public_address')
        if norm.is_profile(value):
            raise WebsiteError('profile_is_not_website')
        return value
    except WebsiteError:
        raise
    except (ValueError, OSError, UnicodeError):
        raise WebsiteError('invalid_or_unresolved_url') from None


def _settings():
    try:
        return (max(1, min(30, float(os.getenv('FLARE_HTTP_TIMEOUT', '15')))),
                max(1, min(10, float(os.getenv('FLARE_REQUEST_INTERVAL', '2')))),
                max(0, min(2, int(os.getenv('FLARE_HTTP_RETRIES', '1')))))
    except ValueError:
        raise WebsiteError('invalid_network_configuration') from None


def _get(value, max_bytes=MAX_BYTES, *, same_origin=True):
    """Проверяет адрес каждого редиректа; не сохраняет тело ответа/ошибки."""
    global _LAST_REQUEST
    timeout, interval, retries = _settings()
    current = value
    original_origin = urlsplit(value).netloc
    for redirect in range(4):
        current = _public_url(current)
        for attempt in range(retries + 1):
            time.sleep(max(0, interval - (time.monotonic() - _LAST_REQUEST)))
            _LAST_REQUEST = time.monotonic()
            try:
                with requests.get(current, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,text/plain'},
                                  timeout=timeout, allow_redirects=False, stream=True) as response:
                    status = response.status_code
                    if status in (301, 302, 303, 307, 308):
                        location = response.headers.get('Location')
                        if not location:
                            raise WebsiteError('invalid_redirect')
                        current = urljoin(current, location)
                        if same_origin and urlsplit(current).netloc != original_origin:
                            raise WebsiteError('cross_origin_redirect_requires_review')
                        break
                    if status in (401, 403):
                        raise WebsiteError('access_denied')
                    if status == 429:
                        # Do not retry at a rate-limited source or bypass its restriction.
                        raise WebsiteError('rate_limited')
                    if status >= 500:
                        if attempt < retries:
                            continue
                        raise WebsiteError('upstream_unavailable')
                    chunks, size = [], 0
                    for chunk in response.iter_content(chunk_size=16384):
                        size += len(chunk)
                        if size > max_bytes:
                            raise WebsiteError('response_too_large')
                        chunks.append(chunk)
                    content = b''.join(chunks).decode(response.encoding or 'utf-8', errors='replace')
                    return current, status, response.headers.get('Content-Type', '').lower(), content
            except requests.RequestException:
                if attempt == retries:
                    raise WebsiteError('network_unavailable') from None
        else:
            raise WebsiteError('network_unavailable')
    raise WebsiteError('too_many_redirects')


def _fetch_public_html(value):
    value = _public_url(value)
    parts = urlsplit(value)
    robots_url = f'{parts.scheme}://{parts.netloc}/robots.txt'
    _, status, _, robots = _get(robots_url, max_bytes=100_000)
    if status not in (404, 410):
        if status != 200:
            raise WebsiteError('robots_unavailable')
        parser = RobotFileParser()
        parser.parse(robots.splitlines())
        if not parser.can_fetch(USER_AGENT, value):
            raise WebsiteError('robots_disallowed')
        # Honour a bounded crawl delay. Larger delays require a later manual run.
        delay = parser.crawl_delay(USER_AGENT) or parser.crawl_delay('*') or 0
        if delay > 30:
            raise WebsiteError('robots_crawl_delay')
        if delay:
            time.sleep(delay)
    final_url, status, content_type, html = _get(value)
    # A redirect to a new origin requires a separate policy check; do not fetch it again.
    if urlsplit(final_url).netloc != parts.netloc:
        raise WebsiteError('cross_origin_redirect_requires_review')
    if status != 200:
        raise WebsiteError('website_http_error')
    if 'text/html' not in content_type:
        raise WebsiteError('not_html')
    return {'url': final_url, 'html': html}


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript'):
            self.ignored += 1
        if tag == 'a':
            # tel links are explicitly published business-contact evidence candidates.
            for key, value in attrs:
                if key == 'href' and value and value.lower().startswith('tel:'):
                    self.parts.append(value[4:])

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.ignored = max(0, self.ignored - 1)

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def check_website(conn, bid, *, fetcher=None):
    """Проверяет только явно указанный URL; отсутствие сайта не устанавливает."""
    from . import core

    row = conn.execute('SELECT * FROM businesses WHERE id=?', (bid,)).fetchone()
    if not row:
        raise ValueError('Бизнес не найден')
    if row['website_status'] == 'found':
        return {'status': 'already_excluded', 'recommended_found': True}
    if not row['website']:
        return {'status': 'no_candidate', 'recommended_found': False}
    website = row['website']
    summary = {'status': 'requires_review', 'recommended_found': False,
               'name_match': False, 'city_match': False, 'phone_match': False}
    try:
        result = (fetcher or _fetch_public_html)(website)
        parser = _VisibleText()
        parser.feed(result['html'])
        text = ' '.join(parser.parts)
        normalized = norm.text_key(text)
        summary['name_match'] = norm.text_key(row['name']) in normalized
        summary['city_match'] = norm.text_key(row['city']) in normalized
        # Compare complete normalized KZ phones, not a loose substring of page digits.
        page_phones = set()
        for candidate in re.findall(r'(?<!\d)(?:\+?7|8)[\s().-]*[67](?:[\s().-]*\d){9}(?!\d)', text):
            try:
                page_phones.add(norm.phone(candidate))
            except ValueError:
                pass
        known = {r[0] for r in conn.execute("SELECT value FROM contacts WHERE business_id=? AND kind IN ('phone','responsible')", (bid,))}
        summary['phone_match'] = bool(page_phones & known)
        summary['recommended_found'] = all(summary[k] for k in ('name_match', 'city_match', 'phone_match'))
        evidence = ('Публичная HTML-страница доступна. Совпадение названия: ' + ('да' if summary['name_match'] else 'нет') +
                    '; города: ' + ('да' if summary['city_match'] else 'нет') +
                    '; известного делового телефона: ' + ('да' if summary['phone_match'] else 'нет') +
                    '. Принадлежность требует ручного подтверждения и второго независимого способа проверки.')
        website = result['url']
    except WebsiteError as exc:
        summary['status'] = 'unavailable'
        summary['error'] = exc.code
        evidence = 'HTTP-проверка кандидата не завершена: ' + exc.code + '. Требуется ручная проверка; отсутствие сайта не установлено.'
    core.edit_business(conn, bid, {
        'website': website, 'website_status': 'ambiguous', 'website_checked_at': core.now(),
        'website_check_source': 'public_website_http', 'website_evidence': evidence,
        'website_check_methods': ['contacts'], 'source_url': website,
    }, source_name='public_website_http')
    return summary
