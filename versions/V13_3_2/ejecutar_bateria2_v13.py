#!/usr/bin/env python3
"""Bateria 2 EMCALI Cyber: evidencias reproducibles, sin fabricar aprobaciones.
Uso: python ejecutar_bateria2_v13.py --app-dir C:\\EMCALI_Cyber_V13_3_2_EXP --datasets-dir C:\\...\\datasets --out C:\\...\\bateria2
Opcionales: --risk-module core.analysis --risk-function risk_matrix --online --cve CVE-2024-3400 --model phi3:mini
"""
import argparse, csv, hashlib, importlib, json, math, os, platform, re, subprocess, sys, tempfile, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ('cvss','epss','cisa_kev','asset_criticality','exposure','operational_impact')
WEIGHTS = {'cvss':.25,'epss':.20,'cisa_kev':.20,'asset_criticality':.15,'exposure':.10,'operational_impact':.10}
RESULTS=[]
def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def record(id,group,status,detail='',elapsed_ms=None,evidence='',dataset=''):
    RESULTS.append(dict(test_id=id,category=group,status=status,detail=str(detail)[:1800],elapsed_ms=elapsed_ms,evidence=evidence,dataset=dataset,utc=now()))
def run(id,group,fn):
    t=time.perf_counter()
    try:
        status,detail,evidence=fn()
    except Exception as e: status,detail,evidence='FAIL',f'{type(e).__name__}: {e}',''
    record(id,group,status,detail,round((time.perf_counter()-t)*1000,3),evidence)
def ref_score(v):
    if set(v)!=set(FIELDS):return None
    if any(not isinstance(v[k],(int,float)) or not math.isfinite(v[k]) or not 0<=v[k]<=100 for k in FIELDS):return None
    return round(sum(WEIGHTS[k]*v[k] for k in FIELDS),6)
def cmd(args):
    try: return subprocess.run(args,capture_output=True,text=True,timeout=15)
    except Exception: return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--app-dir',required=True);ap.add_argument('--datasets-dir',required=True);ap.add_argument('--out',required=True)
    ap.add_argument('--risk-module',default='core.analysis');ap.add_argument('--risk-function',default='risk_matrix')
    ap.add_argument('--online',action='store_true',help='Consultar NVD/FIRST en vivo (requiere red)')
    ap.add_argument('--cve',default='CVE-2024-3400');ap.add_argument('--model',default='phi3:mini')
    args=ap.parse_args(); app=Path(args.app_dir).resolve(); datasets=Path(args.datasets_dir).resolve(); out=Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=True)
    meta={'run_utc':now(),'app_dir':str(app),'datasets_dir':str(datasets),'python':sys.version,'platform':platform.platform(),'risk_adapter':f'{args.risk_module}.{args.risk_function}','model':args.model,'online':args.online,'weights':WEIGHTS,'warning':'No confundir persistencia de archivo con persistencia de sesion Streamlit ni CPU con inferencia LLM.'}
    for label,path in [('app',app),('datasets',datasets)]:
        record('ENV_'+label,'environment','PASS' if path.is_dir() else 'FAIL',str(path))
    if not app.is_dir() or not datasets.is_dir():
        finish(out,meta);return 2
    sys.path.insert(0,str(app))
    # Formula independiente: no demuestra que el motor real la implemente.
    for name,v,expected in [
        ('all_zero',{k:0 for k in FIELDS},0),('all_max',{k:100 for k in FIELDS},100),
        ('cvss_only',{k:(100 if k=='cvss' else 0) for k in FIELDS},25),
        ('epss_only',{k:(100 if k=='epss' else 0) for k in FIELDS},20),
        ('kev_only',{k:(100 if k=='cisa_kev' else 0) for k in FIELDS},20),
        ('criticality_only',{k:(100 if k=='asset_criticality' else 0) for k in FIELDS},15),
        ('exposure_only',{k:(100 if k=='exposure' else 0) for k in FIELDS},10),
        ('impact_only',{k:(100 if k=='operational_impact' else 0) for k in FIELDS},10)]:
        run('REF_'+name,'reference_formula',lambda v=v,expected=expected:('PASS' if ref_score(v)==expected else 'FAIL',f'reference={ref_score(v)} expected={expected}',''))
    for k in FIELDS:
        v={q:50 for q in FIELDS};del v[k]
        run('REF_missing_'+k,'missing_reference',lambda v=v:('PASS' if ref_score(v) is None else 'FAIL',f'reference={ref_score(v)}',''))
    # Verificar existencia del motor real; la integracion requiere adaptador acorde a firma y esquema.
    try:
        m=importlib.import_module(args.risk_module); f=getattr(m,args.risk_function)
        import inspect
        meta['risk_signature']=str(inspect.signature(f));meta['risk_file']=inspect.getsourcefile(f)
        record('ENGINE_IMPORT','engine','PASS',f'Funcion encontrada: {meta["risk_signature"]}',evidence=meta['risk_file'] or '')
    except Exception as e:record('ENGINE_IMPORT','engine','FAIL',f'{type(e).__name__}: {e}');f=None
    # Dataset integrity; no declarar score completo sin ejecutar motor.
    try: import pandas as pd
    except ImportError: pd=None;record('PANDAS','environment','FAIL','Instalar pandas y openpyxl')
    ds=list(sorted(datasets.glob('*.xlsx')))+list(sorted(datasets.glob('*.csv')))
    if not ds:record('DATASET_DISCOVERY','datasets','FAIL','No se encontraron xlsx/csv')
    for i,p in enumerate(ds,1):
        t=time.perf_counter()
        try:
            if pd is None:raise RuntimeError('pandas no disponible')
            df=pd.read_excel(p) if p.suffix.lower()=='.xlsx' else pd.read_csv(p)
            cols=[str(c).strip().lower() for c in df.columns];cves=next((df.iloc[:,j] for j,c in enumerate(cols) if c in ('cve','cve_id')),None)
            nvalid=int(cves.astype(str).str.match(r'^CVE-\d{4}-\d{4,}$',case=False).sum()) if cves is not None else None
            record(f'DATA_{i:03}','datasets','PASS',f'rows={len(df)} cols={len(cols)} valid_cves={nvalid} sha256={sha(p)}',round((time.perf_counter()-t)*1000,3),str(p),p.name)
            # Schema y cobertura: no imputar valores faltantes.
            present=[x for x in FIELDS if x in cols]
            status='PASS' if len(present)==6 else 'PENDING'
            record(f'COVERAGE_{i:03}','six_factors',status,f'Columnas presentes={present}; faltantes={[x for x in FIELDS if x not in cols]}. Requiere mapeo explicito y ejecucion del motor.',dataset=p.name)
            # Guardar manifiesto y recuentos; no asignar puntuaciones simuladas.
        except Exception as e:record(f'DATA_{i:03}','datasets','FAIL',f'{type(e).__name__}: {e}',dataset=p.name)
    # Persistencia real de exportacion: serializar, leer, hash y comparar. No valida st.session_state.
    def persist():
        data={'run_utc':meta['run_utc'],'weights':WEIGHTS,'sentinel':'EMCALI-V13-B2'}
        target=out/'persistence_probe.json';target.write_text(json.dumps(data,sort_keys=True),encoding='utf-8')
        loaded=json.loads(target.read_text(encoding='utf-8'))
        return ('PASS' if loaded==data else 'FAIL',f'file_sha256={sha(target)}',str(target))
    run('PERSIST_FILE','file_persistence',persist)
    record('PERSIST_STREAMLIT','streamlit_persistence','PENDING','Reiniciar Streamlit, recargar la misma evidencia y verificar que los datos persisten sin st.session_state; requiere adaptador de almacenamiento y prueba manual/automatizada de interfaz.')
    record('ENGINE_SIX_FACTOR','engine','PENDING','Falta ejecutar comparacion contra motor V13.3.2 con un fixture de seis factores normalizados 0..100 y score esperado; no inferir firma o mapeo.')
    record('ENGINE_SENSITIVITY','engine','PENDING','Comparar variacion individual de cada factor en motor real y comprobar monotonicidad y delta segun pesos.')
    # Evidencia local de GPU sin inventar rendimiento del modelo.
    gpu=cmd(['nvidia-smi','--query-gpu=name,memory.total,driver_version,utilization.gpu','--format=csv,noheader'])
    record('GPU_DETECT','hardware','PASS' if gpu and gpu.returncode==0 else 'PENDING',gpu.stdout.strip() if gpu and gpu.returncode==0 else 'nvidia-smi no disponible; medir en HP Victus',evidence='nvidia-smi')
    record('GPU_INFERENCE','performance','PENDING','Ejecutar N>=30 inferencias locales; registrar modelo, prompt, tokens, latencia p50/p95, GPU VRAM/uso, CPU/RAM, errores y warmup.')
    record('PERF_STREAMLIT','performance','PENDING','Medir importacion/riesgo end-to-end con 50/100/250/500/750/1000 registros; p50/p95 de al menos 5 repeticiones por carga.')
    # Red externa solo opt-in, con URL exacta y sin credenciales en artefactos.
    if args.online:
        def get_json(url):
            req=urllib.request.Request(url,headers={'User-Agent':'EMCALI-Cyber-Research-B2/1.0'})
            with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
        from urllib.parse import urlencode
        def nvd():
            d=get_json('https://services.nvd.nist.gov/rest/json/cves/2.0?'+urlencode({'cveId':args.cve}))
            rec=d.get('vulnerabilities',[])
            if not rec:return 'PENDING','CVE no encontrado en NVD',''
            c=rec[0]['cve'];p=out/'nvd_evidence.json';p.write_text(json.dumps({'retrieved_at':now(),'cve':c,'source':'NVD'},ensure_ascii=False,indent=2),encoding='utf-8')
            return 'PASS',f'cve={c.get("id")} status={c.get("vulnStatus")} sha256={sha(p)}',str(p)
        def epss():
            d=get_json('https://api.first.org/data/v1/epss?'+urlencode({'cve':args.cve}))
            rec=d.get('data',[])
            if not rec:return 'PENDING','FIRST no devolvio EPSS para el CVE',''
            p=out/'epss_evidence.json';p.write_text(json.dumps({'retrieved_at':now(),'data':rec,'source':'FIRST EPSS'},ensure_ascii=False,indent=2),encoding='utf-8')
            return 'PASS',f'cve={rec[0].get("cve")} epss={rec[0].get("epss")} date={rec[0].get("date")} sha256={sha(p)}',str(p)
        run('NVD_LIVE','enrichment',nvd);run('EPSS_LIVE','enrichment',epss)
    else:
        record('NVD_LIVE','enrichment','PENDING','No se consulto NVD; activar --online')
        record('EPSS_LIVE','enrichment','PENDING','No se consulto FIRST EPSS; activar --online')
    record('ENRICH_APP','enrichment','PENDING','Comparar CVSS/EPSS importados con respuestas oficiales, fuente, fecha, vector y ausencia de imputaciones; requiere adaptador de importacion V13.3.2.')
    finish(out,meta);return 0 if all(r['status']!='FAIL' for r in RESULTS) else 1

def finish(out,meta):
    cols=['test_id','category','status','dataset','elapsed_ms','detail','evidence','utc']
    with (out/'bateria2_resultados.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(RESULTS)
    meta['counts']={s:sum(r['status']==s for r in RESULTS) for s in ('PASS','FAIL','PENDING')}
    meta['result_sha256']=sha(out/'bateria2_resultados.csv')
    (out/'bateria2_manifest.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
    print('BATERIA 2:',meta['counts'],'\nEvidencias:',out)
    print('NOTA: PENDING no equivale a PASS; resultados de referencia no equivalen a pruebas del motor real.')
if __name__=='__main__':sys.exit(main())
