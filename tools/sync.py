#!/usr/bin/env python3
"""Пересобирает index.html из Google Таблиц.

Читает сводную таблицу «СВОД_Контент-календари экспертов», по каждой ссылке
открывает личный контент-календарь эксперта, собирает задачи и ограничения,
пишет data.json и собирает ../index.html.

Авторизация: переменная окружения GOOGLE_TOKEN_JSON (содержимое
authorized_user JSON) либо локальный файл ~/google_token.json.
"""
import os, re, json, sys
from datetime import datetime, timedelta, timezone

SVOD = '1a2P_pGPWy2UQ_fx9rzSlPcrTgjRaj_MWLV3C0B0aEjk'
EXCLUDE = ['Заикина']                     # кого не берём в сводный календарь
STAGES = ['Темы', 'Голосовые', 'Сценарий', 'Съёмка видео', 'Монтаж и публикация']
HERE = os.path.dirname(os.path.abspath(__file__))


def service():
    import warnings; warnings.filterwarnings('ignore')
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    raw = os.environ.get('GOOGLE_TOKEN_JSON')
    if raw:
        creds = Credentials.from_authorized_user_info(json.loads(raw))
    else:
        for f in ('~/google_token_readonly.json', '~/google_token.json'):
            f = os.path.expanduser(f)
            if os.path.exists(f):
                creds = Credentials.from_authorized_user_file(f)
                break
        else:
            sys.exit('Нет токена: задайте GOOGLE_TOKEN_JSON или положите ~/google_token_readonly.json')
    return build('sheets', 'v4', credentials=creds, cache_discovery=False)


def values(svc, sid, rng):
    return svc.spreadsheets().values().get(
        spreadsheetId=sid, range=rng,
        valueRenderOption='FORMATTED_VALUE').execute().get('values', [])


# ---------------------------------------------------------------- отсутствия
RANGE_RE = re.compile(
    r'(?P<d1>\d{1,2})(?:\.(?P<m1>\d{1,2}))?(?:\.(?P<y1>\d{2,4}))?'
    r'\s*[–—-]\s*'
    r'(?P<d2>\d{1,2})\.(?P<m2>\d{1,2})(?:\.(?P<y2>\d{2,4}))?')


def _explicit_year(y):
    if not y:
        return None
    y = int(y)
    return y + 2000 if y < 100 else y


def _guess_year(day, month, base):
    """Год не указан — берём тот, при котором дата ближе всего к началу месяца."""
    best = None
    for y in (base.year - 1, base.year, base.year + 1):
        try:
            d = datetime(y, month, day)
        except ValueError:
            continue
        delta = abs((d - base).days)
        if best is None or delta < best[0]:
            best = (delta, y)
    return best[1] if best else base.year


def parse_absences(text, start):
    """Достаёт периоды отсутствия из свободного текста («12–15.11 и 27–29.11»)."""
    if not text:
        return []
    base = datetime.strptime(start, '%d.%m.%Y')
    out = []
    for m in RANGE_RE.finditer(text):
        m2 = int(m.group('m2'))
        m1 = int(m.group('m1') or m2)
        if not 1 <= m1 <= 12 or not 1 <= m2 <= 12:
            continue
        d1, d2 = int(m.group('d1')), int(m.group('d2'))
        y1 = (_explicit_year(m.group('y1')) or _explicit_year(m.group('y2'))
              or _guess_year(d1, m1, base))
        y2 = _explicit_year(m.group('y2')) or (y1 + 1 if m2 < m1 else y1)
        try:
            a = datetime(y1, m1, d1)
            b = datetime(y2, m2, d2)
        except ValueError:
            continue
        if b < a or (b - a).days > 120:
            continue
        around = text[max(0, m.start() - 90):m.end() + 40].lower()
        label = ('учёба' if 'учёб' in around else
                 'отпуск' if 'отпуск' in around else 'отсутствует')
        out.append({'from': a.strftime('%Y-%m-%d'),
                    'to': b.strftime('%Y-%m-%d'), 'label': label})
    return out


# ---------------------------------------------------------------- сбор данных
def collect():
    svc = service()
    rows = values(svc, SVOD, 'A1:D200')[1:]
    experts, events, skipped = [], [], []
    for r in rows:
        name = (r[1] if len(r) > 1 else '').strip()
        link = (r[2] if len(r) > 2 else '').strip()
        if not name or not link:
            continue
        if any(x.lower() in name.lower() for x in EXCLUDE):
            skipped.append(name); continue
        m = re.search(r'/d/([A-Za-z0-9_-]+)', link)
        if not m:
            skipped.append(name + ' (не разобрана ссылка)'); continue
        sid = m.group(1)
        meta = svc.spreadsheets().get(spreadsheetId=sid).execute()
        tabs = [s['properties']['title'] for s in meta['sheets']]
        tab = 'Календарь' if 'Календарь' in tabs else tabs[0]
        v = values(svc, sid, "'%s'" % tab)

        def cell(row, col):
            rr = v[row - 1] if len(v) >= row else []
            return (rr[col] if len(rr) > col else '').strip()

        e = {'name': name,
             'sheet': 'https://docs.google.com/spreadsheets/d/%s/edit' % sid,
             'start': cell(3, 1), 'voice': cell(5, 1), 'shoot': cell(6, 1),
             'volume': cell(7, 1), 'lead': cell(8, 1), 'notes': []}

        cycle = None
        for i in range(len(v)):
            row = v[i]
            c0 = (row[0] if row else '').strip()
            if c0.startswith('⚠'):
                e['notes'].append(c0)
            if len(row) < 7:
                continue
            if c0.startswith('Цикл'):
                cycle = c0
            stage, who, dur, start = (row[1].strip(), row[2].strip(),
                                      row[3].strip(), row[4].strip())
            if stage not in STAGES or not re.match(r'\d{2}\.\d{2}\.\d{4}$', start):
                continue
            d0 = datetime.strptime(start, '%d.%m.%Y')
            n = max(1, int(float(dur.replace(',', '.')))) if dur else 1
            events.append({'expert': name, 'cycle': cycle or 'Цикл', 'stage': stage,
                           'who': who, 'days': n, 'start': d0.strftime('%Y-%m-%d'),
                           'end': (d0 + timedelta(days=n - 1)).strftime('%Y-%m-%d')})

        e['absences'] = parse_absences(e['shoot'], e['start'] or '01.01.2026') + \
                        parse_absences(e['voice'], e['start'] or '01.01.2026')
        seen, uniq = set(), []
        for a in e['absences']:
            k = (a['from'], a['to'])
            if k not in seen:
                seen.add(k); uniq.append(a)
        e['absences'] = sorted(uniq, key=lambda a: a['from'])
        experts.append(e)
        print('  %-24s задач: %2d  отсутствие: %d' % (name, len([x for x in events if x['expert'] == name]), len(e['absences'])))

    experts.sort(key=lambda x: x['name'])
    if skipped:
        print('  не включены:', ', '.join(skipped))
    if not experts or not events:
        sys.exit('Пустой результат — таблицы не прочитались, ничего не перезаписываю')
    return {'experts': experts, 'events': events,
            'source': 'https://docs.google.com/spreadsheets/d/%s/edit' % SVOD}


def main():
    print('Читаю Google Таблицы…')
    data = collect()
    path = os.path.join(HERE, 'data.json')
    old = {}
    if os.path.exists(path):
        old = json.load(open(path))
    same = {k: v for k, v in old.items() if k != 'generated'} == data
    msk = datetime.now(timezone.utc) + timedelta(hours=3)
    data['generated'] = old.get('generated') if same else msk.strftime('%d.%m.%Y, %H:%M МСК')
    json.dump(data, open(path, 'w'), ensure_ascii=False, indent=1)
    parts = [open(os.path.join(HERE, f)).read()
             for f in ('tpl_head.html', 'data.json', 'tpl_tail.html')]
    open(os.path.join(HERE, '..', 'index.html'), 'w').write(''.join(parts))
    print('Данные %s · экспертов %d · задач %d · index.html собран' % (
        'без изменений' if same else 'ОБНОВЛЕНЫ', len(data['experts']), len(data['events'])))


if __name__ == '__main__':
    main()
