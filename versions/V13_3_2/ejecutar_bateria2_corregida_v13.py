"""Bateria 2 corregida: ejecuta el motor real V13.3.2 y preserva evidencia.
No confunde importacion de archivos con persistencia de Streamlit ni GPU detectada con inferencia.
"""
import argparse, csv, hashlib, json, math, os, platform, statistics, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

def stamp(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--app-dir',required=True);parser.add_argument('--datasets-dir',required=True);parser.add_argument('--out',required=True)
    parser.add_argument('--online',action='store_true',help='Reservado: no simula validacion NVD/FIRST en vivo')
    args=parser.parse_args();app=Path(args.app_dir).resolve();ds=Path(args.datasets_dir).resolve();out=Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=True);sys.path.insert(0,str(app))
    results=[]
    def finish():
        csvpath=out/'bateria2_corregida_resultados.csv'
        with csvpath.open('w',newline='',encoding='utf-8-sig') as fh:
            writer=csv.DictWriter(fh,fieldnames=['test_id','category','status','detail','evidence','utc'])
            writer.writeheader();writer.writerows(results)
        counts={v:sum(r['status']==v for r in results) for v in ('PASS','FAIL','PENDING')}
        manifest={'run_utc':stamp(),'app_dir':str(app),'datasets_dir':str(ds),'python':sys.version,'platform':platform.platform(),'counts':counts,'results_sha256':sha(csvpath),'method':'Motor real; benchmarks pueden contener CVSS/EPSS ausentes; no imputar.'}
        (out/'bateria2_corregida_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf8')
        print('BATERIA 2 CORREGIDA:',counts,'\nEvidencias:',out)
        return 1 if counts['FAIL'] else 0
    def check(name,category,status,detail='',evidence=''):
        results.append(dict(test_id=name,category=category,status=status,detail=str(detail),evidence=str(evidence),utc=stamp()))
    try:
        from core.normalizer import normalize_uploaded_file
        from core.risk_engine_v1332 import evaluate, evaluate_dataframe, WEIGHTS
        risk_matrix = evaluate_dataframe
        check('IMPORT_REAL','integration','PASS','core.normalizer + core.risk_engine_v1332.evaluate_dataframe importados (mismo motor que usa core.analysis.risk_matrix)')
    except Exception as e:
        check('IMPORT_REAL','integration','FAIL',repr(e));return finish()
    def expected(v):
        return round(.25*v['cvss']*10 + .20*v['epss']*100 + .20*(100 if v['cisa_kev'] else 0) + .15*v['asset_criticality'] + .10*v['exposure'] + .10*v['operational_impact'],2)
    base=dict(cvss=8,epss=.5,cisa_kev=True,asset_criticality=75,exposure=100,operational_impact=50)
    cases=[('ZERO',dict(cvss=0,epss=0,cisa_kev=False,asset_criticality=0,exposure=0,operational_impact=0)),('MAX',dict(cvss=10,epss=1,cisa_kev=True,asset_criticality=100,exposure=100,operational_impact=100)),('BASE',base)]
    for name,row in cases:
        actual=evaluate(row)['score'];want=expected(row)
        check('RISK_'+name,'risk_engine','PASS' if actual==want else 'FAIL',f'actual={actual}; expected={want}')
    for factor in base:
        row=dict(base);row[factor]=None
        r=evaluate(row)
        ok=r['score'] is None and ('kev' if factor == 'cisa_kev' else factor) in r['missing_factors'] and r['risk_min']<=r['risk_max']
        check('MISSING_'+factor,'missing','PASS' if ok else 'FAIL',f'score={r["score"]},missing={r["missing_factors"]},interval={r["risk_min"]}:{r["risk_max"]}')
    for factor,change in [('cvss',1),('epss',.1),('cisa_kev',False),('asset_criticality',100),('exposure',25),('operational_impact',100)]:
        a=dict(base);b=dict(base);b[factor]=change
        delta=round(evaluate(b)['score']-evaluate(a)['score'],2)
        want=round(expected(b)-expected(a),2)
        check('SENS_'+factor,'sensitivity','PASS' if delta==want else 'FAIL',f'delta={delta}; expected={want}')
    for key,value in [('cvss',11),('epss',1.5),('cisa_kev','unknown'),('asset_criticality','n/a'),('exposure','n/a'),('operational_impact','n/a')]:
        row=dict(base);row[key]=value;r=evaluate(row)
        check('INVALID_'+key,'invalid','PASS' if r['score'] is None else 'FAIL',f'score={r["score"]}')
    # File objects mimic Streamlit UploadedFile .name, with file-like content.
    import io
    counts=[]; allrows=[]
    files=sorted(ds.glob('*.xlsx'))+sorted(ds.glob('*.csv'))
    if not files:check('DATASET_FOUND','datasets','FAIL','No se encontraron datasets')
    for f in files:
        t=time.perf_counter()
        try:
            raw=f.read_bytes();buf=io.BytesIO(raw);buf.name=f.name
            norm=normalize_uploaded_file(buf)
            scored=risk_matrix(norm)
            n=int(scored['priority_score'].notna().sum());rows=len(scored)
            bad=int((pd.to_numeric(scored['priority_score'],errors='coerce').dropna().between(0,100)==False).sum())
            unknown_kev=int(norm['cisa_kev'].isna().sum())
            status='PASS' if rows>0 and bad==0 and len(scored)==rows else 'FAIL'
            detail=f'rows={rows}; scored={n}; pending={rows-n}; unknown_kev={unknown_kev}; ms={(time.perf_counter()-t)*1000:.2f}; sha256={sha(f)}'
            check('DATA_'+f.stem,'dataset_real',status,detail,f.name)
            counts.append(dict(dataset=f.name,rows=rows,complete_scores=n,pending=rows-n,unknown_kev=unknown_kev,elapsed_ms=round((time.perf_counter()-t)*1000,2),sha256=sha(f)))
            allrows.append(scored.assign(dataset_file=f.name))
        except Exception as e:check('DATA_'+f.stem,'dataset_real','FAIL',repr(e),f.name)
    if allrows:
        combined=pd.concat(allrows,ignore_index=True)
        cols=[c for c in ['dataset_file','finding_id','cve','cvss','epss','cisa_kev','asset_criticality','exposure','operational_impact','priority_score','risk_min','risk_max','risk_missing_factors','cvss_version','epss_date','provenance_status'] if c in combined.columns]
        target=out/'evidencia_riesgo_por_hallazgo.csv';combined[cols].to_csv(target,index=False,encoding='utf-8-sig')
        check('TRACE_EXPORT','traceability','PASS',f'rows={len(combined)}; sha256={sha(target)}',target.name)
        pd.DataFrame(counts).to_csv(out/'cobertura_datasets.csv',index=False,encoding='utf-8-sig')
    # File persistence test: round-trip and hash.
    sample={'version':'V13.3.2-corrective','sentinel':'EMCALI-RISK','utc':stamp()}
    dest=out/'persistence_probe_corrected.json';dest.write_text(json.dumps(sample,sort_keys=True),encoding='utf8')
    check('PERSIST_FILE','persistence','PASS' if json.loads(dest.read_text(encoding='utf8'))==sample else 'FAIL',f'sha256={sha(dest)}',dest.name)
    check('PERSIST_STREAMLIT','persistence','PENDING','No hay persistencia de hallazgos entre reinicios implementada/verificada; requiere prueba real de reinicio de servidor.')
    check('NVD_LIVE','enrichment','PENDING','No se consultaron fuentes externas; los metadatos del benchmark no prueban consulta NVD en vivo.')
    check('EPSS_LIVE','enrichment','PENDING','No se consultaron fuentes externas; ejecutar verificacion independiente con acceso a Internet.')
    check('GPU_INFERENCE','performance','PENDING','No se midio inferencia real de Ollama ni uso GPU; requiere 30 ejecuciones y telemetria.')
    check('STREAMLIT_E2E','performance','PENDING','No se midio rendimiento UI real, ni persistencia entre sesiones.')
    return finish()

    
if __name__=='__main__':
    sys.exit(main())
