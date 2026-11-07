"""Правила квалификации. Сборщики не имеют полномочий снимать блокировки."""
import hashlib
import json
import os
import re
from datetime import datetime, timezone

from . import normalize as norm
from .db import get_source

STAGES = ('новый', 'требует проверки', 'готов к звонку', 'связались', 'заинтересован', 'отказ', 'перезвонить', 'клиент', 'исключён')
PROCESSED = STAGES[3:]
WEBSITE_LABELS = {'found': 'найден', 'not_found': 'не найден при проверке', 'unchecked': 'не проверено', 'ambiguous': 'не проверено: принадлежность неоднозначна'}


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def stamp(value):
    try:
        d = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        d = d.replace(tzinfo=d.tzinfo or timezone.utc).astimezone(timezone.utc)
        if d > datetime.now(timezone.utc):
            raise ValueError()
        return d.isoformat(timespec='seconds')
    except (ValueError, TypeError):
        raise ValueError('Некорректная дата или дата в будущем') from None


def age(value):
    if not value:
        return float('inf')
    return (datetime.now(timezone.utc) - datetime.fromisoformat(stamp(value))).total_seconds() / 86400


def number_env(key, default):
    result = int(os.getenv(key, default))
    if result < 0:
        raise ValueError('Порог или вес не может быть отрицательным')
    return result


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def pack(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def validate_record(record):
    r = {k: v for k, v in record.items() if v is not None and v != ''}
    for key in ('name', 'city', 'category'):
        if not str(r.get(key, '')).strip():
            raise ValueError('Обязательные поля: name, city, category')
        r[key] = str(r[key]).strip()
        if len(r[key]) > 300:
            raise ValueError('Слишком длинное поле бизнес-данных')
    r.setdefault('address', '')
    r['address'] = str(r['address']).strip()
    if len(r['address']) > 500:
        raise ValueError('Слишком длинный адрес')
    for key in ('phone_verified', 'whatsapp_verified', 'contact_verified', 'do_not_contact'):
        if key in r and not isinstance(r[key], bool):
            raise ValueError('Флаг подтверждения должен быть true/false')
    for key in ('phone', 'whatsapp'):
        if key in r:
            r[key] = norm.phone(r[key])
    if r.get('whatsapp') and not r.get('whatsapp_verified'):
        raise ValueError('WhatsApp допустим только при явном подтверждении')
    if r.get('email') and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', str(r['email'])):
        raise ValueError('Некорректный email')
    for key in ('source_url', 'profile_url', 'website', 'signal_url'):
        if r.get(key):
            r[key] = norm.url(r[key])
    r['observed_at'] = stamp(r.get('observed_at', now()))
    try:
        r['confidence'] = float(r.get('confidence', 0.5))
    except (TypeError, ValueError):
        raise ValueError('Уверенность должна быть числом от 0 до 1') from None
    if not 0 <= r['confidence'] <= 1:
        raise ValueError('Уверенность должна быть в диапазоне 0..1')
    if any(r.get(k) for k in ('phone_verified', 'whatsapp_verified', 'contact_verified')) and not r.get('source_url'):
        raise ValueError('Подтверждённый контакт требует URL источника')
    for key in ('website_evidence', 'signal_quote', 'signal_reason', 'exclusion_reason', 'excerpt'):
        if key in r and len(str(r[key])) > 600:
            raise ValueError('Выдержка или причина длиннее 600 символов')
    if r.get('contact_verified') or r.get('contact_name') or r.get('contact_business') or r.get('contact_role'):
        if not all(r.get(k) for k in ('contact_verified', 'contact_name', 'contact_role', 'contact_business', 'source_url')):
            raise ValueError('Контакт ответственного требует имени, роли, делового контакта, источника и подтверждения')
        # Не сохраняем догадки о личности; только телефон или деловой email.
        if '@' in str(r['contact_business']):
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', r['contact_business']):
                raise ValueError('Некорректный деловой email ответственного')
        else:
            r['contact_business'] = norm.phone(r['contact_business'])
    status = r.setdefault('website_status', 'unchecked')
    if status not in WEBSITE_LABELS:
        raise ValueError('Неизвестный статус сайта')
    if status in ('found', 'not_found', 'ambiguous'):
        for key in ('website_checked_at', 'website_check_source', 'website_evidence', 'source_url'):
            if not r.get(key):
                raise ValueError('Проверка сайта требует даты, источника, URL и краткого доказательства')
        r['website_checked_at'] = stamp(r['website_checked_at'])
        methods = r.get('website_check_methods', [])
        if isinstance(methods, str):
            methods = [m.strip() for m in methods.split(';') if m.strip()]
        r['website_check_methods'] = sorted(set(methods))
        if status in ('found', 'not_found') and len(set(methods) & {'search', 'profile', 'contacts'}) < 2:
            raise ValueError('Нужны минимум два способа проверки сайта: search, profile, contacts')
        if status == 'found' and (not r.get('website') or norm.is_profile(r['website'])):
            raise ValueError('Нужен действующий официальный сайт, а не каталог или соцсеть')
        if status == 'not_found' and r.get('website'):
            raise ValueError('Кандидат сайта требует found или ambiguous, а не not_found')
    if r.get('signal_type'):
        if r['signal_type'] not in ('confirmed_demand', 'likely_benefit'):
            raise ValueError('Неизвестный тип сигнала')
        if not r.get('signal_date'):
            raise ValueError('Сигнал требует даты')
        r['signal_date'] = stamp(r['signal_date'])
        if r['signal_type'] == 'confirmed_demand' and not all(r.get(k) for k in ('signal_quote', 'signal_url')):
            raise ValueError('Подтверждённый публичный спрос требует цитаты, URL и даты')
        if r['signal_type'] == 'likely_benefit' and not r.get('signal_reason'):
            raise ValueError('Гипотеза требует объяснения пользы сайта')
    if r.get('stage') and r['stage'] not in STAGES:
        raise ValueError('Неизвестная стадия')
    if r.get('phone_type', 'business') not in ('business', 'owner', 'manager'):
        raise ValueError('Тип телефона: business, owner, manager')
    if r.get('phone_type') in ('owner', 'manager') and (not r.get('contact_verified') or r.get('contact_business') != r.get('phone')):
        raise ValueError('Телефон владельца или руководителя требует подтверждения личности')
    return r


def identity_keys(r, source_name):
    keys = []
    location = norm.text_key(r['city']) + '|' + norm.text_key(r.get('address', ''))
    if r.get('source_external_id'):
        keys.append(('source', source_name + ':' + str(r['source_external_id'])))
    # Номер сети/общий сайт не является идентификатором филиала.
    if r.get('address'):
        if r.get('phone'):
            keys.append(('phone_location', r['phone'] + '|' + location))
        if r.get('profile_url'):
            keys.append(('profile_location', r['profile_url'] + '|' + location))
        keys.append(('name_location', norm.text_key(r['name']) + '|' + location))
    if not keys:
        # Идемпотентная запись без адреса/устойчивого ID остаётся неподтверждённой.
        keys.append(('weak', source_name + '|' + norm.text_key(r['name']) + '|' + location + '|' + r.get('phone', '') + '|' + r.get('profile_url', '')))
    return keys


def add_observation(conn, bid, eid, kind, payload, observed_at):
    encoded = pack(payload)
    fp = digest(f'{bid}|{eid}|{kind}|{encoded}|{observed_at}')
    conn.execute('INSERT OR IGNORE INTO observations(business_id,evidence_id,kind,payload,observed_at,fingerprint) VALUES (?,?,?,?,?,?)',
                 (bid, eid, kind, encoded, observed_at, fp))


def upsert_business(conn, record, source_name='import'):
    """Atomicity belongs to caller; all validation precedes mutations."""
    r = validate_record(record)
    keys = identity_keys(r, source_name)
    matches = set()
    for kind, value in keys:
        row = conn.execute('SELECT business_id FROM identities WHERE kind=? AND value=?', (kind, value)).fetchone()
        if row:
            matches.add(row[0])
    if len(matches) > 1:
        raise ValueError('Конфликт идентификаторов: требуется ручное разрешение, записи не объединены')
    created = not matches
    if matches:
        bid = matches.pop()
        old = dict(conn.execute('SELECT * FROM businesses WHERE id=?', (bid,)).fetchone())
    else:
        bid = conn.execute('INSERT INTO businesses(name,normalized_name,category,city,address,created_at,updated_at) VALUES (?,?,?,?,?,?,?)',
                           (r['name'], norm.text_key(r['name']), r['category'], r['city'], r['address'], now(), now())).lastrowid
        old = dict(conn.execute('SELECT * FROM businesses WHERE id=?', (bid,)).fetchone())
    for kind, value in keys:
        conn.execute('INSERT OR IGNORE INTO identities VALUES (?,?,?)', (kind, value, bid))
    sid = get_source(conn, source_name)
    excerpt = str(r.get('website_evidence') or r.get('signal_quote') or r.get('signal_reason') or r.get('excerpt') or 'Импорт/наблюдение бизнес-данных; подтверждения только явно указанные')[:600]
    evidence_url = r.get('source_url', 'manual://import')
    fp = digest(pack([bid, sid, evidence_url, r['observed_at'], excerpt, r['confidence']]))
    conn.execute('INSERT OR IGNORE INTO evidence(business_id,source_id,url,observed_at,excerpt,confidence,fingerprint) VALUES (?,?,?,?,?,?,?)',
                 (bid, sid, evidence_url, r['observed_at'], excerpt, r['confidence'], fp))
    eid = conn.execute('SELECT id FROM evidence WHERE fingerprint=?', (fp,)).fetchone()[0]
    add_observation(conn, bid, eid, 'facts', r, r['observed_at'])
    if r.get('signal_type'):
        add_observation(conn, bid, eid, 'signal', {k: v for k, v in r.items() if k.startswith('signal_')}, r['signal_date'])
    # Сохраняем все контакты; обновление не превращает непроверенный контакт в проверенный.
    values = [('phone', r.get('phone'), r.get('phone_type', 'business'), r.get('phone_verified', False)),
              ('whatsapp', r.get('whatsapp'), 'business', r.get('whatsapp_verified', False)),
              ('email', r.get('email'), 'business', False), ('profile', r.get('profile_url'), 'business', False)]
    if r.get('contact_verified') and r.get('contact_business'):
        values.append(('responsible', r['contact_business'], r['contact_role'], True))
        add_observation(conn, bid, eid, 'responsible', {k: r[k] for k in ('contact_name', 'contact_role', 'contact_business')}, r['observed_at'])
    for kind, value, role, verified in values:
        if value:
            conn.execute('''INSERT INTO contacts(business_id,kind,value,role,verified,evidence_id) VALUES (?,?,?,?,?,?)
             ON CONFLICT(business_id,kind,value,role) DO UPDATE SET
             evidence_id=CASE WHEN excluded.verified>=contacts.verified THEN excluded.evidence_id ELSE contacts.evidence_id END,
             verified=MAX(contacts.verified,excluded.verified)''', (bid, kind, value, role, int(verified), eid))
    updates = {k: old[k] for k in ('name','normalized_name','category','city','address','website','website_status','website_checked_at','website_check_source','stage','do_not_contact','exclusion_reason')}
    # Не заменяем новую проекцию старыми данными; сами наблюдения остаются.
    last = conn.execute("SELECT MAX(observed_at) FROM observations WHERE business_id=? AND kind='facts'", (bid,)).fetchone()[0]
    if r['observed_at'] >= last:
        updates.update({k: r[k] for k in ('name','category','city')})
        updates['normalized_name'] = norm.text_key(r['name'])
        if r['address']:
            updates['address'] = r['address']
    # Подтверждённый сайт — устойчивое исключение; обычный импорт его не отменяет.
    if old['website_status'] != 'found':
        status = r['website_status']
        newer_check = r.get('website_checked_at', '') >= (old['website_checked_at'] or '')
        if status != 'unchecked' and (newer_check or status == 'found'):
            updates.update(website_status=status, website=r.get('website'), website_checked_at=r.get('website_checked_at'), website_check_source=r.get('website_check_source'))
        elif r.get('website') and r.get('website') != old['website']:
            updates.update(website=r['website'], website_status='ambiguous', website_checked_at=None, website_check_source=source_name)
    updates['do_not_contact'] = int(old['do_not_contact'] or r.get('do_not_contact', False))
    if created or old['stage'] not in PROCESSED:
        updates['stage'] = r.get('stage', old['stage'])
    if r.get('exclusion_reason'):
        updates['exclusion_reason'] = old['exclusion_reason'] or r['exclusion_reason']
        updates['stage'] = 'исключён'
    if updates['stage'] == 'исключён' and not updates['exclusion_reason']:
        updates['exclusion_reason'] = 'Исключён при импорте/обработке'
    for kind, value in keys:
        suppressed = conn.execute('SELECT * FROM suppressions WHERE digest=?', (digest(kind + '|' + value),)).fetchone()
        if suppressed:
            updates.update(stage='исключён', exclusion_reason=suppressed['reason'])
            updates['do_not_contact'] |= suppressed['do_not_contact']
    if updates['website_status'] == 'found':
        updates.update(stage='исключён', exclusion_reason=old['exclusion_reason'] or 'Подтверждён действующий официальный сайт')
    updates['updated_at'] = now()
    conn.execute('UPDATE businesses SET ' + ','.join(k + '=?' for k in updates) + ' WHERE id=?', (*updates.values(), bid))
    if updates['stage'] in PROCESSED and (created or old['stage'] != updates['stage']):
        conn.execute('INSERT INTO interactions(business_id,occurred_at,kind,outcome,note) VALUES (?,?,?,?,?)',
                     (bid, r['observed_at'], 'import', updates['stage'], 'Стадия сохранена при обновлении данных'))
    refresh_stage(conn, bid)
    return bid, created


def qualification(conn, bid):
    b = conn.execute('SELECT * FROM businesses WHERE id=?', (bid,)).fetchone()
    if not b:
        raise ValueError('Бизнес не найден')
    fresh_days = number_env('FLARE_DATA_FRESH_DAYS', 90)
    contacts = conn.execute('SELECT c.*,e.observed_at,e.confidence FROM contacts c JOIN evidence e ON e.id=c.evidence_id WHERE c.business_id=?', (bid,)).fetchall()
    has_phone = any(c['kind'] in ('phone', 'responsible') and c['verified'] and c['value'].startswith('+7') and age(c['observed_at']) <= fresh_days for c in contacts)
    facts = conn.execute("SELECT e.confidence,o.observed_at FROM observations o JOIN evidence e ON e.id=o.evidence_id WHERE o.business_id=? AND o.kind='facts' ORDER BY o.observed_at DESC,o.id DESC LIMIT 1", (bid,)).fetchone()
    fresh = bool(facts and age(facts['observed_at']) <= fresh_days)
    signals = []
    for row in conn.execute("SELECT payload,observed_at FROM observations WHERE business_id=? AND kind='signal' ORDER BY observed_at DESC,id DESC", (bid,)):
        s = json.loads(row['payload'])
        days = number_env('FLARE_DEMAND_FRESH_DAYS', 30) if s['signal_type'] == 'confirmed_demand' else number_env('FLARE_BENEFIT_FRESH_DAYS', 180)
        s['current'] = age(row['observed_at']) <= days
        signals.append(s)
    demand = any(s['signal_type'] == 'confirmed_demand' and s['current'] for s in signals)
    benefit = any(s['signal_type'] == 'likely_benefit' and s['current'] for s in signals)
    factors = {'confirmed_demand': number_env('FLARE_SCORE_DEMAND', 40) if demand else 0,
               'likely_benefit': number_env('FLARE_SCORE_BENEFIT', 20) if benefit else 0,
               'verified_business_phone': number_env('FLARE_SCORE_CONTACT', 25) if has_phone else 0,
               'fresh_data': number_env('FLARE_SCORE_FRESHNESS', 15) if fresh else 0}
    blockers = []
    if b['do_not_contact']:
        blockers.append('Установлен запрет контакта')
    if b['website_status'] != 'not_found':
        blockers.append('Нет однозначной проверки отсутствия найденного официального сайта')
    elif age(b['website_checked_at']) > fresh_days:
        blockers.append('Проверка сайта устарела')
    if not b['address']:
        blockers.append('Не установлен адрес/филиал')
    if not has_phone:
        blockers.append('Нет свежего подтверждённого делового телефона')
    if not fresh:
        blockers.append('Бизнес-данные устарели')
    if not (demand or benefit):
        blockers.append('Нет актуального спроса или обоснованной гипотезы пользы')
    processed_history = conn.execute(
        'SELECT 1 FROM interactions WHERE business_id=? AND outcome IN (' + ','.join('?' for _ in PROCESSED) + ') LIMIT 1',
        (bid, *PROCESSED)).fetchone()
    if b['stage'] in PROCESSED or processed_history:
        blockers.append('Бизнес уже обработан: ' + b['stage'])
    if b['exclusion_reason']:
        blockers.append('Исключение: ' + b['exclusion_reason'])
    quality = round((facts['confidence'] if facts else 0) * 100)
    return dict(ready=not blockers, priority=sum(factors.values()), priority_factors=factors,
                data_quality=quality, data_quality_note='Уверенность последнего факта, не вероятность покупки',
                signals=signals, blockers=blockers,
                next_step='Ручной звонок по опубликованному деловому телефону' if not blockers else blockers[0])


def refresh_stage(conn, bid):
    b = conn.execute('SELECT stage,website_status FROM businesses WHERE id=?', (bid,)).fetchone()
    if b['stage'] in PROCESSED:
        return
    q = qualification(conn, bid)
    conn.execute('UPDATE businesses SET stage=? WHERE id=?', ('готов к звонку' if q['ready'] else 'требует проверки', bid))


def card(conn, bid):
    b = conn.execute('SELECT * FROM businesses WHERE id=?', (bid,)).fetchone()
    if not b:
        raise ValueError('Бизнес не найден')
    refresh_stage(conn, bid)
    result = dict(conn.execute('SELECT * FROM businesses WHERE id=?', (bid,)).fetchone())
    result['website_status_label'] = WEBSITE_LABELS[result['website_status']]
    result.update(qualification(conn, bid))
    for table in ('contacts', 'evidence', 'observations', 'interactions'):
        result[table] = [dict(r) for r in conn.execute('SELECT * FROM ' + table + ' WHERE business_id=? ORDER BY id', (bid,))]
    for o in result['observations']:
        o['payload'] = json.loads(o['payload'])
    return result


def list_businesses(conn, ready_only=False, city=None, stage=None):
    ids = [r[0] for r in conn.execute('SELECT id FROM businesses ORDER BY id')]
    result = []
    for bid in ids:
        c = card(conn, bid)
        if ready_only and not c['ready']:
            continue
        if city and norm.text_key(c['city']) != norm.text_key(city):
            continue
        if stage and c['stage'] != stage:
            continue
        result.append(c)
    return sorted(result, key=lambda c: (-c['priority'], c['id']))


def interact(conn, bid, outcome, note='', kind='call'):
    b = conn.execute('SELECT * FROM businesses WHERE id=?', (bid,)).fetchone()
    if not b:
        raise ValueError('Бизнес не найден')
    if outcome not in STAGES:
        raise ValueError('Неизвестная стадия')
    if len(note) > 600:
        raise ValueError('Заметка длиннее 600 символов')
    if b['website_status'] == 'found' and outcome != 'исключён':
        raise ValueError('Бизнес с официальным сайтом остаётся исключённым')
    if outcome == 'готов к звонку' and not qualification(conn, bid)['ready']:
        raise ValueError('Бизнес не прошёл квалификацию')
    interaction_id = conn.execute('INSERT INTO interactions(business_id,occurred_at,kind,outcome,note) VALUES (?,?,?,?,?)', (bid, now(), kind, outcome, note)).lastrowid
    conn.execute('UPDATE businesses SET stage=?,updated_at=? WHERE id=?', (outcome, now(), bid))
    if outcome == 'заинтересован':
        sid = get_source(conn, 'manual_conversation')
        fp = digest(pack([bid, 'conversation', interaction_id]))
        eid = conn.execute('INSERT INTO evidence(business_id,source_id,url,observed_at,excerpt,confidence,fingerprint) VALUES (?,?,?,?,?,?,?)',
                           (bid, sid, 'manual://conversation', now(), note or 'Интерес отмечен пользователем после разговора', 1, fp)).lastrowid
        add_observation(conn, bid, eid, 'signal', {'signal_type': 'confirmed_demand', 'signal_date': now(), 'signal_quote': note or 'Интерес подтверждён после разговора', 'signal_url': 'manual://conversation'}, now())
    if outcome == 'исключён':
        conn.execute('UPDATE businesses SET exclusion_reason=COALESCE(exclusion_reason,?) WHERE id=?', (note or 'Исключён вручную', bid))


def prohibit(conn, bid, reason):
    if not reason or len(reason) > 600:
        raise ValueError('Нужна краткая причина запрета')
    if not conn.execute('SELECT 1 FROM businesses WHERE id=?', (bid,)).fetchone():
        raise ValueError('Бизнес не найден')
    conn.execute('UPDATE businesses SET do_not_contact=1,updated_at=? WHERE id=?', (now(), bid))
    conn.execute('INSERT INTO interactions(business_id,occurred_at,kind,outcome,note) VALUES (?,?,?,?,?)', (bid, now(), 'do_not_contact', 'запрет контакта', reason))
    refresh_stage(conn, bid)


def delete_business(conn, bid):
    b = conn.execute('SELECT * FROM businesses WHERE id=?', (bid,)).fetchone()
    if not b:
        raise ValueError('Бизнес не найден')
    has_history = conn.execute('SELECT 1 FROM interactions WHERE business_id=? LIMIT 1', (bid,)).fetchone()
    if b['do_not_contact'] or b['stage'] in PROCESSED or has_history:
        for row in conn.execute('SELECT kind,value FROM identities WHERE business_id=?', (bid,)):
            conn.execute('INSERT INTO suppressions VALUES (?,?,?) ON CONFLICT(digest) DO UPDATE SET do_not_contact=MAX(do_not_contact,excluded.do_not_contact)',
                         (digest(row['kind'] + '|' + row['value']), b['do_not_contact'], 'Удалённая ранее обработанная запись'))
    conn.execute('DELETE FROM businesses WHERE id=?', (bid,))


def edit_business(conn, bid, patch, source_name='manual'):
    """Явное ручное исправление; запреты и подтверждённый сайт остаются устойчивыми."""
    b = conn.execute('SELECT * FROM businesses WHERE id=?', (bid,)).fetchone()
    if not b:
        raise ValueError('Бизнес не найден')
    # Внутренний идентификатор позволяет менять имя/адрес без создания дубля.
    conn.execute('INSERT OR IGNORE INTO identities VALUES (?,?,?)', ('source', source_name + ':business:' + str(bid), bid))
    r = {k: b[k] for k in ('name', 'category', 'city', 'address')}
    r.update(patch)
    r['source_external_id'] = 'business:' + str(bid)
    return upsert_business(conn, r, source_name=source_name)
