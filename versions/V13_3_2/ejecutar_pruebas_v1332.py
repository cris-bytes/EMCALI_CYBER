"""Pruebas offline reproducibles V13.3.2. No modifica datos ni consulta API/LLM.
Uso: python ejecutar_pruebas_v1332.py --app-dir C:\\...\\EMCALI_Cyber_V13_3_2_EXP --datasets-dir C:\\...\\datasets --out resultados_v1332.csv
"""
import argparse,csv,hashlib,sys,time,math,traceback,io
from pathlib import Path
import pandas as pd

p=argparse.ArgumentParser();p.add_argument('--app-dir',required=True);p.add_argument('--datasets-dir',required=True);p.add_argument('--out',default='resultados_v1332.csv');a=p.parse_args()
sys.path.insert(0,str(Path(a.app_dir).resolve()))
from core.normalizer import normalize_uploaded_file
from core.risk_engine_v1332 import evaluate, evaluate_dataframe
from core.enrichment_bridge import integrate_enriched_file

records=[]
def test(code,category,dataset,expected,actual,ok,elapsed=0,detail=''):
 records.append(dict(test_id=code,category=category,dataset=dataset,expected=str(expected),actual=str(actual),status='PASS' if ok else 'FAIL',elapsed_ms=round(elapsed*1000,2),detail=detail))

def base():
 return {'cvss':8.8,'epss':.0124,'cisa_kev':True,'asset_criticality':'Low','exposure':'DMZ','operational_impact':'Low'}

s=base(); t=time.perf_counter();r=evaluate(s);test('R01','unit','synthetic','score 56.00',r['score'],r['score']==56.0,time.perf_counter()-t)
for field in s:
 q=s.copy();q[field]=None;r=evaluate(q)
 test('M_'+field,'missing','synthetic','score=None and missing '+field,repr(r['score'])+'; '+r['missing_factors'],r['score'] is None and ('kev' if field=='cisa_kev' else field) in r['missing_factors'])
q=s.copy();q['asset_criticality']='Critical';a1=evaluate(s);a2=evaluate(q)
test('S01','sensitivity','synthetic','delta 11.25',round(a2['score']-a1['score'],2),math.isclose(a2['score']-a1['score'],11.25,abs_tol=.01))
for field,value in [('cvss',11),('epss',1.1),('asset_criticality','undefined')]:
 q=s.copy();q[field]=value;r=evaluate(q);test('V_'+field,'invalid','synthetic','score=None',r['score'],r['score'] is None)

folder=Path(a.datasets_dir)
for path in sorted(folder.glob('*.xlsx')):
 start=time.perf_counter()
 try:
  with path.open('rb') as f:
   class Upload(io.BytesIO):
    def __init__(self,data,name):super().__init__(data);self.name=name
    def getvalue(self):return super().getvalue()
   u=Upload(f.read(),path.name)
  raw=pd.read_excel(path)
  normalized=normalize_uploaded_file(u)
  scored=evaluate_dataframe(normalized)
  ok=len(raw)==len(scored)
  test('D_'+path.stem,'dataset',path.name,len(raw),len(scored),ok,time.perf_counter()-start,'complete_scores='+str(int(scored.priority_score.notna().sum()))+'; pending='+str(int(scored.priority_score.isna().sum())))
  inrange=bool(scored.priority_score.dropna().between(0,100).all())
  test('B_'+path.stem,'bounds',path.name,'scores in [0,100]',inrange,inrange)
 except Exception as e:
  test('D_'+path.stem,'dataset',path.name,'read+normalize+score','ERROR',False,time.perf_counter()-start,str(e))

# This test confirms code behavior only, not Streamlit persistence after restart.
try:
 d=pd.DataFrame([s]);before=evaluate_dataframe(d);after=evaluate_dataframe(d.copy())
 test('DET01','determinism','synthetic','same score',str(before.priority_score.iloc[0])+' / '+str(after.priority_score.iloc[0]),before.priority_score.iloc[0]==after.priority_score.iloc[0])
except Exception as e:test('DET01','determinism','synthetic','same score','ERROR',False,detail=str(e))

out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
print('Pruebas:',len(records),'PASS:',sum(x['status']=='PASS' for x in records),'FAIL:',sum(x['status']=='FAIL' for x in records));print('Resultados:',out.resolve())
