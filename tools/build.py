"""Собирает index.html: tpl_head.html + data.json + tpl_tail.html"""
import os
d = os.path.dirname(os.path.abspath(__file__))
out = os.path.join(d, '..', 'index.html')
parts = [open(os.path.join(d, f)).read() for f in ('tpl_head.html', 'data.json', 'tpl_tail.html')]
open(out, 'w').write(''.join(parts))
print('index.html собран:', sum(len(p) for p in parts), 'байт')
