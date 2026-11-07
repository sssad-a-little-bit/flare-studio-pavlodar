"""CLI не делает звонков/сообщений. Сетевые действия только collect и probe-site."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

from . import core, db


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def parser():
    p = argparse.ArgumentParser(prog='flare', description='Flare Studio — локальная база лидов. Контакт только вручную.')
    p.add_argument('--db', help='SQLite-файл (по умолчанию FLARE_DB или data/flare.sqlite3)')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('init', help='Применить миграции')
    for command in ('import', 'export'):
        cmd = sub.add_parser(command, help='Импорт CSV/XLSX' if command == 'import' else 'Экспорт CSV/XLSX')
        cmd.add_argument('file')
        if command == 'import':
            cmd.add_argument('--source', default='import', help='Стабильное имя CRM/источника для дедупликации')
        else:
            filters(cmd)
    cmd = sub.add_parser('collect', help='Разовый сбор разрешённых источников')
    cmd.add_argument('--city', required=True)
    cmd.add_argument('--category', required=True)
    cmd.add_argument('--sources', default='osm', help='Через запятую: osm,2gis,yandex,instagram')
    cmd.add_argument('--limit', type=int, default=20)
    cmd = sub.add_parser('list', help='Список с причинами допуска/блокировки')
    filters(cmd)
    cmd = sub.add_parser('show', help='Полная карточка с доказательствами и историей')
    cmd.add_argument('id', type=int)
    cmd.add_argument('--json', action='store_true', help='Машиночитаемая карточка с полной историей наблюдений')
    cmd = sub.add_parser('edit', help='Ручная корректировка полей из JSON (не сбрасывает запреты)')
    cmd.add_argument('id', type=int)
    cmd.add_argument('--file', required=True, help='JSON-объект полей как в CSV')
    cmd = sub.add_parser('verify-site', help='Записать результат выполненной человеком проверки сайта')
    cmd.add_argument('id', type=int)
    cmd.add_argument('--status', required=True, choices=('found','not_found','ambiguous'))
    cmd.add_argument('--website', help='Официальный сайт или кандидат')
    cmd.add_argument('--url', required=True, help='Публичный URL основного доказательства проверки')
    cmd.add_argument('--evidence', required=True, help='Краткие основания, до 600 символов')
    cmd.add_argument('--methods', required=True, help='Выполненные проверки через запятую: search,profile,contacts')
    cmd.add_argument('--checked-at', help='Дата фактической проверки ISO 8601, по умолчанию сейчас')
    cmd = sub.add_parser('probe-site', help='Проверить доступность кандидата и совпадение данных; затем нужна ручная проверка')
    cmd.add_argument('id', type=int)
    cmd = sub.add_parser('contact', help='Записать состоявшийся ручной контакт/заметку')
    cmd.add_argument('id', type=int)
    cmd.add_argument('--outcome', required=True, choices=core.STAGES)
    cmd.add_argument('--kind', choices=('call','meeting','note'), default='call')
    cmd.add_argument('--note', default='')
    cmd = sub.add_parser('block', help='Установить устойчивый запрет контакта')
    cmd.add_argument('id', type=int)
    cmd.add_argument('--reason', required=True)
    cmd = sub.add_parser('delete', help='Удалить карточку, контакты и доказательства; сохранить хеши запрета/обработки')
    cmd.add_argument('id', type=int)
    cmd = sub.add_parser('delete-contact', help='Удалить текущий контакт; прежние наблюдения остаются в истории')
    cmd.add_argument('id', type=int, help='ID контакта из карточки')
    sub.add_parser('attempts', help='Состояния и безопасные коды ошибок попыток сбора')
    return p



def render_card(c):
    interest = {'confirmed_demand': 'Подтверждённый спрос', 'likely_benefit': 'Гипотеза пользы сайта'}
    factors = {'confirmed_demand': 'актуальный спрос', 'likely_benefit': 'обоснованная польза',
               'verified_business_phone': 'проверенный телефон', 'fresh_data': 'свежие данные'}
    contact_kinds = {'phone': 'Телефон', 'whatsapp': 'WhatsApp', 'email': 'Email',
                     'profile': 'Бизнес-профиль', 'responsible': 'Деловой контакт ответственного'}
    lines = [f"#{c['id']} {c['name']}", f"{c['city']} · {c['category']} · {c['address'] or 'Адрес не установлен'}",
             f"Стадия: {c['stage']}. Запрет контакта: {'ДА' if c['do_not_contact'] else 'нет'}",
             f"Официальный сайт: {c['website_status_label']}. URL: {c['website'] or 'не установлен'}",
             f"Проверка сайта: {c['website_checked_at'] or 'не выполнена'}; источник: {c['website_check_source'] or '—'}",
             f"Причина исключения: {c['exclusion_reason'] or '—'}", '', 'Контакты:']
    for contact in c['contacts']:
        lines.append(f"  [{contact['id']}] {contact_kinds.get(contact['kind'], contact['kind'])}: {contact['value']} · "
                     f"{'подтверждён' if contact['verified'] else 'не подтверждён'}; роль: {contact['role']}; доказательство #{contact['evidence_id']}")
    if not c['contacts']:
        lines.append('  Нет опубликованных контактов в базе')
    current_people = {ct['value'] for ct in c['contacts'] if ct['kind'] == 'responsible' and ct['verified']}
    responsible = [o for o in c['observations'] if o['kind'] == 'responsible' and o['payload']['contact_business'] in current_people]
    if responsible:
        person = max(responsible, key=lambda o: (o['observed_at'], o['id']))['payload']
        lines.append(f"Ответственный: {person['contact_name']}; роль: {person['contact_role']}; деловой контакт: {person['contact_business']}")
    else:
        lines.append('Владелец/ответственный: не установлен')
    lines.extend(['', 'Сигналы и польза сайта:'])
    for signal in c['signals']:
        lines.append(f"  {interest[signal['signal_type']]} ({'актуален' if signal['current'] else 'устарел'}): "
                     f"{signal.get('signal_reason') or signal.get('signal_quote')}; {signal.get('signal_date', '')}; {signal.get('signal_url', '')}")
    if not c['signals']:
        lines.append('  Спрос не подтверждён; обоснованная гипотеза не записана')
    lines.extend(['', f"Качество данных: {c['data_quality']}/100 ({c['data_quality_note']})",
                  f"Приоритет: {c['priority']} баллов — это не вероятность покупки"])
    for key, value in c['priority_factors'].items():
        lines.append(f"  {factors[key]}: {value}")
    lines.append(f"Готов к первому ручному звонку: {'да' if c['ready'] else 'нет'}")
    for blocker in c['blockers']:
        lines.append('  Причина: ' + blocker)
    lines.extend(['Следующий шаг: ' + c['next_step'], '', 'Доказательства:'])
    for evidence in c['evidence']:
        lines.append(f"  #{evidence['id']} {evidence['url']} · {evidence['observed_at']} · уверенность {evidence['confidence']}\n    {evidence['excerpt']}")
    lines.extend(['', 'История взаимодействий:'])
    for interaction in c['interactions']:
        lines.append(f"  {interaction['occurred_at']} · {interaction['kind']} · {interaction['outcome']}: {interaction['note']}")
    if not c['interactions']:
        lines.append('  Не зафиксированы')
    lines.append(f"Исторических наблюдений: {len(c['observations'])}. Для всех исходных фактов: show {c['id']} --json")
    return '\n'.join(lines)


def filters(cmd):
    cmd.add_argument('--ready', action='store_true', help='Только прошедшие квалификацию для первого ручного звонка')
    cmd.add_argument('--city')
    cmd.add_argument('--stage', choices=core.STAGES)


def main(argv=None):
    args = parser().parse_args(argv)
    conn = None
    try:
        conn = db.connect(args.db)
        db.migrate(conn)
        with conn:
            if args.command == 'init':
                emit({'status': 'База готова; миграции применены'})
            elif args.command == 'import':
                from .io import import_file
                report = import_file(conn, args.file, source_name=args.source)
                emit(report)
                return 2 if report['errors'] else 0
            elif args.command == 'export':
                from .io import export_file
                Path(args.file).parent.mkdir(parents=True, exist_ok=True)
                count = export_file(conn, args.file, ready_only=args.ready, city=args.city, stage=args.stage)
                emit({'exported': count, 'file': args.file})
            elif args.command == 'collect':
                from .sources import collect_sources
                if not 1 <= args.limit <= 100:
                    raise ValueError('Лимит должен быть от 1 до 100')
                report = collect_sources(conn, args.city, args.category, args.sources.split(','), args.limit)
                emit(report)
                return 2 if any(r['status'] != 'completed' for r in report) else 0
            elif args.command == 'list':
                rows = core.list_businesses(conn, args.ready, args.city, args.stage)
                emit([{k: r[k] for k in ('id','name','city','category','stage','do_not_contact','website_status_label','priority','data_quality','ready','next_step')} for r in rows])
            elif args.command == 'show':
                c = core.card(conn, args.id)
                emit(c) if args.json else print(render_card(c))
            elif args.command == 'edit':
                patch = json.loads(Path(args.file).read_text(encoding='utf-8'))
                if not isinstance(patch, dict):
                    raise ValueError('Ожидается JSON-объект полей')
                from .io import IMPORT_COLUMNS
                if set(patch) - set(IMPORT_COLUMNS):
                    raise ValueError('Неизвестные поля; используйте заголовки шаблона импорта')
                core.edit_business(conn, args.id, patch)
                emit({'status': 'Исправления сохранены с историей'})
            elif args.command == 'verify-site':
                patch = dict(website_status=args.status, website_checked_at=args.checked_at or core.now(),
                             website_check_source='manual_multisignal', source_url=args.url,
                             website_evidence=args.evidence, website_check_methods=args.methods.split(','))
                if args.website:
                    patch['website'] = args.website
                core.edit_business(conn, args.id, patch)
                emit(core.card(conn, args.id))
            elif args.command == 'probe-site':
                from .website import check_website
                emit(check_website(conn, args.id))
            elif args.command == 'contact':
                core.interact(conn, args.id, args.outcome, args.note, args.kind)
                emit({'status': 'Ручное взаимодействие записано; автоматической связи не выполнялось'})
            elif args.command == 'block':
                core.prohibit(conn, args.id, args.reason)
                emit({'status': 'Запрет контакта установлен'})
            elif args.command == 'delete':
                core.delete_business(conn, args.id)
                emit({'status': 'Карточка и связанные данные удалены; ограничения повторной обработки сохранены хешами'})
            elif args.command == 'delete-contact':
                row = conn.execute('SELECT business_id FROM contacts WHERE id=?', (args.id,)).fetchone()
                if not row:
                    raise ValueError('Контакт не найден')
                conn.execute('DELETE FROM contacts WHERE id=?', (args.id,))
                core.refresh_stage(conn, row[0])
                emit({'status': 'Текущий контакт удалён; для удаления всей истории используйте delete'})
            elif args.command == 'attempts':
                emit([dict(r) for r in conn.execute('SELECT a.*,s.name AS source FROM collection_attempts a JOIN sources s ON s.id=a.source_id ORDER BY a.id DESC')])
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        # Never print OS/SQL exceptions that might contain paths, queries or contacts.
        message = str(exc) if isinstance(exc, ValueError) else 'Ошибка файла или базы; проверьте путь и доступность'
        print('Ошибка: ' + message, file=sys.stderr)
        return 1
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
