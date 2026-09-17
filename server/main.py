#!/usr/bin/env python3
"""Общая база календаря команды: кто активен и что выполнено.

Одно состояние на всю команду, хранится JSON-файлом на диске Railway,
поэтому отметки, сделанные на одном компьютере, видны на остальных.

GET  /state                 -> всё состояние (читать может кто угодно)
POST /patch  {experts,done} -> точечно меняет и возвращает новое состояние
GET  /health                -> для мониторинга

Запись требует ключ: параметр ?key= или заголовок X-Key, значение из APP_KEY.
Ключ не хранится в репозитории страницы — его вводят на сайте один раз
в каждом браузере.
"""
import json, os, threading, time
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

DATA_DIR = os.environ.get('DATA_DIR', '/data')
STATE = os.path.join(DATA_DIR, 'state.json')
KEY = os.environ.get('APP_KEY', '')
LOCK = threading.Lock()

app = FastAPI(title='Календарь команды · общее состояние')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'],
                   allow_headers=['*'], max_age=86400)


def msk():
    return (datetime.now(timezone.utc) + timedelta(hours=3)).strftime('%d.%m.%Y, %H:%M МСК')


def load():
    """Читает состояние с диска; пустой или битый файл — начинаем с нуля."""
    try:
        with open(STATE, encoding='utf-8') as f:
            s = json.load(f)
    except Exception:
        s = {}
    s.setdefault('experts', {})   # имя -> {"active": bool, "at": "..."}
    s.setdefault('done', {})      # id слота -> {"at": "..."}
    s.setdefault('rev', 0)
    s.setdefault('updated', '')
    return s


def save(s):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = STATE + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(s, f, ensure_ascii=False)
    os.replace(tmp, STATE)


def check(req: Request):
    if not KEY:
        return
    given = req.query_params.get('key') or req.headers.get('x-key', '')
    if given != KEY:
        raise HTTPException(status_code=403, detail='bad key')


@app.get('/health')
def health():
    s = load()
    return {'ok': True, 'rev': s['rev'], 'updated': s['updated'],
            'experts': len(s['experts']), 'done': len(s['done'])}


@app.get('/state')
def get_state():
    return load()


@app.post('/patch')
async def patch(request: Request):
    """{"experts": {"Имя": false}, "done": {"id": true}} — только присланные ключи.

    Значение null убирает ключ совсем (эксперт выбыл из сводной таблицы).
    """
    check(request)
    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail='object expected')
    experts = body.get('experts') or {}
    done = body.get('done') or {}
    if not isinstance(experts, dict) or not isinstance(done, dict):
        raise HTTPException(status_code=400, detail='experts/done must be objects')
    if len(experts) > 200 or len(done) > 2000:
        raise HTTPException(status_code=400, detail='too many keys')
    now = msk()
    with LOCK:
        s = load()
        for name, active in experts.items():
            name = str(name)[:120]
            if active is None:
                s['experts'].pop(name, None)
            else:
                s['experts'][name] = {'active': bool(active), 'at': now}
        for sid, v in done.items():
            sid = str(sid)[:300]
            if v:
                s['done'][sid] = {'at': now}
            else:
                s['done'].pop(sid, None)
        if experts or done:
            s['rev'] += 1
            s['updated'] = now
            save(s)
    return s
