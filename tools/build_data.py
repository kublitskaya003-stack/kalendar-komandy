import json, re
from datetime import datetime, timedelta
raw=json.load(open('all_raw.json'))
WD=['Пн','Вт','Ср','Чт','Пт','Сб','Вс']
STAGES=['Темы','Голосовые','Сценарий','Съёмка видео','Монтаж и публикация']
experts=[]; events=[]
for name,info in raw.items():
    v=info['tabs']['Календарь']
    def cell(r,c):
        row=v[r-1] if len(v)>=r else []
        return row[c] if len(row)>c else ''
    e={'name':name,'sheet':'https://docs.google.com/spreadsheets/d/%s/edit'%info['id'],
       'start':cell(3,1),'voice':cell(5,1),'shoot':cell(6,1),'volume':cell(7,1),'lead':cell(8,1),'notes':[]}
    for r in range(40,len(v)+1):
        t=cell(r,0).strip()
        if t.startswith('⚠'): e['notes'].append(t)
    cycle=None
    for r in range(20,40):
        row=v[r-1] if len(v)>=r else []
        if len(row)<7: continue
        c0=row[0].strip()
        if c0: cycle=c0
        stage=row[1].strip(); who=row[2].strip(); dur=row[3].strip(); start=row[4].strip()
        if stage not in STAGES or not start: continue
        d0=datetime.strptime(start,'%d.%m.%Y')
        n=int(float(dur.replace(',','.'))) if dur else 1
        events.append({'expert':name,'cycle':cycle,'stage':stage,'who':who,'days':n,
                       'start':d0.strftime('%Y-%m-%d'),
                       'end':(d0+timedelta(days=n-1)).strftime('%Y-%m-%d')})
    experts.append(e)
experts.sort(key=lambda x:x['name'])
data={'experts':experts,'events':events,
      'source':'https://docs.google.com/spreadsheets/d/1a2P_pGPWy2UQ_fx9rzSlPcrTgjRaj_MWLV3C0B0aEjk/edit',
      'generated':datetime.now().strftime('%d.%m.%Y')}
json.dump(data,open('data.json','w'),ensure_ascii=False,indent=1)
ds=sorted(e['start'] for e in events); de=sorted(e['end'] for e in events)
print('experts',len(experts),'events',len(events),'range',ds[0],de[-1])
from collections import Counter
print(Counter(e['stage'] for e in events))
print(Counter(e['who'] for e in events))
