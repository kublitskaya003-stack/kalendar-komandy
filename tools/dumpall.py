import warnings, json
warnings.filterwarnings('ignore')
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
creds = Credentials.from_authorized_user_file('/Users/angelinakublitskaya/google_token.json')
s = build('sheets','v4',credentials=creds)
EXPERTS = [
 ("Евгения Клинчук","1uLbIl8uVwuOyEERGxfP94Czraym5jKQ5aWOCLmW5yL4"),
 ("Екатерина Грабовская","1sY2-bQdCVSBQpCZFtubv_fhaVLE5gTjmTfQA9UB5qG0"),
 ("Инна Чеботаева","1PXinLwOLTTUP5FIq0EMDWKodI_WIupeF7iWFhG7RuXI"),
 ("Ирина Савушкина","1blV-ux2JMLqlUl_XYXjc6mDMuYY5MaBtjO0Xe48ImKI"),
 ("Оксана Пополитова","1rXXylG62CBDqYBuGLCE6wMrA7na4-1M3IOLw3-c8lpc"),
 ("Руслан Терекбаев","1IdBESO24RtnBMXYD4UHUCcNUVtPTt8ZKPkMJ6FiV6FY"),
 ("Юлия Белкина","11NyLGMtQryKRNtJvcbr-FeJRI1r_1LbLpovx4z4FOX0"),
 ("Юлия Ивашечкина","12IVkG1DE9MEYUD5y_jcHSKge_t1zGpFRh2ZYhrbDg4Y"),
 ("Юлия Кулинич","1yPlHA2CCASRg5teXP_Of7Wc8vUcRTF9slKRz2HB2P3Y"),
]
out={}
for name, sid in EXPERTS:
    m = s.spreadsheets().get(spreadsheetId=sid).execute()
    tabs=[sh['properties']['title'] for sh in m['sheets']]
    out[name]={'id':sid,'title':m['properties']['title'],'tabs':{}}
    print('===',name,'|',m['properties']['title'],'| tabs:',tabs)
    for t in tabs:
        v = s.spreadsheets().values().get(spreadsheetId=sid, range=f"'{t}'", valueRenderOption='FORMATTED_VALUE').execute().get('values',[])
        out[name]['tabs'][t]=v
        print('   tab',t,'rows',len(v))
json.dump(out, open('all_raw.json','w'), ensure_ascii=False, indent=1)
