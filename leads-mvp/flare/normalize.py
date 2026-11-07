import ipaddress
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit


def text_key(value):
    return ' '.join(re.sub(r'[^\w\s]', ' ', unicodedata.normalize('NFKC', str(value)).casefold().replace('ё', 'е')).split())


def phone(value):
    digits = re.sub(r'\D', '', str(value))
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    if len(digits) == 10:
        digits = '7' + digits
    # Казахстан: коды 6xx и 7xx; российские номера не принимаются как KZ.
    if len(digits) != 11 or not re.fullmatch(r'7[67]\d{9}', digits):
        raise ValueError('Некорректный телефон Казахстана')
    return '+' + digits


def url(value):
    value = str(value).strip()
    if '://' not in value:
        value = 'https://' + value
    parts = urlsplit(value)
    if parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Некорректный публичный URL')
    host = parts.hostname.encode('idna').decode('ascii').lower().rstrip('.')
    if '.' not in host or host.endswith(('.local', '.localhost', '.internal')):
        raise ValueError('Требуется публичный URL')
    try:
        if not ipaddress.ip_address(host).is_global:
            raise ValueError('Локальные адреса запрещены')
    except ValueError as exc:
        if str(exc) == 'Локальные адреса запрещены':
            raise
    port = parts.port
    netloc = host if port in (None, 80, 443) else f'{host}:{port}'
    return urlunsplit((parts.scheme.lower(), netloc, parts.path.rstrip('/'), parts.query, ''))


def is_profile(value):
    host = urlsplit(value).hostname or ''
    domains = ('instagram.com','facebook.com','vk.com','t.me','2gis.kz','2gis.ru','yandex.kz','yandex.ru','maps.google.com','google.com','wa.me','whatsapp.com')
    return any(host == d or host.endswith('.' + d) for d in domains)
