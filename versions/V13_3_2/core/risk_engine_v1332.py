"""V13.3.2 experimental: weighted risk, 0..100; unknown != zero."""
import math
import pandas as pd
WEIGHTS = {'cvss': .25, 'epss': .20, 'kev': .20, 'asset_criticality': .15, 'exposure': .10, 'operational_impact': .10}
LEVELS = {'low': 25., 'medium': 50., 'med': 50., 'high': 75., 'critical': 100., 'very high': 100.}
EXPOSURE = {'internal': 25., 'interna':25., 'lan':25., 'dmz':75., 'internet':100., 'public':100., 'external':100., 'externa':100., 'isolated':0., 'aislado':0.}
TRUE = {'true','yes','1','si','sí','kev'}
FALSE = {'false','no','0'}
def number(value, low, high):
    try:
        x=float(value)
        return x if math.isfinite(x) and low <= x <= high else None
    except (TypeError,ValueError): return None

def factor_level(value, mapping):
    if value is None or pd.isna(value): return None
    s=str(value).strip().lower()
    if s in mapping: return mapping[s]
    # Explicit numeric factors on a 0..100 scale, not guessed categories.
    return number(value,0,100)

def evaluate(row):
    cvss=number(row.get('cvss'),0,10)
    epss=number(row.get('epss'),0,1)
    kev_value=row.get('cisa_kev')
    kev_text=str(kev_value).strip().lower() if kev_value is not None else ''
    kev=100. if kev_text in TRUE else 0. if kev_text in FALSE else None
    values={'cvss':cvss*10 if cvss is not None else None,
            'epss':epss*100 if epss is not None else None,
            'kev':kev,
            'asset_criticality':factor_level(row.get('asset_criticality'),LEVELS),
            'exposure':factor_level(row.get('exposure'),EXPOSURE),
            'operational_impact':factor_level(row.get('operational_impact'),LEVELS)}
    missing=[k for k,v in values.items() if v is None]
    weighted=sum(WEIGHTS[k]*v for k,v in values.items() if v is not None)
    known_weight=sum(WEIGHTS[k] for k,v in values.items() if v is not None)
    # Interval bounds explicitly show uncertainty, rather than treating unknown as zero.
    lower=round(weighted,2)
    upper=round(weighted+100*(1-known_weight),2)
    score=round(weighted,2) if not missing else None
    band=('Pendiente de evaluación' if score is None else
          'Crítico' if score>=80 else 'Alto' if score>=60 else 'Medio' if score>=40 else 'Bajo')
    return {'score':score,'band':band,'coverage_pct':round(known_weight*100,1),
            'risk_min':lower,'risk_max':upper,'missing_factors':', '.join(missing),
            'components':values,'method':'V13.3.2 weighted prototype; no empirical calibration'}

def evaluate_dataframe(df):
    work=df.copy()
    if work.empty:
        for col in ('priority_score','risk_band_v1332','risk_coverage_pct','risk_min','risk_max','risk_missing_factors'):
            work[col]=pd.Series(dtype='object')
        return work
    results=[evaluate(row) for _,row in work.iterrows()]
    work['priority_score']=[r['score'] for r in results]
    work['risk_band_v1332']=[r['band'] for r in results]
    work['risk_coverage_pct']=[r['coverage_pct'] for r in results]
    work['risk_min']=[r['risk_min'] for r in results]
    work['risk_max']=[r['risk_max'] for r in results]
    work['risk_missing_factors']=[r['missing_factors'] for r in results]
    return work
